"""
winrt_pipeline.py

Replaces audio_pipeline.SlidingWindowPipeline. Instead of pulling raw audio
frames from sounddevice and pushing them through Whisper, this hands the
microphone entirely to Windows' own on-device continuous dictation engine
(Windows.Media.SpeechRecognition, DICTATION topic constraint) and relays its
results into the exact same downstream contract server.py already expects.

IMPORTANT ARCHITECTURAL NOTE (read before debugging "no audio" issues):
WinRT's SpeechRecognizer captures the default microphone directly at the OS
level -- it does NOT accept audio pushed from Python. That means:
  - push_audio() below is a no-op, kept only so server.py's existing
    sounddevice callback (if still wired anywhere) doesn't crash.
  - server.py's start_mic() must NOT also open a sounddevice InputStream --
    two consumers fighting over the same input device will cause glitches
    or silent failure on some drivers. This bundle's server.py already has
    that removed; if you're diffing against the old server.py, that's why.

Output contract preserved for server.py / detection_orchestrator.py:
    on_result(AudioChunkResult(text, avg_logprob, start_ts, end_ts, had_speech))
    on_speech_started(timestamp: float)
    on_partial_result(text: str)  -- NEW. WinRT fires two distinct event
        types: hypothesis_generated (continuous, live, fires on nearly
        every word WHILE you're still talking) and result_generated (fires
        ONCE, only after WinRT decides the phrase is finished). Previously
        only result_generated was wired to anything visible -- hypothesis
        events were used solely to flag "speech started" the first time
        they fired, and the actual growing partial text they carry on
        every subsequent call was discarded. That's why nothing appeared
        in the terminal until a pause. on_partial_result carries that
        growing text so callers can echo it live, in place, ahead of the
        eventual finalized [TRANSCRIPT] line. It is NOT run through
        detection -- detection stays anchored to the finalized on_result
        text only.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger("windowverse.winrt_pipeline")

_WINRT_CHECKS: tuple[tuple[str, str], ...] = (
    ("winrt.windows.foundation", "winrt-Windows.Foundation"),
    ("winrt.windows.foundation.collections", "winrt-Windows.Foundation.Collections"),
    ("winrt.windows.globalization", "winrt-Windows.Globalization"),
    ("winrt.windows.media.speechrecognition", "winrt-Windows.Media.SpeechRecognition"),
    ("winrt.windows.storage", "winrt-Windows.Storage"),
)


def verify_winrt_dependencies() -> list[str]:
    """Return pip package names that are missing (empty list = OK)."""
    missing: list[str] = []
    for mod, pkg in _WINRT_CHECKS:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def winrt_install_hint(missing: list[str] | None = None) -> str:
    pkgs = missing or verify_winrt_dependencies()
    if not pkgs:
        return ""
    extra = f" ({', '.join(pkgs)})" if pkgs else ""
    return (
        f"Install Windows speech packages{extra}: "
        "pip install -r requirements_winrt.txt --break-system-packages — then restart MultiVerse."
    )


def probe_winrt_mic(timeout: float = 25.0) -> str | None:
    """Start/stop WinRT dictation briefly. Return error text or None if OK."""
    missing = verify_winrt_dependencies()
    if missing:
        return winrt_install_hint(missing)
    pipeline = WinRTSpeechPipeline()
    pipeline.start()
    try:
        if not pipeline.wait_session_ready(timeout):
            return pipeline.last_error or "Microphone session did not start in time"
        if not pipeline.is_running():
            return pipeline.last_error or "Microphone session stopped unexpectedly"
        return None
    finally:
        pipeline.stop()


@dataclass
class AudioChunkResult:
    text: str
    avg_logprob: float | None
    start_ts: float
    end_ts: float
    had_speech: bool


class WinRTSpeechPipeline:
    """
    Constructor deliberately accepts **_ignored so any leftover
    transcriber / chunk_seconds / overlap_seconds kwargs from the old
    call site don't break anything -- WinRT needs none of them; it does
    its own capture, its own VAD-equivalent turn-taking, and its own
    chunking internally.
    """

    def __init__(self, on_result=None, on_speech_started=None,
                 on_partial_result=None, on_session_recovered=None, **_ignored):
        self.on_result = on_result
        self.on_speech_started = on_speech_started
        self.on_partial_result = on_partial_result
        self.on_session_recovered = on_session_recovered
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._recognizer = None
        self._stop_event = threading.Event()
        self._utterance_start: float | None = None
        self.last_error: str | None = None
        self._session_ready = threading.Event()
        self._session_active = threading.Event()

    def push_audio(self, frame):
        # Intentional no-op -- see module docstring.
        pass

    def start(self):
        if self._thread is not None:
            return
        self.last_error = None
        self._session_ready.clear()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="winrt-speech")
        self._thread.start()

    def wait_session_ready(self, timeout: float = 20.0) -> bool:
        """Block until WinRT reports the dictation session is running."""
        if self.last_error:
            return False
        if not self._session_ready.wait(timeout=timeout):
            return False
        return self.is_running() and not self.last_error

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_capturing(self) -> bool:
        """True when WinRT continuous recognition session is actively listening."""
        return self.is_running() and self._session_active.is_set()

    def stop(self):
        self._stop_event.set()
        if self._loop is not None and self._recognizer is not None:
            fut = asyncio.run_coroutine_threadsafe(self._stop_async(), self._loop)
            try:
                fut.result(timeout=5)
            except Exception:
                logger.exception("Timed out / errored stopping WinRT session")
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._session_ready.clear()
        self._session_active.clear()

    # ── background thread: owns its own asyncio loop, separate from the
    #    server's main asyncio loop, because pywinrt's async calls need one ──
    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_async())
        except Exception as e:
            logger.exception("WinRT speech pipeline crashed")
            self.last_error = str(e)
            return

    async def _main_async(self):
        missing = verify_winrt_dependencies()
        if missing:
            self.last_error = f"Missing WinRT packages: {', '.join(missing)}"
            logger.error("%s — %s", self.last_error, winrt_install_hint(missing))
            return

        import winrt.windows.foundation.collections  # noqa: F401
        import winrt.windows.globalization  # noqa: F401
        import winrt.windows.media.speechrecognition as speech

        recognizer = speech.SpeechRecognizer()
        logger.info("WinRT recognizer language: %s", recognizer.current_language.display_name)

        recognizer.constraints.append(
            speech.SpeechRecognitionTopicConstraint(
                speech.SpeechRecognitionScenario.DICTATION, "dictation"
            )
        )
        compilation = await recognizer.compile_constraints_async()
        if compilation.status != speech.SpeechRecognitionResultStatus.SUCCESS:
            self.last_error = f"compile_constraints_async failed: {compilation.status}"
            logger.error(self.last_error)
            return

        self._recognizer = recognizer

        def on_hypothesis(sender, args):
            # First partial result of a new utterance == "speech started",
            # fired well before the phrase finalizes -- mirrors the old
            # VAD-based instant UI trigger.
            if self._utterance_start is None:
                self._utterance_start = time.time()
                if self.on_speech_started:
                    try:
                        self.on_speech_started(self._utterance_start)
                    except Exception:
                        logger.exception("on_speech_started callback failed")

            # Every hypothesis call (not just the first) carries the
            # actual, growing partial text of the in-progress utterance.
            # This is the ONLY thing that fires while someone is still
            # talking -- on_result below fires once, only after WinRT
            # decides the phrase is finished. Thread it through so the
            # terminal can echo speech live instead of only after a pause.
            partial_text = (getattr(args, "hypothesis", None) and
                             (args.hypothesis.text or "").strip())
            if partial_text and self.on_partial_result:
                try:
                    self.on_partial_result(partial_text)
                except Exception:
                    logger.exception("on_partial_result callback failed")

        def on_result(sender, args):
            text = (args.result.text or "").strip()
            end_ts = time.time()
            start_ts = self._utterance_start or end_ts
            self._utterance_start = None
            if not text:
                return
            if self.on_result:
                try:
                    self.on_result(AudioChunkResult(
                        text=text,
                        # WinRT doesn't expose a Whisper-style avg_logprob;
                        # leave None. Confidence-based logic downstream
                        # (detection_orchestrator confidence bands) is
                        # untouched since it's computed from regex/semantic
                        # match quality, not this field.
                        avg_logprob=None,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        had_speech=True,
                    ))
                except Exception:
                    logger.exception("on_result callback failed")

        def on_completed(sender, args):
            # WinRT's continuous DICTATION session auto-stops itself on its
            # own internal silence timeout (SpeechRecognitionResultStatus
            # .TimeoutExceeded is the common one -- typically only a few
            # seconds of silence). This is Windows deciding to stop, not
            # anything in this app doing so. Previously nothing subscribed
            # to this event, so the mic just went silently dead until the
            # whole process was restarted. Auto-restart unless we're the
            # ones who asked it to stop.
            status = getattr(args, "status", None)
            self._session_active.clear()
            if self._stop_event.is_set():
                logger.info("WinRT session completed (status=%s) -- deliberate stop", status)
                return
            if self._loop is not None:
                asyncio.run_coroutine_threadsafe(self._restart_session(status), self._loop)

        recognizer.add_hypothesis_generated(on_hypothesis)
        recognizer.continuous_recognition_session.add_result_generated(on_result)
        recognizer.continuous_recognition_session.add_completed(on_completed)

        await self._start_session("initial")
        self._session_ready.set()

        while not self._stop_event.is_set():
            if not self._session_active.is_set() and self._recognizer is not None:
                await self._restart_session("watchdog")
            await asyncio.sleep(0.5)

    async def _start_session(self, reason: str):
        if self._stop_event.is_set() or self._recognizer is None:
            return False
        sess = self._recognizer.continuous_recognition_session
        await sess.start_async()
        self._session_active.set()
        self._utterance_start = None
        logger.info("WinRT continuous on-device dictation session started (%s)", reason)
        return True

    async def _restart_session(self, status):
        if self._stop_event.is_set() or self._recognizer is None:
            return
        sess = self._recognizer.continuous_recognition_session
        for attempt in range(5):
            try:
                try:
                    await sess.stop_async()
                except Exception:
                    pass
                await asyncio.sleep(0.15 * (attempt + 1))
                await sess.start_async()
                self._session_active.set()
                self._utterance_start = None
                logger.warning(
                    "WinRT session auto-restarted after Windows silence timeout "
                    "(status=%s, attempt=%d)",
                    status, attempt + 1,
                )
                if self.on_session_recovered:
                    try:
                        self.on_session_recovered()
                    except Exception:
                        logger.exception("on_session_recovered callback failed")
                return
            except Exception:
                logger.exception(
                    "Failed to auto-restart WinRT session (status=%s, attempt=%d)",
                    status, attempt + 1,
                )
                await asyncio.sleep(0.35 * (attempt + 1))
        self.last_error = f"WinRT session failed to restart after status={status}"
        logger.error(self.last_error)

    async def _stop_async(self):
        try:
            await self._recognizer.continuous_recognition_session.stop_async()
            logger.info("WinRT session stopped")
        except Exception:
            logger.exception("Error stopping WinRT session")

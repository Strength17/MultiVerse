"""
server.py  —  V3

WebSocket bridge between the detection backend and the browser UI.
The transcript (terminal + log + WebSocket) is printed immediately on every
spoken chunk, synchronously, before detection runs. Detection (regex,
semantic/embedding fallback, narrative tracking) runs afterward on a
dedicated background thread so it never delays the next chunk's transcript
-- a verse match prints/broadcasts separately, whenever it's ready.

Terminal output:
  [TRANSCRIPT] <text>               ← every spoken chunk, real-time
  {"triggered":true,"book":...}     ← every confirmed detection (JSONL),
                                       printed after the transcript, once
                                       background detection finishes

WebSocket messages to UI:
  hardware_profile   — once on connect
  startup_progress   — each background boot step (running/done/error)
  status             — booting/ready/starting/listening/stopped/error/idle_paused
  speech_started     — instant VAD trigger, before transcription finishes
  transcript_partial — every spoken chunk (feeds left panel)
  detection          — verse detection from live speech (Suggestions only)
  preview_verse      — verse staged for the operator, NOT on air
  broadcast_verse    — verse pushed on air (stage + projector + NDI)
  nav_state          — canonical position + whether next/prev exist
  voice_command      — a spoken navigation command was acted on
  bible_structure /
  chapter_verses /
  browser_results    — Scripture Browser data
  heartbeat          — periodic alive ping

WebSocket actions from UI:
  start_mic / stop / manual_search / search_verse
  get_bible_structure / get_chapter / lookup_reference / navigate_verse
  broadcast_verse / clear_broadcast / load_search_results / set_voice_nav
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import websockets

from console_output import mark_live_line_open, write_line

from bible_db import BibleDB
from detection_orchestrator import DetectionOrchestrator
from winrt_pipeline import WinRTSpeechPipeline, verify_winrt_dependencies, winrt_install_hint, probe_winrt_mic
from vocab_correction import correct_text, purge_bad_corrections

from paths import app_root, ensure_user_dirs, resource_root, bootstrap_install
from verse_display import (
    DisplaySettings, load_user_display, save_user_display, list_background_images,
)
from audio_devices import list_input_devices, set_default_input_device
from error_catalog import log_entry
from verse_navigation import VerseNavigator, VerseRef, parse_reference
from voice_commands import VoiceCommandParser

# ── Logging ───────────────────────────────────────────────────────────────────
def _configure_logging():
    import os
    log_dir = Path(os.environ.get("WINDOWVERSE_LOGS_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "windowverse.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


_configure_logging()
logger = logging.getLogger("windowverse.server")

# One-time self-heal: strip any bad entries (stopwords, digit-containing
# keys) that were saved to data/corrections_learned.json before these
# guards existed, so a machine with an already-corrupted file recovers
# without a manual step. Must run after logging.basicConfig (above) or its
# log line is silently dropped.
purge_bad_corrections()

from app_config import load_config
from bible_library import BibleLibrary
from ndi_sender import NDISender
from version import APP_VERSION

APP_CONFIG = load_config()


def _load_db_config() -> tuple[str, str]:
    """db_path/translation now come from the single app_config.py loader
    (see [database] in config.ini) -- this wrapper is kept so the rest of
    this module doesn't need to change how it calls it."""
    return APP_CONFIG.db_path, APP_CONFIG.translation


DB_PATH, DEFAULT_TRANSLATION = _load_db_config()

# ── Startup self-check: catch a wrong book-number scheme BEFORE a live
#    session, not mid-service. Each check word is a single ordinary word
#    from the verse (not a quote) -- just enough to confirm the DB actually
#    returned the right passage instead of something else at that number.
_ANCHOR_VERSES = [
    (10,  1,  1,  ("beginning", "created")),   # Genesis 1:1
    (430, 3,  16, ("world", "son")),            # John 3:16
    (450, 8,  1,  ("condemnation",)),           # Romans 8:1
    (660, 22, 21, ("grace", "amen")),           # Revelation 22:21
]


def verify_anchor_verses(bible_db: BibleDB) -> list[str]:
    """Look up a handful of well-known verses and sanity-check the text
    actually looks like them. Catches a wrong/mismatched book-number
    scheme (the root cause behind Song of Solomon 8:1 silently returning
    Job's text) at startup instead of live, mid-session. Returns a list of
    human-readable problem descriptions -- empty list means all good."""
    from bible_books import BOOK_NUMBER_TO_CANONICAL
    problems: list[str] = []
    for book_number, chapter, verse, expect_words in _ANCHOR_VERSES:
        book_name = BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number))
        row = bible_db.lookup_verse(book_number, chapter, verse)
        if row is None or not row.get("text"):
            problems.append(f"{book_name} {chapter}:{verse} — not found in DB")
            continue
        text_lower = row["text"].lower()
        if not any(w in text_lower for w in expect_words):
            problems.append(
                f"{book_name} {chapter}:{verse} — text doesn't look right "
                f"(got: {row['text'][:70]!r})"
            )
    return problems
HOST, PORT = "localhost", 8765

# Dated transcript log — every spoken line appended here (separate from system log)
_TRANSCRIPT_LOG = Path("logs") / f"transcript_{time.strftime('%Y-%m-%d')}.log"


def _append_transcript_log(text: str) -> None:
    if not text:
        return
    try:
        _TRANSCRIPT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_TRANSCRIPT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
    except Exception as e:
        logger.warning("Transcript log write failed: %s", e)


IDLE_TIMEOUT_SECONDS = APP_CONFIG.app.idle_timeout_seconds
SILENCE_SAVE_SECONDS = APP_CONFIG.app.silence_save_seconds

# Per-source minimum gap before auto-displaying a DIFFERENT verse than the
# one currently shown. Now sourced from config.ini [detection] instead of
# being hardcoded here -- see app_config.py.
AUTO_DISPLAY_COOLDOWN = {
    "regex":     APP_CONFIG.detection.cooldown_regex_seconds,
    "semantic":  APP_CONFIG.detection.cooldown_semantic_seconds,
    "narrative": APP_CONFIG.detection.cooldown_narrative_seconds,
}


class WindowVerseServer:
    def __init__(self):
        self.config = APP_CONFIG
        self.orchestrator = None
        self.narrative_tracker = None
        self.pipeline = None
        self.bible_db = None
        self._clients: set = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mic_stream = None

        # ── Bible version/language library (auto-discovered from disk) ──
        data_root = os.environ.get("WINDOWVERSE_DATA_ROOT") or os.environ.get(
            "WINDOWVERSE_DATA_ROOT", self.config.library.data_root
        )
        self.library = BibleLibrary(data_root)
        self.library.rescan()
        self._current_version: str = DEFAULT_TRANSLATION
        self._current_language: str = "English"
        self._show_secondary: bool = self.config.library.show_secondary_translation_by_default
        self._secondary_above: bool = self.config.library.secondary_above_primary_by_default

        self._user_dirs = ensure_user_dirs()
        self._display_path = self._user_dirs["config"] / "display_user.json"
        from narrative_settings import DetectionUserSettings, load_detection_user
        self._detection_user_path = self._user_dirs["config"] / "detection_user.json"
        self._detection_user = load_detection_user(self._detection_user_path)
        self._display = load_user_display(self._display_path)
        self._secondary_above = self._display.secondary_above
        self._display.secondary_above = self._secondary_above
        self._selected_mic: str = "System Default Microphone"
        self._session_transcript: list[dict] = []
        self._ndi_broadcasting = False

        # ── NDI output (independent subsystem — see ndi_sender.py) ──
        self.ndi_sender = NDISender(self.config.ndi)
        self.ndi_sender.set_backgrounds_dir(self._user_dirs["backgrounds"])
        self.ndi_sender.set_display(self._display)

        self._last_speech_at = 0.0
        self._idle_paused = False
        self._mic_listening = False
        self._silence_checkpoint_saved = False
        self._mic_stale_since: float | None = None
        self._last_display_at = 0.0
        self._last_displayed: dict | None = None
        self._startup_warnings: list[str] = []
        self._startup_steps: dict[str, dict] = {}
        self._ready = False

        # OSC / broadcast state
        self.osc_controller = None
        self._on_air = False
        self._opacity = 1.0
        self._active_theme = "Selah"
        self._broadcast_mode = "off"

        # ── Preview / broadcast split ────────────────────────────────────
        # _preview is what the operator is looking at; _last_displayed is
        # what the congregation is looking at. Navigation steps from the
        # preview when there is one, so arrowing through a chapter never
        # changes the screen until Broadcast.
        self.navigator: VerseNavigator | None = None
        self._preview: dict | None = None
        self._nav_ref: VerseRef | None = None
        self._voice_parser = VoiceCommandParser()
        self._apply_voice_keywords()

        # Detection (regex + semantic embedding + narrative tracking) runs
        # here, off the main event loop. A single worker keeps chunks
        # processed in the order they were spoken (no races on the
        # orchestrator's internal buffers) while never blocking the loop
        # that prints/broadcasts the NEXT transcript chunk. This is what
        # keeps the transcript real-time even when a verse match takes a
        # few hundred ms of embedding work to resolve.
        self._detection_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="windowverse-detect"
        )

    # ── Initialisation ────────────────────────────────────────────────────────
    def _report_startup(self, step_id: str, label: str, status: str, sub_percent: int | None = None):
        """Record a boot step and push it to any connected UI (thread-safe)."""
        pct = self._startup_percent(step_id, status, sub_percent)
        self._startup_steps[step_id] = {
            "step": step_id, "label": label, "status": status, "percent": pct,
        }
        payload = {
            "type": "startup_progress",
            "step": step_id, "label": label, "status": status, "percent": pct,
        }
        if sub_percent is not None:
            payload["sub_percent"] = sub_percent
        self._broadcast_threadsafe(payload)

    @staticmethod
    def _startup_percent(step_id: str, status: str, sub_percent: int | None) -> int:
        """Map step + optional sub-progress to overall 0–100."""
        bands = {
            "bible_db": (0, 8),
            "detection": (8, 12),
            "self_check": (12, 18),
            "search_index": (18, 78),
            "narrative": (78, 84),
            "speech": (84, 88),
            "mic_check": (88, 96),
            "ndi": (96, 100),
        }
        lo, hi = bands.get(step_id, (0, 100))
        if status == "done":
            return hi
        if status == "error":
            return lo
        if sub_percent is not None:
            return lo + int((hi - lo) * max(0, min(100, sub_percent)) / 100)
        return lo

    def initialize(self, db_path: str = DB_PATH,
                   external_faiss_index: str | None = None,
                   external_verse_lookup: str | None = None,
                   external_lookup_format: str = "pickle"):
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Bible DB not found at {db_path} — see README.")

        self._report_startup("bible_db", "Loading Bible database", "running")
        # Schema detection happens inside BibleDB.__init__. If the file's
        # table/columns can't be understood, this raises SchemaDetectionError
        # immediately with the details — the server refuses to start rather
        # than limping along and failing silently later mid-transcript.
        try:
            self.bible_db = BibleDB(db_path, translation=DEFAULT_TRANSLATION)
        except Exception:
            self._report_startup("bible_db", "Loading Bible database", "error")
            logger.error(
                "Failed to initialize Bible DB at '%s'. Run "
                "'python inspect_bible_db.py %s' to diagnose the schema.",
                db_path, db_path,
            )
            raise
        self._report_startup("bible_db", "Loading Bible database", "done")
        self.navigator = VerseNavigator(
            self.bible_db, wrap_books=self._detection_user.voice_nav_wrap_books,
        )

        self._report_startup("detection", "Initializing detection engine", "running")
        self.orchestrator = DetectionOrchestrator(
            self.bible_db, translation=DEFAULT_TRANSLATION,
            context_timeout_s=self.config.detection.book_memory_seconds,
            regex_threshold=self.config.detection.regex_threshold,
            min_semantic_words=self.config.detection.min_semantic_words,
            dedup_seconds=self.config.detection.dedup_seconds,
            vector_threshold=self.config.detection.vector_threshold,
            min_overlap_ratio=self.config.detection.min_overlap_ratio,
        )
        self._report_startup("detection", "Initializing detection engine", "done")

        # Fail loud, before anyone's on stage: confirm the DB is actually
        # returning the verses it claims to, not silently wrong ones.
        self._report_startup("self_check", "Verifying verse lookups", "running")
        self._startup_warnings = verify_anchor_verses(self.bible_db)
        if self._startup_warnings:
            self._report_startup("self_check", "Verifying verse lookups", "error")
            logger.error(
                "STARTUP SELF-CHECK FAILED — verse lookups may be WRONG for "
                "this DB file:\n  " + "\n  ".join(self._startup_warnings)
            )
            raise RuntimeError(
                "English NKJV database failed verification. Place NKJV.sqlite3 in "
                "Documents\\WindowVerse\\data\\NKJV\\English\\ — not the French file."
            )
        self._report_startup("self_check", "Verifying verse lookups", "done")
        logger.info("Startup self-check passed — anchor verses match expected text")

        index_cache = str(self._user_dirs["data"] / "index_cache")
        progress_cb = lambda p: self._report_startup(
            "search_index", "Preparing search index", "running", sub_percent=p,
        )

        from index_cache import cache_paths_for_db
        cached_faiss, cached_lookup = cache_paths_for_db(
            index_cache, db_path, self.orchestrator.translation,
        )
        use_db_cache = cached_faiss.exists() and cached_lookup.exists()

        if use_db_cache:
            logger.info("Loading DB-matched semantic index cache — skipping external/rebuild")
            self._report_startup("search_index", "Preparing search index", "running", sub_percent=0)
            self.orchestrator.build_index(cache_dir=index_cache, progress_callback=progress_cb)
        elif external_faiss_index and external_verse_lookup:
            logger.info("Loading pre-built FAISS index — skipping embedding work")
            self._report_startup("search_index", "Preparing search index", "running")
            self.orchestrator.load_external_index(
                external_faiss_index, external_verse_lookup,
                lookup_format=external_lookup_format,
            )
        else:
            self._report_startup("search_index", "Preparing search index", "running", sub_percent=0)
            self.orchestrator.build_index(cache_dir=index_cache, progress_callback=progress_cb)
        self._report_startup("search_index", "Preparing search index", "done")

        self._report_startup("narrative", "Starting narrative tracker", "running")
        from narrative_tracker import NarrativeTracker
        narrative_cfg = self._detection_user.narrative_thresholds()
        self.narrative_tracker = NarrativeTracker(
            embedding_model=self.orchestrator.vector_engine._model,
            bible_db=self.bible_db,
            default_translation="NKJV",
            **narrative_cfg,
        )
        self._report_startup("narrative", "Starting narrative tracker", "done")

        # ── Wire pipeline: Windows on-device dictation owns the mic directly,
        #    no chunk_seconds/transcriber args needed anymore ───────────────
        self._report_startup("speech", "Preparing speech pipeline", "running")
        self._winrt_missing = verify_winrt_dependencies()
        if self._winrt_missing:
            logger.error("WinRT speech packages missing: %s", ", ".join(self._winrt_missing))
        self.pipeline = WinRTSpeechPipeline(
            on_result=self._on_chunk_result,
            on_speech_started=self._on_speech_started,
            on_partial_result=self._on_partial_result,
            on_session_recovered=self._on_session_recovered,
        )
        self._report_startup("speech", "Preparing speech pipeline", "done")

        self._report_startup("mic_check", "Verifying microphone engine", "running")
        self._mic_probe_error = probe_winrt_mic()
        if self._mic_probe_error:
            self._report_startup("mic_check", "Verifying microphone engine", "error")
            logger.error("Mic preflight failed: %s", self._mic_probe_error)
        else:
            self._report_startup("mic_check", "Verifying microphone engine", "done")
        logger.info("Initialization complete.")

    # ── VAD instant callback ──────────────────────────────────────────────────
    def _on_session_recovered(self):
        """WinRT restarted after Windows silence timeout — keep UI in listening state."""
        if self._loop is None or not self._mic_listening:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast({"type": "status", "state": "listening"}),
            self._loop,
        )

    def _on_speech_started(self, timestamp: float):
        """Fires the instant VAD detects speech — before transcription finishes.
        Sends speech_started to UI so the left panel shows 🎤 immediately."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast({"type": "speech_started", "ts": timestamp}),
            self._loop,
        )

    # ── Live partial-transcript callback (fires continuously WHILE the
    #    person is still talking, ahead of the finalized [TRANSCRIPT] line) ──
    def _on_partial_result(self, partial_text: str):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._handle_partial_async(partial_text), self._loop
        )

    async def _handle_partial_async(self, partial_text: str):
        # In-place terminal echo, overwritten as the utterance grows --
        # never run through detection (that stays anchored to the
        # finalized on_result text only; re-running the regex/semantic
        # pipeline on every half-finished word would be wasteful and
        # premature). Padded with trailing spaces so a shorter re-print
        # doesn't leave stray characters from a longer previous one, and
        # the eventual "\n[TRANSCRIPT] ..." print (unchanged, below)
        # naturally ends this line once the phrase finalizes.
        print(f"\r[live] {partial_text}" + " " * 10, end="", flush=True)
        mark_live_line_open()
        await self._broadcast({"type": "transcript_live", "text": partial_text})

    # ── Chunk result callback ─────────────────────────────────────────────────
    def _on_chunk_result(self, chunk_result):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._handle_chunk_async(chunk_result), self._loop
        )

    async def _handle_chunk_async(self, chunk_result):
        now = time.time()

        if not chunk_result.had_speech:
            await self._check_idle(now)
            await self._broadcast({"type": "heartbeat"})
            return

        self._last_speech_at = now
        self._silence_checkpoint_saved = False
        self._mic_stale_since = None
        if self._idle_paused:
            self._idle_paused = False
            await self._broadcast({"type": "status", "state": "listening"})
            logger.info("Resumed from idle pause")

        # Fix known Windows-dictation mishears (e.g. "Nebuchadnezzar",
        # "Deuteronomy") -- but only for the copy detection matches
        # against. The RAW transcript is what gets shown/logged: "book of
        # John" is part of what was actually said and stays exactly as
        # spoken. Only the internal matching copy gets corrected.
        raw_text = chunk_result.text
        corrected_text = correct_text(raw_text)

        self._session_transcript.append({
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "text": raw_text,
        })

        # ── Transcript: terminal + log file + WebSocket, ALL immediate ────────
        # This must never wait on detection. Detection (below) includes a
        # semantic/embedding fallback that can take real time, and used to
        # run inline here -- which meant a slow verse match delayed the
        # NEXT spoken chunk from even appearing. Printing happens first and
        # unconditionally so the transcript always keeps pace with speech.
        # write_line() (not a bare print) closes out any open [live] partial
        # line first, so this never gets glued onto the end of it.
        write_line(f"[TRANSCRIPT] {raw_text}")
        _append_transcript_log(raw_text)
        await self._broadcast({"type": "transcript_partial", "text": raw_text})

        # ── Detection: scheduled in the background, not awaited here ──────────
        # _handle_chunk_async returns right after this line, freeing the
        # event loop to handle the next chunk immediately. The detection
        # result (verse match, if any) is broadcast/printed separately,
        # whenever it's ready -- "coming back below" the transcript instead
        # of blocking it. Detection matches against corrected_text (so
        # "book of John chapter 4 verse 24" still resolves), never raw_text.

        # ── Spoken navigation, checked BEFORE detection ───────────────────
        # "next verse" isn't a verse quote; if it were fed to detection it
        # would either match nothing or, worse, semantically match some
        # unrelated passage. Handled and consumed here when it's clearly a
        # command (see voice_commands.py for the false-positive rules).
        if await self._maybe_handle_voice_command(corrected_text, now):
            return

        latency_ms = (chunk_result.end_ts - chunk_result.start_ts) * 1000
        asyncio.ensure_future(self._run_detection_background(
            corrected_text, latency_ms, chunk_result.start_ts, chunk_result.end_ts, now
        ))

    def _run_detection_sync(self, text: str, latency_ms: float | None,
                             chunk_start: float, chunk_end: float, now: float):
        """Runs on the detection executor thread, never on the event loop.
        Bundles orchestrator detection + narrative tracking so both stay in
        the same chunk order they'd have had inline (single worker == no
        races on the orchestrator's/tracker's internal buffers)."""
        event = self.orchestrator.detect(
            text, latency_ms=latency_ms, chunk_start=chunk_start, chunk_end=chunk_end,
        )
        self.narrative_tracker.push_transcript(text, timestamp=now)

        if event.get("triggered"):
            # This chunk already produced its OWN explicit/semantic
            # detection -- don't also let the independent, timer-driven
            # narrative pointer fire/advance for the same chunk. The
            # narrative tracker matches against a 45s ROLLING window, not
            # just this chunk, so old (no-longer-relevant) text sitting in
            # that window could still clear its similarity floor even
            # though what was JUST said has nothing to do with it -- e.g.
            # "There's this verse that says worship in spirit and truth"
            # correctly detected John 4:24, but the same tick also printed
            # a Genesis 1:2 narrative advance purely because "In the
            # beginning God created the heavens and the earth" was still
            # sitting in the rolling window from three chunks earlier.
            # Skipping maybe_check() here (rather than just discarding its
            # result) also defers the tracker's own recheck/advance timers
            # by one chunk, so nothing is silently consumed either.
            narrative_event = None
        else:
            narrative_event = self.narrative_tracker.maybe_check(now=now)

        return event, narrative_event

    async def _run_detection_background(self, text: str, latency_ms: float | None,
                                         chunk_start: float, chunk_end: float, now: float):
        loop = asyncio.get_event_loop()
        try:
            event, narrative_event = await loop.run_in_executor(
                self._detection_executor, self._run_detection_sync,
                text, latency_ms, chunk_start, chunk_end, now,
            )
        except Exception:
            logger.exception("Background detection failed for chunk %r", text[:80])
            return

        # narrative_event is checked independently, NOT as an elif after the
        # warning branch. It previously was -- meaning any chunk where the
        # orchestrator also emitted a warning (e.g. semantic_index_empty,
        # which fires on almost every non-regex chunk) silently ate the
        # narrative_event and it was never printed or broadcast at all. That
        # is exactly why "in the beginning God created the heavens and the
        # earth" anchored the Creation passage (you can see that in the log)
        # but never produced a verse: the elif chain discarded it.
        if event.get("triggered"):
            await self._handle_detection(event, now)
        elif event.get("warning"):
            # Regex matched a reference with no DB row, or semantic search
            # is running with an empty index -- not a "detection" (nothing
            # to display), but not nothing either. Surface it to the UI
            # instead of collapsing into an indistinguishable heartbeat.
            await self._emit_system_log_from_event(event)

        if narrative_event is not None:
            # Terminal JSONL print (mirrors the unconditional print that
            # orchestrator.detect() does for regex/semantic hits). Routed
            # through write_line so it can't land mid-way through an open
            # [live] partial line.
            write_line(json.dumps(narrative_event, ensure_ascii=False))
            await self._handle_detection(narrative_event, now)

        if not event.get("triggered") and not event.get("warning") and narrative_event is None:
            await self._broadcast({"type": "heartbeat"})

    async def _silence_monitor_loop(self):
        """Auto-save transcript after silence while mic stays open."""
        while True:
            await asyncio.sleep(1.0)
            if not self._mic_listening or not self._session_transcript:
                continue
            if self._last_speech_at <= 0 or self._silence_checkpoint_saved:
                continue
            save_secs = self._detection_user.clamped_silence_save_seconds()
            if time.time() - self._last_speech_at < save_secs:
                continue
            saved = await asyncio.to_thread(self._save_session_transcript)
            self._session_transcript.clear()
            self._silence_checkpoint_saved = True
            if saved:
                await self._emit_system_log(
                    "transcript_saved",
                    f"Session saved to {saved} (auto-save after {int(save_secs)}s silence)",
                )

    async def _mic_watchdog_loop(self):
        """Recover mic if WinRT session dies while UI still shows listening."""
        while True:
            await asyncio.sleep(2.0)
            if not self._mic_listening or not self.pipeline:
                self._mic_stale_since = None
                continue
            if self.pipeline.is_capturing():
                self._mic_stale_since = None
                continue
            now = time.time()
            if self._mic_stale_since is None:
                self._mic_stale_since = now
                continue
            if now - self._mic_stale_since < 3.0:
                continue
            logger.warning("Mic not capturing after %.1fs — attempting recovery", now - self._mic_stale_since)
            try:
                await asyncio.to_thread(self._recover_mic_session)
                self._mic_stale_since = None
                await self._broadcast({"type": "status", "state": "listening"})
            except Exception as exc:
                logger.exception("Mic recovery failed")
                await self._emit_system_log("mic_start_failed", str(exc))

    def _recover_mic_session(self):
        if not self.pipeline or not self._mic_listening:
            return
        if self.pipeline.is_capturing():
            return
        if self.pipeline.is_running():
            self.pipeline.stop()
        self.pipeline.start()
        if not self.pipeline.wait_session_ready(timeout=20.0):
            detail = self.pipeline.last_error or "Microphone session did not restart"
            raise RuntimeError(detail)
        if not self.pipeline.is_capturing():
            raise RuntimeError(self.pipeline.last_error or "Microphone is not capturing after restart")

    async def _check_idle(self, now: float):
        if self._idle_paused or self._last_speech_at == 0.0:
            return
        if now - self._last_speech_at >= IDLE_TIMEOUT_SECONDS:
            self._idle_paused = True
            await self._broadcast({"type": "status", "state": "idle_paused"})
            logger.info("No speech for %ds — idle pause", IDLE_TIMEOUT_SECONDS)

    async def _handle_detection(self, event: dict, now: float):
        """Apply cooldown logic, then broadcast. Terminal print already done
        inside detect() — this is WebSocket-only.

        Speech detections are the ONLY thing that lands in the UI's
        Suggestions column (type "detection"). Whether the verse also goes
        on air is a user setting: on by default, matching the behaviour
        operators are used to, but switchable to preview-first."""
        source  = event.get("source") or "semantic"
        event["source"] = source
        min_gap = AUTO_DISPLAY_COOLDOWN.get(source, AUTO_DISPLAY_COOLDOWN["semantic"])

        # Secondary-language lookup: English primary + optional French below.
        event = self._attach_secondary_text(event)

        same_verse = (
            self._last_displayed is not None
            and self._last_displayed.get("book")    == event.get("book")
            and self._last_displayed.get("chapter") == event.get("chapter")
            and self._last_displayed.get("verse")   == event.get("verse")
        )

        if not same_verse and (now - self._last_display_at) < min_gap:
            await self._broadcast({"type": "detection", **event, "auto_display": False})
            return

        # Terminal JSONL already printed in orchestrator.detect() — no double-print here.
        auto = bool(self._detection_user.transcript_auto_broadcast)
        await self._broadcast({"type": "detection", **event, "auto_display": auto})
        if auto:
            self._last_display_at = now
            await self._go_on_air(event)
        else:
            await self._stage_preview(event)

    def _reference_results(self, query: str) -> list[dict] | None:
        """A typed reference ("John 3:16", "1 Cor 13") answers itself — the
        semantic index is only for phrase searches. Returns None when the
        query isn't a reference so the caller falls through to search."""
        if not self.navigator:
            return None
        parsed = parse_reference(query)
        if parsed is None:
            return None
        book_number, chapter, verse = parsed
        if verse is None:
            verses = self.navigator.chapter_verses(book_number, chapter)
            return [self._attach_secondary_text(v) for v in verses] or None
        ref = self.navigator.resolve_ref(book_number, chapter, verse)
        if ref is None:
            return None
        event = self.navigator.verse_event(ref, source="reference")
        return [self._attach_secondary_text(event)] if event else None

    # ── Spoken navigation ────────────────────────────────────────────────────
    def _apply_voice_keywords(self) -> None:
        """Push the operator's keyword edits into the live parser."""
        du = self._detection_user
        self._voice_parser.set_keywords(
            list(du.voice_nav_disabled_keywords or []),
            dict(du.voice_nav_custom_keywords or {}),
        )

    def _voice_keyword_payload(self) -> dict:
        from voice_commands import INTENTS, builtin_keywords

        du = self._detection_user
        disabled = {k.strip().lower() for k in (du.voice_nav_disabled_keywords or [])}
        custom = du.voice_nav_custom_keywords or {}
        builtin = builtin_keywords()
        return {
            "type": "voice_keywords",
            "intents": [
                {
                    "intent": intent,
                    "builtin": [
                        {"phrase": p, "enabled": p.strip().lower() not in disabled}
                        for p in builtin.get(intent, [])
                    ],
                    "custom": list(custom.get(intent) or []),
                }
                for intent in INTENTS
            ],
        }

    async def _update_voice_keywords(self, msg: dict) -> None:
        """add / remove / enable / disable a spoken phrase for one intent."""
        from dataclasses import replace

        from narrative_settings import save_detection_user
        from voice_commands import INTENTS

        du = self._detection_user
        op = (msg.get("op") or "").strip().lower()
        intent = (msg.get("intent") or "").strip().lower()
        phrase = (msg.get("phrase") or "").strip()
        if op in ("add", "remove") and intent not in INTENTS:
            await self._emit_system_log("generic", f"Unknown voice intent {intent!r}")
        elif op == "add" and phrase:
            custom = {k: list(v) for k, v in (du.voice_nav_custom_keywords or {}).items()}
            existing = custom.setdefault(intent, [])
            if phrase.lower() not in [e.lower() for e in existing]:
                existing.append(phrase)
            du = replace(du, voice_nav_custom_keywords=custom)
        elif op == "remove" and phrase:
            custom = {k: list(v) for k, v in (du.voice_nav_custom_keywords or {}).items()}
            custom[intent] = [p for p in custom.get(intent, []) if p.lower() != phrase.lower()]
            du = replace(du, voice_nav_custom_keywords=custom)
        elif op in ("enable", "disable") and phrase:
            disabled = [p for p in (du.voice_nav_disabled_keywords or [])
                        if p.lower() != phrase.lower()]
            if op == "disable":
                disabled.append(phrase)
            du = replace(du, voice_nav_disabled_keywords=disabled)

        self._detection_user = du
        save_detection_user(self._detection_user_path, self._detection_user)
        self._apply_voice_keywords()
        await self._broadcast(self._voice_keyword_payload())

    async def _maybe_handle_voice_command(self, text: str, now: float) -> bool:
        """Returns True when *text* was a navigation command and has been
        acted on — the caller then skips verse detection for that chunk."""
        if not self._detection_user.voice_nav_enabled or not self._mic_listening:
            return False
        if self._detection_user.voice_nav_respects_story_mode and self._narrative_is_active():
            return False
        command = self._voice_parser.parse(text, {
            "now": now,
            "finalized": True,
            "has_verse": bool(self._preview or self._last_displayed),
        })
        if command is None:
            return False

        logger.info("Voice command: %s (%.2f) from %r",
                    command.intent, command.confidence, command.matched_phrase)
        await self._broadcast({
            "type": "voice_command",
            "intent": command.intent,
            "confidence": command.confidence,
            "matched_phrase": command.matched_phrase,
        })
        auto = bool(self._detection_user.voice_nav_auto_broadcast)
        if command.intent == "next":
            await self._navigate(1, auto_broadcast=auto)
        elif command.intent == "prev":
            await self._navigate(-1, auto_broadcast=auto)
        elif command.intent == "repeat":
            await self._go_on_air(self._last_displayed or self._preview)
        elif command.intent == "clear":
            await self._clear_broadcast()
        elif command.intent == "broadcast":
            await self._go_on_air(self._preview or self._last_displayed)
        return True

    def _narrative_is_active(self) -> bool:
        """True while the narrative tracker is following a story — spoken
        'next' during story mode belongs to the story, not the operator."""
        tracker = self.narrative_tracker
        return bool(tracker and tracker.state.passage is not None)

    # ── Preview / broadcast pipeline ─────────────────────────────────────────
    def _ref_from_event(self, event: dict | None) -> VerseRef | None:
        if not event or not self.navigator:
            return None
        return self.navigator.resolve_ref(
            event.get("book_number") or event.get("book"),
            event.get("chapter"), event.get("verse"),
        )

    def _nav_state_payload(self) -> dict:
        ref = self._nav_ref
        payload: dict = {
            "type": "nav_state",
            "reference": ref.to_dict() if ref else None,
            "has_next": False,
            "has_prev": False,
            "on_air": bool(self._last_displayed) and self._on_air,
            "preview": self._preview,
        }
        if ref and self.navigator:
            payload["has_next"] = self.navigator.next_verse(ref) is not None
            payload["has_prev"] = self.navigator.prev_verse(ref) is not None
        return payload

    async def _stage_preview(self, event: dict | None, source: str | None = None):
        """Show a verse to the operator only — no stage, no NDI, no projector."""
        if not event:
            return
        event = dict(event)
        if source:
            event["source"] = source
        event.setdefault("triggered", True)
        event = self._attach_secondary_text(event)
        self._preview = event
        self._nav_ref = self._ref_from_event(event) or self._nav_ref
        await self._broadcast({"type": "preview_verse", **event})
        await self._broadcast(self._nav_state_payload())

    async def _go_on_air(self, event: dict | None):
        """Push a verse to stage, projector and NDI. Everything that ends up
        in front of the congregation goes through here."""
        if not event:
            return
        event = self._attach_secondary_text(dict(event))
        self._last_displayed = event
        self._last_display_at = time.time()
        self._on_air = True
        # The preview has been "taken" — clearing it means the arrows now
        # follow what's on air instead of a stale staged verse.
        self._preview = None
        self._nav_ref = self._ref_from_event(event) or self._nav_ref
        await self._broadcast({"type": "broadcast_verse", **event})
        try:
            self._push_ndi(event)
        except Exception:
            logger.exception("NDI update failed — display pipeline unaffected")
        await self._broadcast(self._nav_state_payload())

    async def _clear_broadcast(self):
        self._on_air = False
        self._last_displayed = None
        await self._broadcast({"type": "broadcast_state", "on_air": False})
        try:
            self.ndi_sender.clear()
            self._ndi_broadcasting = False
        except Exception:
            logger.exception("NDI clear failed")
        await self._broadcast(self._nav_state_payload())

    async def _navigate(self, direction: int, *, auto_broadcast: bool | None = None):
        """Step one verse from the current position (preview first, then
        whatever is on air). Stops at the ends of the canon unless the user
        has asked navigation to wrap."""
        if not self.navigator:
            return
        ref = self._nav_ref or self._ref_from_event(self._preview) or self._ref_from_event(self._last_displayed)
        if ref is None:
            await self._emit_system_log(
                "generic", "Nothing to navigate from — pick a verse first.",
            )
            return
        target = self.navigator.navigate(ref, direction)
        if target is None:
            await self._emit_system_log(
                "generic",
                "End of the Bible reached — navigation stops at Genesis 1:1 / Revelation 22:21.",
            )
            return
        event = self.navigator.verse_event(target, source="navigation")
        if not event:
            return
        self._nav_ref = target
        if auto_broadcast is None:
            # Nothing staged and something already on air => the operator is
            # walking the live verse forward, so keep the screen following.
            auto_broadcast = bool(self._last_displayed) and self._preview is None
        if auto_broadcast:
            await self._go_on_air(event)
        else:
            await self._stage_preview(event)

    def _push_ndi(self, event: dict):
        if not self._display.ndi_output_enabled:
            return
        self._display.secondary_above = self._secondary_above
        self.ndi_sender.set_display(self._display)
        self.ndi_sender.update(
            reference=event.get("reference_display")
            or f"{event.get('book')} {event.get('chapter')}:{event.get('verse')}",
            text=event.get("text", ""),
            secondary_text=event.get("secondary_text"),
        )
        self._ndi_broadcasting = True
        self._broadcast_threadsafe({
            "type": "ndi_state",
            "enabled": True,
            "broadcasting": True,
            "available": self.ndi_sender._available,
        })

    async def _emit_system_log(self, code: str, message: str, fix: str | None = None):
        entry = log_entry(code, message, fix)
        entry["ts"] = time.strftime("%H:%M:%S")
        await self._broadcast(entry)

    async def _emit_system_log_from_event(self, event: dict):
        from error_catalog import CATALOG
        warning = event.get("warning", "generic")
        code = warning if warning in CATALOG else "generic"
        detail = event.get("detail") or event.get("reason") or ""
        book = event.get("book")
        ch, v = event.get("chapter"), event.get("verse")
        if book and ch and v:
            msg = f"Heard {book} {ch}:{v}" + (f" — {detail}" if detail else "")
        else:
            msg = detail or str(warning)
        await self._emit_system_log(code, msg)

    def _search_query(self, query: str, mode: str = "all") -> dict | None:
        """Search: explicit refs, paraphrase, stories — or a single mode."""
        if not query or not query.strip():
            return None
        corrected = correct_text(query.strip())
        mode = (mode or "all").lower()
        if mode == "explicit":
            regex_hit = self.orchestrator._run_regex_only(corrected)
            return regex_hit if regex_hit and regex_hit.get("triggered") else None
        if mode == "paraphrase":
            if not self.orchestrator._index_built:
                return None
            return self.orchestrator.vector_engine.search_paraphrase(corrected)
        if mode == "narrative":
            if not self.narrative_tracker:
                return None
            return self.narrative_tracker.search_query(corrected)
        regex_hit = self.orchestrator._run_regex_only(corrected)
        if regex_hit and regex_hit.get("triggered"):
            return regex_hit
        if self.orchestrator._index_built:
            paraphrase_hit = self.orchestrator.vector_engine.search_paraphrase(corrected)
            if paraphrase_hit:
                return paraphrase_hit
        if self.narrative_tracker:
            return self.narrative_tracker.search_query(corrected)
        return None

    def _search_query_multi(self, query: str, testament: str = "all") -> dict:
        """Forgiving multi-match search grouped by Old and New Testament."""
        from bible_books import book_testament, testament_matches

        empty = {"results": [], "old_testament": [], "new_testament": []}
        if not query or not query.strip():
            return empty

        corrected = correct_text(query.strip())
        testament = (testament or "all").strip().lower()
        hits: list[dict] = []
        seen: set[tuple] = set()

        def add_hit(raw: dict | None, match_type: str) -> None:
            if not raw:
                return
            book = raw.get("book")
            chapter = raw.get("chapter")
            verse = raw.get("verse")
            if not book or chapter is None or verse is None:
                return
            book_number = int(raw.get("book_number") or 0)
            if not testament_matches(book_number, testament):
                return
            key = (book, chapter, verse)
            if key in seen:
                return
            seen.add(key)
            entry = {
                **raw,
                "match_type": match_type,
                "testament": book_testament(book_number),
                "triggered": True,
            }
            hits.append(entry)

        regex_hit = self.orchestrator._run_regex_only(corrected)
        if regex_hit and regex_hit.get("triggered"):
            add_hit({**regex_hit, "source": "explicit"}, "explicit")

        if self.orchestrator._index_built:
            for paraphrase_hit in self.orchestrator.vector_engine.search_paraphrase_multi(
                corrected, testament=testament,
            ):
                add_hit(paraphrase_hit, "paraphrase")

        if self.narrative_tracker:
            narrative_hit = self.narrative_tracker.search_query(corrected, min_score=0.38)
            add_hit(narrative_hit, "narrative")

        hits.sort(key=lambda h: h.get("confidence") or 0, reverse=True)
        ot = [h for h in hits if h.get("testament") == "OT"]
        nt = [h for h in hits if h.get("testament") == "NT"]
        return {"results": hits, "old_testament": ot, "new_testament": nt}

    def _audio_devices_payload(self) -> dict:
        return {
            "type": "audio_devices",
            "devices": list_input_devices(),
            "selected": self._selected_mic,
        }

    def _mic_progress(self, step: str, percent: int, label: str = ""):
        self._broadcast_threadsafe({
            "type": "mic_startup_progress",
            "step": step, "percent": percent, "label": label,
        })

    def _refresh_ndi_display(self):
        """Re-push the current on-air verse to NDI (e.g. after layout toggle)."""
        if not self._last_displayed:
            return
        self._push_ndi(self._last_displayed)

    async def _broadcast(self, message: dict):
        if not self._clients:
            return
        payload = json.dumps(message)
        await asyncio.gather(
            *(client.send(payload) for client in list(self._clients)),
            return_exceptions=True,
        )

    # ── Mic / file control ────────────────────────────────────────────────────
    def start_mic(self):
        if self.pipeline is None:
            raise RuntimeError("Speech pipeline not initialized")
        self._mic_progress("starting_mic", 0, "Preparing microphone…")
        set_default_input_device(self._selected_mic)
        self._mic_progress("setting_device", 33, "Selecting audio device…")
        self.pipeline.start()
        self._mic_progress("opening_session", 66, "Opening microphone session…")
        if not self.pipeline.wait_session_ready(timeout=20.0):
            detail = self.pipeline.last_error or "Microphone session did not start in time"
            raise RuntimeError(detail)
        if not self.pipeline.is_running():
            detail = self.pipeline.last_error or "Microphone session stopped unexpectedly"
            raise RuntimeError(detail)
        self._mic_progress("ready", 100, "Microphone ready")
        self._mic_listening = True
        self._silence_checkpoint_saved = False
        self._mic_stale_since = None
        self._last_speech_at = time.time()
        logger.info("Mic input started (Windows on-device dictation)")

    def stop(self):
        self._mic_listening = False
        self._mic_stale_since = None
        if self.pipeline:
            self.pipeline.stop()
        # Note: deliberately NOT shutting down self._detection_executor here.
        # This stop() is reachable from the UI's "stop mic" button, and the
        # mic can be restarted afterward (start_mic) in the same process --
        # killing the executor here would break detection on that restart.
        # concurrent.futures registers its own atexit handler, so the
        # worker thread is still joined cleanly when the process exits.
        logger.info("Stopped")

    def _save_session_transcript(self) -> str | None:
        if not self._session_transcript:
            return None
        out_dir = self._user_dirs["transcription"]
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        path = out_dir / f"WindowVerse_{stamp}.txt"
        lines = [
            f"WindowVerse session — saved {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]
        for row in self._session_transcript:
            lines.append(f"[{row['ts']}] {row['text']}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Session transcript saved to %s", path)
        return str(path)

    def _apply_display_patch(self, patch: dict):
        for key, val in patch.items():
            if hasattr(self._display, key):
                setattr(self._display, key, val)
        if "secondary_above" in patch:
            self._secondary_above = bool(patch["secondary_above"])
        self._display.secondary_above = self._secondary_above
        save_user_display(self._display_path, self._display)
        self.ndi_sender.set_display(self._display)
        if self._last_displayed:
            self._last_displayed = self._attach_secondary_text(self._last_displayed)
        self._refresh_ndi_display()

    # ── WebSocket handling ────────────────────────────────────────────────────
    async def _send_boot_state(self, websocket):
        """Everything a newly-connected UI needs to mirror current boot status."""
        await websocket.send(json.dumps({
            "type": "hardware_profile",
            "os": "Windows 11",
            "app_version": APP_VERSION,
            "cpu": None,
            "cpu_cores": None,
            "ram_gb": None,
            "gpus": [],
            "has_nvidia": False,
            "nvidia_name": None,
            "has_other_gpu": False,
            "other_gpu_name": None,
            "model_size": "system-managed",
            "compute_type": "native",
            "chunk_seconds": "continuous",
        }))
        for step in self._startup_steps.values():
            await websocket.send(json.dumps({"type": "startup_progress", **step}))
        state = "ready" if self._ready else "booting"
        await websocket.send(json.dumps({"type": "status", "state": state}))
        if self._ready:
            self.library.rescan()
            await websocket.send(json.dumps({
                "type": "library",
                "versions": self.library.list_versions(),
                "current_version": self._current_version,
                "current_language": self._current_language,
                "secondary_language": self.library.secondary_language_for(
                    self._current_version, self._current_language),
                "show_secondary": self._show_secondary,
                "secondary_above": self._secondary_above,
            }))
            await websocket.send(json.dumps({
                "type": "display_state",
                "settings": self._display.to_ui_dict(),
                "backgrounds": list_background_images(self._user_dirs["backgrounds"]),
            }))
            await websocket.send(json.dumps({
                "type": "detection_state",
                "settings": self._detection_user.to_ui_dict(),
            }))
            await websocket.send(json.dumps(self._voice_keyword_payload()))
            await websocket.send(json.dumps({
                "type": "ndi_state",
                "enabled": self._display.ndi_output_enabled,
                "broadcasting": False,
                "available": getattr(self.ndi_sender, "_available", False),
            }))
            await websocket.send(json.dumps(self._audio_devices_payload()))
        # Sent even while still booting so the reference bar and arrows
        # start out in a known (disabled) state instead of guessing.
        await websocket.send(json.dumps(self._nav_state_payload()))

    async def handle_client(self, websocket):
        self._clients.add(websocket)
        logger.info("UI connected (%d total)", len(self._clients))
        try:
            await self._send_boot_state(websocket)
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._dispatch(msg, websocket)
        finally:
            self._clients.discard(websocket)
            logger.info("UI disconnected (%d remaining)", len(self._clients))

    async def _dispatch(self, msg: dict, websocket):
        action = msg.get("action")
        if action == "start_mic":
            if not self._ready:
                await self._emit_system_log(
                    "not_ready",
                    "Backend is still loading — wait for all startup steps to finish.",
                )
                return
            await self._broadcast({"type": "status", "state": "starting"})
            try:
                await asyncio.to_thread(self.start_mic)
            except Exception as exc:
                logger.exception("start_mic failed")
                fix = None
                err = str(exc).lower()
                if "winrt" in err or "globalization" in err or "no module named" in err:
                    fix = winrt_install_hint()
                await self._emit_system_log("mic_start_failed", str(exc), fix=fix)
                await self._broadcast({"type": "status", "state": "ready"})
                return
            await self._broadcast({"type": "status", "state": "listening"})
            self._mic_listening = True
            self._silence_checkpoint_saved = False
            self._mic_stale_since = None
            self._last_speech_at = time.time()
        elif action == "stop":
            saved = await asyncio.to_thread(self._save_session_transcript)
            self._mic_listening = False
            self._silence_checkpoint_saved = False
            self._mic_stale_since = None
            await asyncio.to_thread(self.stop)
            await self._broadcast({"type": "status", "state": "ready"})
            if saved:
                await self._emit_system_log(
                    "transcript_saved", f"Session saved to {saved}",
                )
        elif action == "search_verse":
            query = msg.get("query", "")
            testament = msg.get("testament") or self._detection_user.clamped_search_testament()
            # A typed reference answers itself; only phrases need the index.
            direct = self._reference_results(query)
            if direct is not None:
                await websocket.send(json.dumps({
                    "type": "search_results",
                    "query": query,
                    "testament": testament,
                    "results": direct,
                    "old_testament": [],
                    "new_testament": [],
                }))
                if len(direct) == 1:
                    await self._stage_preview(direct[0], source="reference")
                return
            try:
                grouped = await asyncio.to_thread(self._search_query_multi, query, testament)
                for bucket in ("results", "old_testament", "new_testament"):
                    grouped[bucket] = [
                        self._attach_secondary_text(hit)
                        for hit in grouped.get(bucket) or []
                    ]
            except Exception:
                logger.exception("Search failed for query %r", query)
                grouped = {"results": [], "old_testament": [], "new_testament": []}
            await websocket.send(json.dumps({
                "type": "search_results",
                "query": query,
                "testament": testament,
                **grouped,
            }))
        elif action == "manual_search":
            query = msg.get("query", "")
            try:
                result = await asyncio.to_thread(self._search_query, query)
                if result:
                    result = self._attach_secondary_text(result)
            except Exception:
                logger.exception("Manual search failed for query %r", query)
                result = None
            await websocket.send(json.dumps({
                "type": "manual_search_result",
                "query": query,
                "result": result,
            }))
            # A manual search is the operator looking something up, not the
            # preacher quoting it — it stages, it never goes straight on air.
            if result:
                await self._stage_preview(result, source="search")
        elif action == "get_bible_structure":
            testament = (msg.get("testament") or "all").lower()
            books = self.navigator.list_books(testament) if self.navigator else []
            await websocket.send(json.dumps({
                "type": "bible_structure",
                "testament": testament,
                "books": books,
            }))
        elif action == "get_chapter":
            if not self.navigator:
                return
            book_number = msg.get("book_number") or msg.get("book")
            ref = self.navigator.resolve_ref(book_number, msg.get("chapter"))
            if ref is None:
                await self._emit_system_log(
                    "generic", f"No chapter data for {book_number} {msg.get('chapter')}",
                )
                return
            verses = await asyncio.to_thread(
                self.navigator.chapter_verses, ref.book_number, ref.chapter,
            )
            await websocket.send(json.dumps({
                "type": "chapter_verses",
                "book_number": ref.book_number,
                "book": ref.book,
                "chapter": ref.chapter,
                "chapters": self.navigator.list_chapters(ref.book_number),
                "verses": verses,
            }))
        elif action == "lookup_reference":
            if not self.navigator:
                return
            ref = self.navigator.resolve_ref(
                msg.get("book"), msg.get("chapter"), msg.get("verse"),
            )
            if ref is None:
                await self._emit_system_log(
                    "generic",
                    f"Could not find {msg.get('book')} {msg.get('chapter')}:{msg.get('verse')} "
                    f"in {self._current_version} ({self._current_language}).",
                )
                return
            event = self.navigator.verse_event(ref, source="manual")
            await self._stage_preview(event)
            if msg.get("broadcast"):
                await self._go_on_air(event)
        elif action == "navigate_verse":
            direction = 1 if int(msg.get("direction", 1)) >= 0 else -1
            await self._navigate(direction, auto_broadcast=msg.get("broadcast"))
        elif action == "stage_preview":
            # The operator clicked a verse somewhere in the UI. The server
            # has to know about it too, otherwise the next nav_state (which
            # carries the server's idea of the preview) wipes it and
            # Broadcast has nothing to send.
            verse = msg.get("verse")
            if verse:
                await self._stage_preview(verse, source=verse.get("source") or "manual")
        elif action == "broadcast_verse":
            event = msg.get("verse") or self._preview
            if not event:
                await self._emit_system_log("generic", "Nothing in preview to broadcast.")
                return
            await self._go_on_air(event)
        elif action == "clear_broadcast":
            await self._clear_broadcast()
        elif action == "clear_preview":
            self._preview = None
            await self._broadcast({"type": "preview_cleared"})
            await self._broadcast(self._nav_state_payload())
        elif action == "load_search_results":
            # Search → Scripture Browser handoff. The browser owns the list;
            # a single result is staged for preview but still needs Broadcast.
            query = msg.get("query", "")
            testament = msg.get("testament") or self._detection_user.clamped_search_testament()
            results = self._reference_results(query)
            if results is None:
                try:
                    grouped = await asyncio.to_thread(self._search_query_multi, query, testament)
                    results = [self._attach_secondary_text(hit) for hit in grouped.get("results") or []]
                except Exception:
                    logger.exception("Browser search failed for query %r", query)
                    results = []
            await websocket.send(json.dumps({
                "type": "browser_results",
                "query": query,
                "testament": testament,
                "results": results,
            }))
            if len(results) == 1:
                await self._stage_preview(results[0], source="search")
        elif action == "get_voice_keywords":
            await websocket.send(json.dumps(self._voice_keyword_payload()))
        elif action == "set_voice_keywords":
            await self._update_voice_keywords(msg)
        elif action == "set_voice_nav":
            from dataclasses import replace
            from narrative_settings import save_detection_user

            du = self._detection_user
            for key in ("voice_nav_enabled", "voice_nav_auto_broadcast",
                        "voice_nav_wrap_books", "voice_nav_respects_story_mode",
                        "transcript_auto_broadcast"):
                if key in msg:
                    du = replace(du, **{key: bool(msg[key])})
            self._detection_user = du
            save_detection_user(self._detection_user_path, self._detection_user)
            if self.navigator:
                self.navigator.wrap_books = du.voice_nav_wrap_books
            self._voice_parser.reset()
            await self._broadcast({
                "type": "detection_state",
                "settings": self._detection_user.to_ui_dict(),
            })
        elif action == "switch_version":
            await self._switch_version(
                msg.get("version"), msg.get("language", "English"), websocket
            )
        elif action == "set_show_translation":
            self._show_secondary = bool(msg.get("enabled", False))
            await self._broadcast({
                "type": "broadcast_state", "show_secondary": self._show_secondary
            })
            await self._refresh_last_display_secondary()
            self._refresh_ndi_display()
        elif action == "set_secondary_order":
            self._secondary_above = bool(msg.get("above", False))
            self._display.secondary_above = self._secondary_above
            save_user_display(self._display_path, self._display)
            self._broadcast_threadsafe({
                "type": "broadcast_state", "secondary_above": self._secondary_above
            })
            self._refresh_ndi_display()
        elif action == "set_display":
            self._apply_display_patch(msg.get("settings") or {})
            await self._broadcast({
                "type": "display_state",
                "settings": self._display.to_ui_dict(),
                "backgrounds": list_background_images(self._user_dirs["backgrounds"]),
            })
        elif action == "set_detection":
            from dataclasses import replace
            from narrative_settings import save_detection_user

            du = self._detection_user
            if "narrative_sensitivity" in msg:
                du = replace(du, narrative_sensitivity=int(msg["narrative_sensitivity"]))
            if "search_testament" in msg:
                st = str(msg["search_testament"]).strip().lower()
                if st in ("all", "ot", "nt"):
                    du = replace(du, search_testament=st)
            if "silence_save_seconds" in msg:
                du = replace(
                    du,
                    silence_save_seconds=max(5.0, min(600.0, float(msg["silence_save_seconds"]))),
                )
            self._detection_user = du
            save_detection_user(self._detection_user_path, self._detection_user)
            if self.narrative_tracker:
                self.narrative_tracker.apply_thresholds(
                    **self._detection_user.narrative_thresholds()
                )
            await self._broadcast({
                "type": "detection_state",
                "settings": self._detection_user.to_ui_dict(),
            })
        elif action == "get_audio_devices":
            await websocket.send(json.dumps(self._audio_devices_payload()))
        elif action == "set_mic":
            self._selected_mic = msg.get("name") or "System Default Microphone"
            await self._broadcast(self._audio_devices_payload())
        elif action == "set_ndi_enabled":
            self._display.ndi_output_enabled = bool(msg.get("enabled", True))
            save_user_display(self._display_path, self._display)
            if not self._display.ndi_output_enabled:
                try:
                    self.ndi_sender.clear()
                except Exception:
                    pass
                self._ndi_broadcasting = False
            await self._broadcast({
                "type": "ndi_state",
                "enabled": self._display.ndi_output_enabled,
                "broadcasting": self._ndi_broadcasting,
                "available": getattr(self.ndi_sender, "_available", False),
            })
        elif action == "ndi_preview":
            preview = {
                "book": "John", "book_number": 430, "chapter": 3, "verse": 16,
                "text": "For God so loved the world, that he gave his only begotten Son.",
            }
            preview = self._attach_secondary_text(preview)
            try:
                self.ndi_sender.set_display(self._display)
                self.ndi_sender.update(
                    reference="John 3:16",
                    text=preview["text"],
                    secondary_text=preview.get("secondary_text"),
                )
            except Exception:
                logger.exception("NDI preview failed")
            await websocket.send(json.dumps({"type": "ndi_preview_sent"}))
        else:
            logger.warning("Unknown action: %s", action)

    def _resolve_book_number(self, event: dict) -> int | None:
        """Canonical book number for cross-language verse lookup."""
        bn = event.get("book_number")
        if bn is not None:
            return int(bn)
        book = (event.get("book") or "").strip()
        if not book:
            return None
        from bible_books import BOOKS
        target = book.lower()
        for num, name, _abbrevs in BOOKS:
            if name.lower() == target:
                return num
        return None

    def _attach_secondary_text(self, event: dict) -> dict:
        """Look up the French (secondary) verse for every display event.
        Secondary text is for Live Output / NDI only — never added to terminal logs."""
        out = dict(event)
        out.pop("secondary_text", None)
        out.pop("secondary_language", None)
        if out.get("book") is None or out.get("chapter") is None or out.get("verse") is None:
            return out
        from verse_display import PRIMARY_VERSION_LABEL, SECONDARY_VERSION_LABEL, bilingual_reference
        from bible_books import french_book_name
        out["primary_version_label"] = PRIMARY_VERSION_LABEL
        book = out.get("book")
        chapter, verse = out.get("chapter"), out.get("verse")
        if book and chapter is not None and verse is not None:
            out["book_french"] = french_book_name(book)
            out["reference_display"] = bilingual_reference(book, chapter, verse, out["book_french"])
        secondary_language = self.library.secondary_language_for(
            self._current_version, self._current_language
        )
        book_number = self._resolve_book_number(out)
        if not (secondary_language and book_number):
            return out
        try:
            sec_db = self.library.get_db(self._current_version, secondary_language)
            sec_row = sec_db.lookup_verse(
                book_number, out["chapter"], out["verse"]
            ) if sec_db else None
        except Exception:
            logger.exception("Secondary-language lookup failed — showing primary only")
            sec_row = None
        if sec_row and sec_row.get("text"):
            out["secondary_language"] = secondary_language
            out["secondary_text"] = sec_row["text"]
            out["book_number"] = book_number
            out["secondary_version_label"] = SECONDARY_VERSION_LABEL
        return out

    async def _refresh_last_display_secondary(self):
        if not self._last_displayed:
            return
        event = self._attach_secondary_text(self._last_displayed)
        self._last_displayed = event
        await self._broadcast({"type": "detection", **event, "auto_display": True})
        try:
            self._push_ndi(event)
        except Exception:
            logger.exception("NDI update failed after secondary toggle")

    async def _switch_version(self, version: str | None, language: str, websocket):
        """
        Swaps the active Bible DB + rebuilds the detection index for a
        different version/language. Runs the (potentially slow, CPU-bound)
        rebuild in a worker thread so it never blocks the event loop --
        the transcript/mic keep working while it happens. On any failure
        the PREVIOUS orchestrator is kept running untouched; nothing about
        version-switching can leave the app in a broken detection state.
        """
        if not version:
            return
        db = self.library.get_db(version, language)
        if db is None:
            await self._emit_system_log(
                "db_schema_error",
                f"No usable Bible DB found for {version} / {language}",
            )
            return

        if self.pipeline and self.pipeline.is_running():
            restore_state = "idle_paused" if self._idle_paused else "listening"
        else:
            restore_state = "ready"

        await self._broadcast({"type": "status", "state": "switching_version"})

        def _rebuild():
            new_orch = DetectionOrchestrator(
                db, translation=version,
                context_timeout_s=self.config.detection.book_memory_seconds,
                regex_threshold=self.config.detection.regex_threshold,
                min_semantic_words=self.config.detection.min_semantic_words,
                dedup_seconds=self.config.detection.dedup_seconds,
                vector_threshold=self.config.detection.vector_threshold,
                min_overlap_ratio=self.config.detection.min_overlap_ratio,
            )
            new_orch.build_index()
            return new_orch

        try:
            new_orchestrator = await asyncio.to_thread(_rebuild)
        except Exception:
            logger.exception("Version switch to %s/%s failed — keeping previous version", version, language)
            await self._emit_system_log(
                "db_schema_error",
                f"{version} ({language}) failed to build — kept the previous version running",
            )
            await self._broadcast({"type": "status", "state": restore_state})
            return

        self.orchestrator = new_orchestrator
        self.bible_db = db
        self.navigator = VerseNavigator(
            db, wrap_books=self._detection_user.voice_nav_wrap_books,
        )
        self._current_version = version
        self._current_language = language
        self._last_displayed = None
        self._preview = None
        self._nav_ref = None
        self._last_display_at = 0.0
        logger.info("Switched active Bible version to %s / %s", version, language)

        await self._broadcast({
            "type": "library",
            "versions": self.library.list_versions(),
            "current_version": self._current_version,
            "current_language": self._current_language,
            "secondary_language": self.library.secondary_language_for(
                self._current_version, self._current_language),
            "show_secondary": self._show_secondary,
            "secondary_above": self._secondary_above,
        })
        await self._broadcast({"type": "status", "state": restore_state})

    # ── OSC broadcast state ───────────────────────────────────────────────────
    def queue_advance(self, direction: int):
        """Thread-safe entry point for OSC /pew/next and /pew/prev — steps
        the canonical navigator and pushes the result on air."""
        loop = self._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._navigate(1 if direction >= 0 else -1, auto_broadcast=True), loop,
        )

    def set_on_air(self, value: bool):
        self._on_air = value
        self._broadcast_threadsafe({"type": "broadcast_state", "on_air": value})
        if not value:
            try:
                self.ndi_sender.clear()
            except Exception:
                logger.exception("NDI clear failed")

    def set_opacity(self, value: float):
        self._opacity = max(0.0, min(1.0, value))
        self._broadcast_threadsafe({"type": "broadcast_state", "opacity": self._opacity})

    def set_theme(self, theme_name: str | None):
        if theme_name:
            self._active_theme = theme_name
            self._broadcast_threadsafe({"type": "broadcast_state", "theme": theme_name})

    def set_broadcast_mode(self, mode_name: str | None):
        if mode_name:
            self._broadcast_mode = mode_name
            self._broadcast_threadsafe({"type": "broadcast_state", "mode": mode_name})

    def set_confidence_threshold(self, value: float):
        logger.info("Confidence threshold updated: %.2f", value)
        self._broadcast_threadsafe({"type": "broadcast_state", "confidence_threshold": value})

    def _broadcast_threadsafe(self, message: dict):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

    async def _rescan_library_loop(self):
        interval = self.config.library.rescan_interval_seconds
        if interval <= 0:
            return
        while True:
            await asyncio.sleep(interval)
            before = {v["version"]: v["languages"] for v in self.library.list_versions()}
            self.library.rescan()
            after = {v["version"]: v["languages"] for v in self.library.list_versions()}
            if before != after:
                logger.info("Bible library changed on disk — notifying connected UIs")
                await self._broadcast({
                    "type": "library",
                    "versions": self.library.list_versions(),
                    "current_version": self._current_version,
                    "current_language": self._current_language,
                    "secondary_language": self.library.secondary_language_for(
                        self._current_version, self._current_language),
                    "show_secondary": self._show_secondary,
                    "secondary_above": self._secondary_above,
                })

    # ── Run ───────────────────────────────────────────────────────────────────
    async def run(self, *, db_path: str = DB_PATH,
                  external_faiss_index: str | None = None,
                  external_verse_lookup: str | None = None,
                  external_lookup_format: str = "pickle"):
        self._loop = asyncio.get_running_loop()

        from static_server import start_static_server, HTTP_PORT
        ui_root = resource_root() / "ui"
        if not ui_root.exists():
            ui_root = app_root() / "ui"
        start_static_server(ui_root, self._user_dirs["backgrounds"], port=HTTP_PORT)

        async with websockets.serve(self.handle_client, HOST, PORT):
            logger.info("WindowVerse listening on ws://%s:%d — booting", HOST, PORT)
            await self._broadcast({"type": "status", "state": "booting"})

            try:
                await asyncio.to_thread(
                    self.initialize,
                    db_path,
                    external_faiss_index,
                    external_verse_lookup,
                    external_lookup_format,
                )
            except Exception as exc:
                logger.exception("Startup failed")
                await self._broadcast({
                    "type": "status", "state": "error", "detail": str(exc),
                })
                try:
                    await asyncio.Future()
                finally:
                    pass
                return

            from osc_control import OSCController
            self.osc_controller = OSCController(self)
            await self.osc_controller.start()

            self._report_startup("ndi", "Starting NDI output", "running")
            await asyncio.to_thread(self.ndi_sender.start)
            self._report_startup("ndi", "Starting NDI output", "done")

            asyncio.create_task(self._rescan_library_loop())
            asyncio.create_task(self._silence_monitor_loop())
            asyncio.create_task(self._mic_watchdog_loop())

            self._ready = True
            await self._broadcast({"type": "status", "state": "ready"})
            self.library.rescan()
            await self._broadcast({
                "type": "library",
                "versions": self.library.list_versions(),
                "current_version": self._current_version,
                "current_language": self._current_language,
                "secondary_language": self.library.secondary_language_for(
                    self._current_version, self._current_language),
                "show_secondary": self._show_secondary,
                "secondary_above": self._secondary_above,
            })
            await self._broadcast({
                "type": "display_state",
                "settings": self._display.to_ui_dict(),
                "backgrounds": list_background_images(self._user_dirs["backgrounds"]),
            })
            await self._broadcast({
                "type": "detection_state",
                "settings": self._detection_user.to_ui_dict(),
            })
            await self._broadcast({
                "type": "ndi_state",
                "enabled": self._display.ndi_output_enabled,
                "broadcasting": False,
                "available": getattr(self.ndi_sender, "_available", False),
            })
            logger.info("Startup complete — press Start in the UI to open the microphone")
            try:
                await asyncio.Future()
            finally:
                self.ndi_sender.stop()


# ── Entry point ───────────────────────────────────────────────────────────────
DEFAULT_FAISS  = "data/bible_vectors.index"
DEFAULT_LOOKUP = "data/bible_verse_map.pkl"


def main():
    import os
    os.chdir(app_root())
    bootstrap_install()
    global APP_CONFIG, DB_PATH, DEFAULT_TRANSLATION
    APP_CONFIG = load_config()
    DB_PATH, DEFAULT_TRANSLATION = _load_db_config()

    server = WindowVerseServer()

    faiss_index = os.environ.get("WINDOWVERSE_FAISS_INDEX")
    verse_lookup = os.environ.get("WINDOWVERSE_VERSE_LOOKUP")

    data_root = Path(
        os.environ.get("WINDOWVERSE_DATA_ROOT")
        or os.environ.get("WINDOWVERSE_DATA_ROOT", APP_CONFIG.library.data_root)
    )
    default_faiss = data_root / "bible_vectors.index"
    default_lookup = data_root / "bible_verse_map.pkl"
    if not faiss_index and default_faiss.exists():
        faiss_index = str(default_faiss)
    if not verse_lookup and default_lookup.exists():
        verse_lookup = str(default_lookup)

    db_path = DB_PATH
    server.library.rescan()
    resolved = server.library.resolve_primary_db(DEFAULT_TRANSLATION, "English")
    if resolved:
        version, lang, path = resolved
        db_path = str(path)
        server._current_version = version
        server._current_language = lang
        logger.info("Using primary Bible DB: %s (%s/%s)", path, version, lang)
    elif not Path(db_path).exists():
        logger.error(
            "No English NKJV database found. Expected: "
            "Documents\\WindowVerse\\data\\NKJV\\English\\NKJV.sqlite3"
        )
        sys.exit(1)

    if faiss_index and verse_lookup:
        logger.info("Found pre-built index files — loading automatically")

    asyncio.run(server.run(
        db_path=db_path,
        external_faiss_index=faiss_index,
        external_verse_lookup=verse_lookup,
        external_lookup_format=os.environ.get(
            "WINDOWVERSE_LOOKUP_FORMAT",
            os.environ.get("WINDOWVERSE_LOOKUP_FORMAT", "pickle"),
        ),
    ))


if __name__ == "__main__":
    main()

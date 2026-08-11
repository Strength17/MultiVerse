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
  detection          — verse detection (auto_display true/false)
  heartbeat          — periodic alive ping

WebSocket actions from UI:
  start_mic / stop / manual_search
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import websockets

from console_output import mark_live_line_open, write_line

from bible_db import BibleDB
from detection_orchestrator import DetectionOrchestrator
from winrt_pipeline import WinRTSpeechPipeline
from vocab_correction import correct_text, purge_bad_corrections

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/multiverse.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("multiverse.server")

# One-time self-heal: strip any bad entries (stopwords, digit-containing
# keys) that were saved to data/corrections_learned.json before these
# guards existed, so a machine with an already-corrupted file recovers
# without a manual step. Must run after logging.basicConfig (above) or its
# log line is silently dropped.
purge_bad_corrections()

from app_config import load_config
from bible_library import BibleLibrary
from ndi_sender import NDISender

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

# Per-source minimum gap before auto-displaying a DIFFERENT verse than the
# one currently shown. Now sourced from config.ini [detection] instead of
# being hardcoded here -- see app_config.py.
AUTO_DISPLAY_COOLDOWN = {
    "regex":     APP_CONFIG.detection.cooldown_regex_seconds,
    "semantic":  APP_CONFIG.detection.cooldown_semantic_seconds,
    "narrative": APP_CONFIG.detection.cooldown_narrative_seconds,
}


class MultiVerseServer:
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
        self.library = BibleLibrary(self.config.library.data_root)
        self.library.rescan()
        self._current_version: str = DEFAULT_TRANSLATION
        self._current_language: str = "English"
        self._show_secondary: bool = self.config.library.show_secondary_translation_by_default

        # ── NDI output (independent subsystem -- see ndi_sender.py; a
        #    missing NDI runtime or cyndilib install degrades this to a
        #    no-op instead of touching detection/UI at all) ──
        self.ndi_sender = NDISender(self.config.ndi)

        self._last_speech_at = 0.0
        self._idle_paused = False
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
        self._verse_queue: list[dict] = []
        self._queue_position = -1

        # Detection (regex + semantic embedding + narrative tracking) runs
        # here, off the main event loop. A single worker keeps chunks
        # processed in the order they were spoken (no races on the
        # orchestrator's internal buffers) while never blocking the loop
        # that prints/broadcasts the NEXT transcript chunk. This is what
        # keeps the transcript real-time even when a verse match takes a
        # few hundred ms of embedding work to resolve.
        self._detection_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="multiverse-detect"
        )

    # ── Initialisation ────────────────────────────────────────────────────────
    def _report_startup(self, step_id: str, label: str, status: str):
        """Record a boot step and push it to any connected UI (thread-safe)."""
        self._startup_steps[step_id] = {
            "step": step_id, "label": label, "status": status,
        }
        self._broadcast_threadsafe({
            "type": "startup_progress",
            "step": step_id, "label": label, "status": status,
        })

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
        else:
            self._report_startup("self_check", "Verifying verse lookups", "done")
            logger.info("Startup self-check passed — anchor verses match expected text")

        if external_faiss_index and external_verse_lookup:
            logger.info("Loading pre-built FAISS index — skipping embedding work")
            self._report_startup("search_index", "Loading search index", "running")
            self.orchestrator.load_external_index(
                external_faiss_index, external_verse_lookup,
                lookup_format=external_lookup_format,
            )
        else:
            self._report_startup("search_index", "Building search index", "running")
            self.orchestrator.build_index()
        self._report_startup(
            "search_index",
            "Loading search index" if external_faiss_index else "Building search index",
            "done",
        )

        self._report_startup("narrative", "Starting narrative tracker", "running")
        from narrative_tracker import NarrativeTracker
        self.narrative_tracker = NarrativeTracker(
            embedding_model=self.orchestrator.vector_engine._model,
            bible_db=self.bible_db,
            default_translation="NKJV",
        )
        self._report_startup("narrative", "Starting narrative tracker", "done")

        # ── Wire pipeline: Windows on-device dictation owns the mic directly,
        #    no chunk_seconds/transcriber args needed anymore ───────────────
        self._report_startup("speech", "Preparing speech pipeline", "running")
        self.pipeline = WinRTSpeechPipeline(
            on_result=self._on_chunk_result,
            on_speech_started=self._on_speech_started,
            on_partial_result=self._on_partial_result,
        )
        self._report_startup("speech", "Preparing speech pipeline", "done")
        logger.info("Initialization complete.")

    # ── VAD instant callback ──────────────────────────────────────────────────
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
            logger.warning("Detection warning: %s", event)
            await self._broadcast({"type": "detection_warning", **event})

        if narrative_event is not None:
            # Terminal JSONL print (mirrors the unconditional print that
            # orchestrator.detect() does for regex/semantic hits). Routed
            # through write_line so it can't land mid-way through an open
            # [live] partial line.
            write_line(json.dumps(narrative_event, ensure_ascii=False))
            await self._handle_detection(narrative_event, now)

        if not event.get("triggered") and not event.get("warning") and narrative_event is None:
            await self._broadcast({"type": "heartbeat"})

    async def _check_idle(self, now: float):
        if self._idle_paused or self._last_speech_at == 0.0:
            return
        if now - self._last_speech_at >= IDLE_TIMEOUT_SECONDS:
            self._idle_paused = True
            await self._broadcast({"type": "status", "state": "idle_paused"})
            logger.info("No speech for %ds — idle pause", IDLE_TIMEOUT_SECONDS)

    async def _handle_detection(self, event: dict, now: float):
        """Apply cooldown logic, then broadcast. Terminal print already done
        inside detect() — this is WebSocket-only."""
        source  = event.get("source", "semantic")
        min_gap = AUTO_DISPLAY_COOLDOWN.get(source, AUTO_DISPLAY_COOLDOWN["semantic"])

        # Secondary-language lookup: attached whenever a language folder
        # sits next to the current version's (e.g. data/NKJV/French/...)
        # and the toggle is on. A missing/broken secondary DB is caught
        # inside BibleLibrary.get_db and just returns None -- never crashes
        # the primary (English) detection path.
        secondary_language = self.library.secondary_language_for(
            self._current_version, self._current_language
        )
        if self._show_secondary and secondary_language and event.get("book_number"):
            try:
                sec_db = self.library.get_db(self._current_version, secondary_language)
                sec_row = sec_db.lookup_verse(
                    event["book_number"], event["chapter"], event["verse"]
                ) if sec_db else None
            except Exception:
                logger.exception("Secondary-language lookup failed — showing primary only")
                sec_row = None
            if sec_row and sec_row.get("text"):
                event = {**event, "secondary_language": secondary_language,
                          "secondary_text": sec_row["text"]}

        same_verse = (
            self._last_displayed is not None
            and self._last_displayed.get("book")    == event.get("book")
            and self._last_displayed.get("chapter") == event.get("chapter")
            and self._last_displayed.get("verse")   == event.get("verse")
        )

        if not same_verse and (now - self._last_display_at) < min_gap:
            await self._broadcast({"type": "detection", **event, "auto_display": False})
            return

        self._last_display_at = now
        self._last_displayed  = event
        # Terminal JSONL already printed in orchestrator.detect() — no double-print here.
        await self._broadcast({"type": "detection", **event, "auto_display": True})

        # Mirror to NDI (vMix input) -- isolated try/except so a rendering
        # or NDI-runtime problem can never take down detection/broadcast.
        try:
            self.ndi_sender.update(
                reference=f"{event.get('book')} {event.get('chapter')}:{event.get('verse')}",
                text=event.get("text", ""),
                secondary_text=event.get("secondary_text"),
            )
        except Exception:
            logger.exception("NDI update failed — display pipeline unaffected")

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
        # No sounddevice InputStream here: WinRTSpeechPipeline captures the
        # default microphone itself at the OS level. Opening a second
        # consumer on the same device would fight it for the input.
        if self.pipeline is None:
            raise RuntimeError("Speech pipeline not initialized")
        self.pipeline.start()
        if not self.pipeline.wait_session_ready(timeout=20.0):
            detail = self.pipeline.last_error or "WinRT session did not start in time"
            raise RuntimeError(detail)
        if not self.pipeline.is_running():
            detail = self.pipeline.last_error or "WinRT session stopped unexpectedly"
            raise RuntimeError(detail)
        logger.info("Mic input started (Windows on-device dictation)")

    def stop(self):
        if self.pipeline:
            self.pipeline.stop()
        # Note: deliberately NOT shutting down self._detection_executor here.
        # This stop() is reachable from the UI's "stop mic" button, and the
        # mic can be restarted afterward (start_mic) in the same process --
        # killing the executor here would break detection on that restart.
        # concurrent.futures registers its own atexit handler, so the
        # worker thread is still joined cleanly when the process exits.
        logger.info("Stopped")

    # ── WebSocket handling ────────────────────────────────────────────────────
    async def _send_boot_state(self, websocket):
        """Everything a newly-connected UI needs to mirror current boot status."""
        await websocket.send(json.dumps({
            "type": "hardware_profile",
            "os": "Windows 11",
            "cpu": None,
            "cpu_cores": None,
            "ram_gb": None,
            "gpus": [],
            "has_nvidia": False,
            "nvidia_name": None,
            "has_other_gpu": False,
            "other_gpu_name": None,
            "engine": "Windows on-device dictation (WinRT)",
            "model_size": "system-managed",
            "compute_type": "native",
            "chunk_seconds": "continuous",
        }))
        for step in self._startup_steps.values():
            await websocket.send(json.dumps({"type": "startup_progress", **step}))
        state = "ready" if self._ready else "booting"
        await websocket.send(json.dumps({"type": "status", "state": state}))
        if self._ready:
            for problem in self._startup_warnings:
                await websocket.send(json.dumps({
                    "type": "detection_warning",
                    "warning": "startup_self_check_failed",
                    "detail": problem,
                }))
            self.library.rescan()
            await websocket.send(json.dumps({
                "type": "library",
                "versions": self.library.list_versions(),
                "current_version": self._current_version,
                "current_language": self._current_language,
                "secondary_language": self.library.secondary_language_for(
                    self._current_version, self._current_language),
                "show_secondary": self._show_secondary,
            }))

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
                await websocket.send(json.dumps({
                    "type": "detection_warning",
                    "warning": "not_ready",
                    "detail": "Backend is still loading — wait for all startup steps to finish.",
                }))
                return
            await self._broadcast({"type": "status", "state": "starting"})
            try:
                await asyncio.to_thread(self.start_mic)
            except Exception as exc:
                logger.exception("start_mic failed")
                await self._broadcast({
                    "type": "detection_warning",
                    "warning": "mic_start_failed",
                    "detail": str(exc),
                })
                await self._broadcast({"type": "status", "state": "ready"})
                return
            await self._broadcast({"type": "status", "state": "listening"})
        elif action == "stop":
            await asyncio.to_thread(self.stop)
            await self._broadcast({"type": "status", "state": "ready"})
        elif action == "manual_search":
            query = msg.get("query", "")
            try:
                result = await asyncio.to_thread(
                    self.orchestrator.vector_engine.search_paraphrase, query
                )
            except Exception:
                logger.exception("Manual search failed for query %r", query)
                result = None
            await websocket.send(json.dumps({
                "type": "manual_search_result",
                "query": query,
                "result": result,
            }))
        elif action == "switch_version":
            await self._switch_version(
                msg.get("version"), msg.get("language", "English"), websocket
            )
        elif action == "set_show_translation":
            self._show_secondary = bool(msg.get("enabled", False))
            self._broadcast_threadsafe({
                "type": "broadcast_state", "show_secondary": self._show_secondary
            })
        else:
            logger.warning("Unknown action: %s", action)

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
            await websocket.send(json.dumps({
                "type": "detection_warning",
                "warning": "version_switch_failed",
                "detail": f"No usable Bible DB found for {version} / {language}",
            }))
            return

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
            await self._broadcast({
                "type": "detection_warning",
                "warning": "version_switch_failed",
                "detail": f"{version} ({language}) failed to build — kept the previous version running",
            })
            await self._broadcast({"type": "status", "state": "listening"})
            return

        self.orchestrator = new_orchestrator
        self.bible_db = db
        self._current_version = version
        self._current_language = language
        logger.info("Switched active Bible version to %s / %s", version, language)

        await self._broadcast({
            "type": "library",
            "versions": self.library.list_versions(),
            "current_version": self._current_version,
            "current_language": self._current_language,
            "secondary_language": self.library.secondary_language_for(
                self._current_version, self._current_language),
            "show_secondary": self._show_secondary,
        })
        await self._broadcast({"type": "status", "state": "listening"})

    # ── OSC broadcast state ───────────────────────────────────────────────────
    def queue_advance(self, direction: int):
        if not self._verse_queue:
            return
        self._queue_position = max(0, min(len(self._verse_queue) - 1,
                                          self._queue_position + direction))
        self._broadcast_threadsafe({
            "type": "detection",
            **self._verse_queue[self._queue_position],
            "auto_display": True,
        })

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
                })

    # ── Run ───────────────────────────────────────────────────────────────────
    async def run(self, *, db_path: str = DB_PATH,
                  external_faiss_index: str | None = None,
                  external_verse_lookup: str | None = None,
                  external_lookup_format: str = "pickle"):
        self._loop = asyncio.get_running_loop()

        async with websockets.serve(self.handle_client, HOST, PORT):
            logger.info("MultiVerse V3 listening on ws://%s:%d — booting", HOST, PORT)
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

            self._ready = True
            await self._broadcast({"type": "status", "state": "ready"})
            for problem in self._startup_warnings:
                await self._broadcast({
                    "type": "detection_warning",
                    "warning": "startup_self_check_failed",
                    "detail": problem,
                })
            self.library.rescan()
            await self._broadcast({
                "type": "library",
                "versions": self.library.list_versions(),
                "current_version": self._current_version,
                "current_language": self._current_language,
                "secondary_language": self.library.secondary_language_for(
                    self._current_version, self._current_language),
                "show_secondary": self._show_secondary,
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
    server = MultiVerseServer()

    faiss_index  = os.environ.get("MULTIVERSE_FAISS_INDEX")
    verse_lookup = os.environ.get("MULTIVERSE_VERSE_LOOKUP")

    if not faiss_index  and Path(DEFAULT_FAISS).exists():  faiss_index  = DEFAULT_FAISS
    if not verse_lookup and Path(DEFAULT_LOOKUP).exists():  verse_lookup = DEFAULT_LOOKUP

    if faiss_index and verse_lookup:
        logger.info("Found pre-built index files — loading automatically")

    asyncio.run(server.run(
        external_faiss_index=faiss_index,
        external_verse_lookup=verse_lookup,
        external_lookup_format=os.environ.get("MULTIVERSE_LOOKUP_FORMAT", "pickle"),
    ))


if __name__ == "__main__":
    main()

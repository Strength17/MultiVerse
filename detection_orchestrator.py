"""
detection_orchestrator.py  —  V3

Combines V2's full pipeline with V1's two-chunk merge buffer and unconditional
terminal printing. Detection priority:

  1. Regex direct reference (fast, ~5ms, 90-97%)
  2. Semantic/paraphrase FAISS search (~20-80ms, 35-89%)
  3. Narrative/story tracking (background, ~50ms, 35-75%)

Two-layer cross-chunk handling:
  - V1 layer: deque(maxlen=2) — merges last 2 raw chunks before detection
  - V2 layer: RollingTranscriptBuffer (12s window) — catches refs split over 3+ chunks

Terminal output:
  [TRANSCRIPT] <spoken text>         ← printed immediately by server.py,
                                        before detect() is even called
  {"triggered": true, "book": "John", "chapter": 3, "verse": 16, ...}
                                      ← printed by detect() itself, once
                                        detection finishes (may run in the
                                        background, after the transcript)
"""

from __future__ import annotations

import collections
import json
import logging
import sys
import time

import re

from reference_context import ReferenceContext
from detection_filters import should_skip_detection
from verse_detector import detect_direct_reference, _WORD_TO_NUM
from vector_search import VectorSearchEngine
from console_output import write_line
from transcriber import RollingTranscriptBuffer

logger = logging.getLogger("multiverse.orchestrator")

CONFIDENCE_BANDS = {
    "high":   (0.80, 1.01),
    "medium": (0.55, 0.80),
    "low":    (0.35, 0.55),
}

# NOTE: the semantic-word floor, regex threshold, dedup window, and vector
# threshold all now live in config.ini [detection] and are injected via
# DetectionOrchestrator's constructor (see app_config.py) -- no
# module-level constants here anymore, so there's exactly one place each
# value can drift from what config.ini documents: nowhere.


_NUMBER_WORD_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(_WORD_TO_NUM, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _chunk_has_reference_signal(text: str) -> bool:
    """True if this (newest) chunk alone contains something that could be
    part of a chapter/verse number -- a digit or a spoken number word.

    Used to gate the two-chunk/rolling-window fallback: those levels exist
    ONLY to catch a reference number split across chunks (e.g. "chapter
    one" / "verse twenty four"). If the newest chunk has no digit and no
    number word at all, any regex match found in the merged buffer can
    only be coming from OLD text that already failed (or already
    triggered) on its own -- i.e. a stale rematch, not a genuine split
    reference -- so the fallback must not run.
    """
    if re.search(r"\d", text):
        return True
    return bool(_NUMBER_WORD_PATTERN.search(text))


def confidence_band(confidence: float) -> str:
    for band, (lo, hi) in CONFIDENCE_BANDS.items():
        if lo <= confidence < hi:
            return band
    return "low"


def _regex_needs_escalation(result: dict | None) -> bool:
    """True when regex on the current chunk didn't produce a final hit."""
    if result is None:
        return True
    if result.get("triggered"):
        return False
    return bool(result.get("handled"))


def _match_anchored_in_fresh_chunk(direct: dict, matched_text: str,
                                    fresh_chunk: str) -> bool:
    """Allow merged-buffer regex hits when the newest chunk contributed the
    reference tail (chapter/verse), not only when the full match substring
    appears verbatim in the fresh chunk."""
    matched = (matched_text or "").strip().lower()
    fresh = fresh_chunk.strip().lower()
    if not matched:
        return True
    if matched in fresh:
        return True
    if re.search(r"\b(chapter|verse)\b", fresh, re.IGNORECASE):
        chap, ver = direct.get("chapter"), direct.get("verse")
        chap_s = str(chap) if chap is not None else ""
        ver_s = str(ver) if ver is not None else ""
        if chap_s and ver_s and chap_s in fresh and ver_s in fresh:
            return True
        if ver_s and ver_s in fresh and matched.startswith("verse"):
            return True
    return False


class DetectionOrchestrator:
    def __init__(self, bible_db, translation: str = "NKJV",
                 semantic_top_k: int = 8, context_timeout_s: float = 10.0,
                 regex_threshold: float = 0.75, min_semantic_words: int = 8,
                 dedup_seconds: float = 6.0,
                 vector_threshold: float = 0.70, min_overlap_ratio: float = 0.25):
        self.bible_db = bible_db
        self.translation = translation
        self.context = ReferenceContext(timeout_seconds=context_timeout_s)
        self.vector_engine = VectorSearchEngine(
            bible_db, translation=translation,
            vector_threshold=vector_threshold, min_overlap_ratio=min_overlap_ratio,
        )
        self.semantic_top_k = semantic_top_k
        # Injected from config.ini [detection] (see app_config.py) instead
        # of a module-level constant, so the value doesn't drift between
        # what config.ini documents and what actually runs.
        self.regex_threshold = regex_threshold
        self.min_semantic_words = min_semantic_words
        self.dedup_seconds = dedup_seconds
        self._index_built = False

        # Same-verse recent-fire dedup state (see detect()) -- tracks the
        # last verse actually broadcast and when, independent of the
        # chunk-idempotency guard below (which only catches literal replays
        # of the same audio, not two different chunks hitting the same verse).
        self._last_fired_verse: tuple | None = None
        self._last_fired_at: float = 0.0

        # Session-level verse cache: avoids a DB hit when the same verse is
        # detected again later in the same session (e.g. a preacher repeats
        # a verse). Cleared only by restarting the app -- intentionally not
        # persisted to disk, this is a per-session speed optimization only.
        self._verse_cache: dict[tuple[int, int, int], dict] = {}

        # Chunk idempotency guard: if the mic pipeline or websocket ever
        # reconnects and replays a chunk (e.g. after a dropped connection),
        # this stops the same audio window from being detected twice.
        # Bounded deque so memory doesn't grow across a long session.
        self._seen_chunks: collections.deque = collections.deque(maxlen=200)
        self._seen_chunk_set: set[tuple[float, float]] = set()

        # V2: 12s rolling window — catches refs split over 3+ chunks
        self.buffer = RollingTranscriptBuffer(window_seconds=12.0, commit_after_updates=2)

        # V1: two-chunk deque merge — "John chapter 3" + "verse 16" in next chunk
        self._two_chunk_deque: collections.deque = collections.deque(maxlen=2)

        # Set by _run_regex_only when a reference was correctly parsed but
        # the DB had no matching row -- surfaced in detect()'s return value
        # (and by the semantic warmup below) instead of failing silently.
        self._last_miss: dict | None = None
        self._semantic_empty_warned = False

    # ── Index management ──────────────────────────────────────────────────────
    def build_index(self, cache_dir: str | None = None, progress_callback=None):
        from index_cache import load_or_build_index
        from paths import ensure_user_dirs
        if cache_dir is None:
            cache_dir = str(ensure_user_dirs()["data"] / "index_cache")
        t0 = time.time()
        load_or_build_index(
            self.vector_engine,
            db_path=self.bible_db.db_path,
            cache_dir=cache_dir,
            translation=self.translation,
            progress_callback=progress_callback,
        )
        self._index_built = True
        logger.info("Semantic index ready in %.1fs", time.time() - t0)

    def load_external_index(self, faiss_index_path: str, verse_lookup_path: str,
                             lookup_format: str = "pickle"):
        from index_cache import load_external_index
        t0 = time.time()
        load_external_index(
            self.vector_engine,
            faiss_index_path=faiss_index_path,
            verse_lookup_path=verse_lookup_path,
            lookup_format=lookup_format,
        )
        self._index_built = True
        logger.info("External semantic index loaded in %.1fs (pre-built files, unmodified)",
                    time.time() - t0)

    # ── Main detection entry point ────────────────────────────────────────────
    def detect(self, transcript_chunk: str, latency_ms: float | None = None,
               chunk_start: float = 0.0, chunk_end: float = 0.0) -> dict:
        """
        Runs detection against the rolling window text. Always returns a dict,
        never raises. Prints a JSONL line to terminal on a confirmed detection.

        Does NOT print the raw transcript line -- this method (specifically
        the semantic-search fallback) can take real time, and callers may
        run it off the main thread/event loop so slow detection never delays
        the next chunk. The transcript itself must appear immediately
        regardless of how long detection takes, so printing it is the
        caller's job, done before detect() is ever invoked (see server.py's
        _handle_chunk_async).
        """
        if not transcript_chunk or not transcript_chunk.strip():
            return {"triggered": False}

        if should_skip_detection(transcript_chunk):
            logger.debug("Skipping detection — likely non-English interpreter speech: %r",
                         transcript_chunk[:80])
            return {"triggered": False, "skipped": "interpreter_speech"}

        self._last_miss = None

        # ── Idempotency guard: skip a chunk we've already processed ───────────
        # (e.g. a websocket/mic reconnect replaying buffered audio). Keyed on
        # the chunk's own timestamps, which are stable across a replay.
        chunk_key = (chunk_start, chunk_end)
        if chunk_start or chunk_end:  # (0.0, 0.0) means "no real timestamp" -- don't guard those
            if chunk_key in self._seen_chunk_set:
                logger.info("Skipping already-processed chunk (start=%.2f end=%.2f) — duplicate/replay",
                            chunk_start, chunk_end)
                return {"triggered": False}
            self._seen_chunks.append(chunk_key)
            self._seen_chunk_set.add(chunk_key)
            if len(self._seen_chunks) == self._seen_chunks.maxlen:
                # deque auto-evicts the oldest on append once full; keep the
                # lookup set in sync so it doesn't grow unbounded.
                self._seen_chunk_set = set(self._seen_chunks)

        # ── V1 two-chunk deque merge ──────────────────────────────────────────
        self._two_chunk_deque.append(transcript_chunk.strip())
        two_chunk_text = " ".join(self._two_chunk_deque)

        # ── V2 rolling buffer ─────────────────────────────────────────────────
        self.buffer.add_chunk(chunk_start, chunk_end, transcript_chunk)
        window_text = self.buffer.rolling_text()

        # Detection priority: current chunk ALONE first (fastest, and immune
        # to stale references left over from the previous chunk), then the
        # two-chunk merge (catches a reference split across exactly 2 chunks),
        # then the full rolling window (catches refs split over 3+ chunks).
        # Every level also uses last-match-wins internally (verse_detector's
        # _last_match), so even within a merged buffer the most recently
        # spoken reference always takes priority over a stale one.
        #
        # Regex (cheap, ~5ms) is tried at all three levels first. Semantic
        # search (~20-80ms, one embedding call each) only runs AFTER regex
        # has failed at every level, and only ONCE, against the richest text
        # available — never once-per-level. This keeps worst-case cost at
        # 1 embedding call per chunk instead of up to 3.
        result = self._run_regex_only(transcript_chunk.strip())
        # Fallback levels only exist to catch a reference NUMBER split
        # across chunks. If the newest chunk has no digit/number-word at
        # all, skip them outright (cheap pre-filter). Even when it does,
        # require the ACTUAL matched substring to be verifiably present in
        # the newest chunk (see _run_regex_only's fresh_chunk param) --
        # digit-presence alone isn't enough: "John 11" in the new chunk
        # still let a fuzzy match built from OLD words ("so I John") through
        # before, because those words individually also appear in the new
        # chunk. Contiguous-substring verification is what actually blocks it.
        chunk_has_signal = _chunk_has_reference_signal(transcript_chunk)
        if _regex_needs_escalation(result) and chunk_has_signal and two_chunk_text != transcript_chunk.strip():
            result = self._run_regex_only(two_chunk_text, fresh_chunk=transcript_chunk.strip())
        if _regex_needs_escalation(result) and chunk_has_signal and window_text != two_chunk_text:
            result = self._run_regex_only(window_text, fresh_chunk=transcript_chunk.strip())

        if result is not None:
            result["latency_ms"] = latency_ms
        else:
            semantic_queries = self._pick_semantic_queries(
                transcript_chunk.strip(), two_chunk_text.strip(), window_text.strip(),
            )
            result = self._run_semantic_only(
                semantic_queries, latency_ms, anchor_chunk=transcript_chunk.strip(),
            )

        if result.get("triggered"):
            verse_key = (result.get("book_number"), result.get("chapter"), result.get("verse"))
            now = time.time()
            is_recent_repeat = (
                self._last_fired_verse == verse_key
                and (now - self._last_fired_at) < self.dedup_seconds
            )
            if is_recent_repeat:
                # Root cause of the double-print: escalation levels are
                # already deduped (one semantic call per chunk, see class
                # docstring), but two DIFFERENT adjacent chunks can each
                # independently detect the same real-world moment a few
                # hundred ms to a few seconds apart. This is the guard that
                # was missing -- suppress the re-fire instead of broadcasting
                # the same verse twice.
                logger.info(
                    "Deduped repeat fire of %s %s:%s — %.2fs since last fire (window=%.1fs)",
                    result.get("book"), result.get("chapter"), result.get("verse"),
                    now - self._last_fired_at, self.dedup_seconds,
                )
                result = {"triggered": False, "deduped": True, **result}
                self.buffer.clear()
                self._two_chunk_deque.clear()
                return result

            self._last_fired_verse = verse_key
            self._last_fired_at = now

            # ── Terminal JSONL detection print (V1 behavior, unconditional) ──
            # Routed through write_line so it can't land mid-way through an
            # open [live] partial-transcript line (see console_output.py).
            write_line(json.dumps(result, ensure_ascii=False))
            # This chunk's speech has now been fully consumed and reported.
            # Clear both cross-chunk buffers so it can't keep leaking into
            # the NEXT detection call -- previously the 12s rolling window
            # (and the two-chunk deque it falls back to) carried the
            # just-triggered text forward, and its leftover words could
            # dominate the next embedding/rerank enough to re-report the
            # SAME verse instead of a genuinely new one spoken right after.
            self.buffer.clear()
            self._two_chunk_deque.clear()
        elif self._last_miss is not None:
            # Nothing triggered, but a reference WAS correctly parsed --
            # either out-of-range (invalid chapter/verse for this book) or
            # in-range but missing from the DB. Surface it instead of going
            # silent. Terminal print here mirrors the unconditional
            # detection print above so this is never invisible.
            warning_kind = "reference_out_of_range" if self._last_miss.get("out_of_range") \
                else "matched_reference_missing_from_db"
            result = {**result, "warning": warning_kind, **self._last_miss}
            write_line(json.dumps({k: v for k, v in result.items()
                               if k in ("warning", "book", "chapter", "verse", "reason",
                                        "max_chapter", "max_verse",
                                        "requested_chapter", "requested_verse")},
                              ensure_ascii=False))

        return result

    def _run_regex_only(self, text: str, fresh_chunk: str | None = None) -> dict | None:
        """Fast-path direct-reference match. Returns a detection dict on a
        hit, or None (not {"triggered": False}) so callers can tell 'no
        match, try the next text level' apart from 'this level is final'.
        latency_ms is filled in by the caller.

        fresh_chunk: only passed for the two-chunk/window FALLBACK calls
        (never the chunk-alone call, where it'd be a no-op anyway). When
        set, a match is discarded unless its matched text is a literal
        (case-insensitive) substring of fresh_chunk -- i.e. it's really
        anchored in the newest speech, not stitched together out of
        leftover words from an older chunk still sitting in the buffer.
        """
        if not text.strip():
            return None

        direct = detect_direct_reference(text, self.context, bible_db=self.bible_db,
                                          regex_threshold=self.regex_threshold)
        if direct is None:
            return None
        if direct.get("handled"):
            return direct

        if fresh_chunk is not None:
            matched_text = (direct.get("matched_text") or "").strip()
            if matched_text and not _match_anchored_in_fresh_chunk(
                direct, matched_text, fresh_chunk,
            ):
                logger.info(
                    "Discarding stale fallback match %s %s:%s -- matched text %r "
                    "isn't anchored in the newest chunk",
                    direct["book"], direct["chapter"], direct["verse"], matched_text,
                )
                return None

        book_number, chapter, verse = direct["book_number"], direct["chapter"], direct["verse"]
        verse_end = direct.get("verse_end")

        # ── Out-of-range check FIRST, before hitting the DB -- gives a
        # specific, actionable log/warning ("Romans only has 16 chapters")
        # instead of the generic "no matching row" below, which is what
        # you'd otherwise get for a genuinely invalid reference.
        validation = self.bible_db.validate_reference(book_number, chapter, verse)
        if not validation.get("valid") and validation.get("reason") in (
            "chapter_out_of_range", "verse_out_of_range",
        ):
            self._last_miss = {
                "book": direct["book"], "chapter": chapter, "verse": verse,
                "out_of_range": True, **validation,
            }
            return None

        if verse_end is not None:
            # Verse range: fetch every verse in [verse, verse_end] and
            # concatenate. A range partially out of bounds still returns
            # whatever verses ARE valid -- loud log per skipped verse.
            texts = []
            for v in range(verse, verse_end + 1):
                cache_key = (book_number, chapter, v)
                row = self._verse_cache.get(cache_key)
                if row is None:
                    row = self.bible_db.lookup_verse(book_number, chapter, v, translation=self.translation)
                    if row is not None:
                        self._verse_cache[cache_key] = row
                if row is None:
                    logger.warning(
                        "Verse range %s %s:%s-%s -- verse %s missing from DB, skipping it",
                        direct["book"], chapter, verse, verse_end, v,
                    )
                    continue
                texts.append(row["text"])
            if not texts:
                self._last_miss = {"book": direct["book"], "chapter": chapter, "verse": verse}
                return None
            verse_text = " ".join(texts)
        else:
            cache_key = (book_number, chapter, verse)
            verse_row = self._verse_cache.get(cache_key)
            if verse_row is None:
                verse_row = self.bible_db.lookup_verse(
                    book_number, chapter, verse, translation=self.translation,
                )
                if verse_row is not None:
                    self._verse_cache[cache_key] = verse_row

            if verse_row is None:
                # This is a real, user-visible failure -- the reference was
                # heard and parsed correctly, in-range, but the Bible DB has
                # no row for it (bad data, schema mismatch, wrong translation
                # file, etc). Log loud (not DEBUG) and remember it so
                # detect() can surface it even though nothing "triggered".
                logger.warning(
                    "Regex matched %s %s:%s (in-range) but no matching row in Bible DB -- "
                    "check the DB file/schema for this book/translation",
                    direct["book"], chapter, verse,
                )
                self._last_miss = {"book": direct["book"], "chapter": chapter, "verse": verse}
                return None
            verse_text = verse_row["text"]

        logger.info(
            "DETECTED [regex] %s %s:%s%s (confidence=%.2f%s) matched=%r",
            direct["book"], chapter, verse,
            f"-{verse_end}" if verse_end else "",
            direct["confidence"],
            " bare_number_confirmed" if direct.get("bare_number_confirmed") else "",
            direct.get("matched_text", ""),
        )
        result = {
            "triggered": True,
            "source": "regex",
            "book": direct["book"],
            "book_number": book_number,
            "chapter": chapter,
            "verse": verse,
            "text": verse_text,
            "translation": "NKJV",
            "confidence": direct["confidence"],
            "confidence_band": confidence_band(direct["confidence"]),
        }
        if verse_end is not None:
            result["verse_end"] = verse_end
        if direct.get("bare_number_confirmed"):
            result["bare_number_confirmed"] = True
        return result

    @staticmethod
    def _split_semantic_clauses(text: str) -> list[str]:
        """Split a transcript span into clause-sized pieces for embedding.
        Prevents a trailing unrelated sentence ('and the Lord gives rain…')
        from steering a beatitude/paraphrase toward the wrong verse."""
        if not text.strip():
            return []
        parts = re.split(
            r"(?:\.\s+|\s+and\s+(?:the|he|she|they|who|whoever|it|we|you)\s+)",
            text,
            flags=re.IGNORECASE,
        )
        return [p.strip() for p in parts if p.strip()]

    def _pick_semantic_queries(self, chunk: str, two_chunk: str, window: str) -> list[str]:
        """Build ordered semantic query spans — freshest speech first, never
        the full 12s rolling window (regex needs that; embeddings don't)."""
        seen: set[str] = set()
        queries: list[str] = []

        def add(q: str) -> None:
            q = q.strip()
            if not q or q in seen:
                return
            seen.add(q)
            queries.append(q)

        # Clauses first — a trailing unrelated sentence must not beat the
        # beatitude/paraphrase in the same mic chunk.
        for candidate in (chunk, two_chunk):
            for clause in self._split_semantic_clauses(candidate):
                if len(clause.split()) >= self.min_semantic_words:
                    add(clause)

        for candidate in (chunk, two_chunk):
            if len(candidate.split()) >= self.min_semantic_words:
                add(candidate)

        words = window.strip().split()
        if len(words) >= self.min_semantic_words:
            tail = " ".join(words[-24:])
            if len(tail.split()) >= self.min_semantic_words:
                add(tail)
                for clause in self._split_semantic_clauses(tail):
                    if len(clause.split()) >= self.min_semantic_words:
                        add(clause)

        if not queries:
            add(window.strip() or two_chunk or chunk)
        return queries

    def _run_semantic_only(self, queries: list[str] | str, latency_ms: float | None,
                           anchor_chunk: str = "") -> dict:
        """Paraphrase/embedding fallback. Tries each query span and keeps
        the highest-confidence hit above the detection floor."""
        if isinstance(queries, str):
            queries = [queries]
        queries = [q.strip() for q in queries if q and q.strip()]
        if not queries:
            return {"triggered": False}

        anchor = (anchor_chunk or queries[0]).strip()

        if not self._index_built:
            logger.warning("Semantic index not built yet — skipping semantic search")
            return {"triggered": False}

        if not self.vector_engine._verse_lookup:
            if not self._semantic_empty_warned:
                logger.error(
                    "Semantic search has 0 usable verses loaded — every "
                    "paraphrase/indirect reference will silently miss until "
                    "this is fixed. Check data/bible_verse_map.pkl's key names."
                )
                self._semantic_empty_warned = True
            return {"triggered": False, "warning": "semantic_index_empty"}

        best = None
        try:
            for q in queries:
                if len(q.split()) < self.min_semantic_words:
                    continue
                hit = self.vector_engine.search_paraphrase(
                    q, top_k=self.semantic_top_k, anchor_text=anchor,
                )
                if hit and (best is None or hit["confidence"] > best["confidence"]):
                    best = hit
        except Exception:
            logger.exception(
                "Semantic search failed for queries %r — returning no-hit", queries[:3],
            )
            return {"triggered": False, "error": "semantic_search_failed"}

        if best is None:
            return {"triggered": False}

        semantic = best
        self.context.update(semantic["book_number"], semantic["book"], semantic["chapter"])
        logger.info(
            "DETECTED [semantic] %s %s:%s (confidence=%.2f)",
            semantic["book"], semantic["chapter"], semantic["verse"], semantic["confidence"],
        )
        return {
            "triggered": True,
            "source": "semantic",
            "book": semantic["book"],
            "book_number": semantic["book_number"],
            "chapter": semantic["chapter"],
            "verse": semantic["verse"],
            "text": semantic["text"],
            "translation": "NKJV",
            "confidence": semantic["confidence"],
            "confidence_band": confidence_band(semantic["confidence"]),
            "latency_ms": latency_ms,
        }

    def emit_jsonl(self, event: dict, stream=sys.stdout):
        """Write one JSONL line to the given stream."""
        stream.write(json.dumps(event) + "\n")
        stream.flush()

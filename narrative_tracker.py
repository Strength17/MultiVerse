"""
narrative_tracker.py

NEW CAPABILITY — not present in Pewbeam's documented feature set.

Pewbeam's semantic search (vector_search.py / search_paraphrase) matches
ONE transcript chunk against ONE verse's embedding. That works when a
preacher closely paraphrases a specific verse, but fails for the common
case of narrating a Bible STORY in completely original wording across
many sentences — e.g. retelling the Prodigal Son for two minutes without
ever producing a sentence that resembles the verse text closely enough
to score above the semantic confidence floor.

This module adds a second, parallel detection track that:

  1. Maintains a rolling window of recent transcript text (not just the
     current chunk) — narrative requires more context than one sentence.
  2. Periodically re-embeds that window and matches it against a small
     catalog of known passage SUMMARIES (narrative_passages.py), not
     individual verses — "does this sound like the Prodigal Son" rather
     than "does this sound like Luke 15:20 specifically".
  3. Once anchored to a passage with enough confidence, advances a verse
     pointer through that passage over time, so the displayed verse
     keeps pace with roughly where the narration has gotten to — without
     re-running expensive search every chunk.
  4. Re-anchors (or drops out) when confidence in the current passage
     fades, so it doesn't get stuck showing the wrong story.

Design constraints this respects:
  - MUST NOT touch or rebuild the user's existing 31,102-verse FAISS
    index — this builds its own much smaller (dozens of entries) passage
    index, separately, using the same embedding model instance.
  - MUST be cheap: the rolling-window re-embed only runs on a timer
    (default every 4s), not per chunk, since this is a background
    process running alongside the existing fast per-chunk detection.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from narrative_passages import NARRATIVE_PASSAGES, NarrativePassage, PASSAGE_BY_ID

logger = logging.getLogger("multiverse.narrative_tracker")

# Tuning constants
ROLLING_WINDOW_SECONDS = 45        # how much recent transcript to consider
RECHECK_INTERVAL_SECONDS = 4       # how often to re-embed the window (not per-chunk)
ANCHOR_CONFIDENCE_FLOOR = 0.42     # minimum cosine similarity to anchor to a passage
DROPOUT_CONFIDENCE_FLOOR = 0.28    # below this, abandon the current passage
ADVANCE_SECONDS_PER_VERSE = 6.0    # rough pacing: assume ~6s of narration per verse,
                                    # tuned conservatively slow since pastors often
                                    # linger -- better to lag slightly than overshoot
ADVANCE_SIMILARITY_FLOOR = 0.40    # minimum cosine similarity between the recent
                                    # window and the SPECIFIC next verse's own text
                                    # before the pointer is allowed onto it -- elapsed
                                    # time alone used to be sufficient, which let the
                                    # pointer march forward over totally unrelated
                                    # speech ("triggering previous" verses)


@dataclass
class _WindowEntry:
    text: str
    timestamp: float


@dataclass
class NarrativeState:
    passage: NarrativePassage | None = None
    anchored_at: float = 0.0
    current_verse_pointer: int = 0
    last_advance_at: float = 0.0
    confidence: float = 0.0


class NarrativeTracker:
    """
    Runs alongside DetectionOrchestrator. Call `push_transcript(text)` on
    every transcript chunk (same chunks fed to the regular detector), and
    call `maybe_check()` periodically (the server's event loop can just
    call it on every chunk -- it internally rate-limits itself via
    RECHECK_INTERVAL_SECONDS so the expensive re-embed doesn't run too
    often).
    """

    def __init__(self, embedding_model, bible_db,
                 passages: list[NarrativePassage] | None = None,
                 default_translation: str = "NKJV"):
        self._model = embedding_model
        self.bible_db = bible_db
        self.default_translation = default_translation
        self.passages = passages or NARRATIVE_PASSAGES

        self._window: deque = deque()
        self._passage_embeddings: np.ndarray | None = None
        self._last_check_at = 0.0
        self.state = NarrativeState()

        self._build_passage_index()

    def _build_passage_index(self):
        if not self.passages:
            self._passage_embeddings = np.zeros((0, 384), dtype="float32")
            return

        summaries = [p.summary for p in self.passages]
        embeddings = self._model.encode(
            summaries, normalize_embeddings=True, show_progress_bar=False
        ).astype("float32")
        self._passage_embeddings = embeddings
        logger.info("Narrative passage index built: %d known stories", len(self.passages))

    def push_transcript(self, text: str, timestamp: float | None = None):
        if not text.strip():
            return
        ts = timestamp if timestamp is not None else time.time()
        self._window.append(_WindowEntry(text=text.strip(), timestamp=ts))
        self._prune_window(ts)

    def _prune_window(self, now: float):
        cutoff = now - ROLLING_WINDOW_SECONDS
        while self._window and self._window[0].timestamp < cutoff:
            self._window.popleft()

    def _window_text(self) -> str:
        return " ".join(e.text for e in self._window)

    def maybe_check(self, now: float | None = None):
        now = now if now is not None else time.time()

        # Run confidence recheck on its own timer FIRST, independently of
        # pointer advance, so dropout fires even on a tick where the pointer
        # would also advance. Two separate concerns, both must run.
        recheck_due = (now - self._last_check_at >= RECHECK_INTERVAL_SECONDS)
        if recheck_due:
            self._last_check_at = now
            self._run_confidence_recheck(now)

        # If still anchored after confidence check, try advancing pointer.
        if self.state.passage is not None:
            advance_event = self._maybe_advance_pointer(now)
            if advance_event is not None:
                return advance_event

        # If not anchored (either dropped or never set), try fresh anchor.
        if self.state.passage is None and recheck_due:
            return self._try_anchor(now)

        return None

    def _run_confidence_recheck(self, now: float):
        """Re-embed window, update confidence, drop anchor if too low."""
        if self.state.passage is None:
            return
        window_text = self._window_text()
        if len(window_text.split()) < 8:
            return
        if self._passage_embeddings is None or self._passage_embeddings.shape[0] == 0:
            return
        query_vec = self._model.encode(
            [window_text], normalize_embeddings=True, show_progress_bar=False
        ).astype("float32")[0]
        scores = self._passage_embeddings @ query_vec
        current_idx = next(
            (i for i, p in enumerate(self.passages) if p.id == self.state.passage.id), None
        )
        if current_idx is None:
            return
        current_score = float(scores[current_idx])
        self.state.confidence = current_score
        if current_score < DROPOUT_CONFIDENCE_FLOOR:
            logger.info("Narrative confidence dropped (%.2f) -- dropping anchor on %s",
                        current_score, self.state.passage.title)
            self._drop_anchor()

    def _try_anchor(self, now: float):
        """Try to anchor to a passage from the current window. Returns event or None."""
        window_text = self._window_text()
        if len(window_text.split()) < 8:
            return None
        if self._passage_embeddings is None or self._passage_embeddings.shape[0] == 0:
            return None
        query_vec = self._model.encode(
            [window_text], normalize_embeddings=True, show_progress_bar=False
        ).astype("float32")[0]
        scores = self._passage_embeddings @ query_vec
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score >= ANCHOR_CONFIDENCE_FLOOR:
            return self._anchor_to_passage(self.passages[best_idx], best_score, now)
        return None

    def _anchor_to_passage(self, passage: NarrativePassage, score: float, now: float):
        logger.info("Anchored to narrative passage: %s (confidence %.2f)", passage.title, score)
        self.state = NarrativeState(
            passage=passage, anchored_at=now, current_verse_pointer=0,
            last_advance_at=now, confidence=score,
        )
        return self._build_event(verse_number=passage.start_verse, is_new_anchor=True)

    def _drop_anchor(self):
        self.state = NarrativeState()

    def _maybe_advance_pointer(self, now: float):
        if self.state.passage is None:
            return None
        passage = self.state.passage

        elapsed_since_advance = now - self.state.last_advance_at
        if elapsed_since_advance < ADVANCE_SECONDS_PER_VERSE:
            return None

        next_pointer = self.state.current_verse_pointer + 1
        next_verse_number = passage.start_verse + next_pointer

        if passage.start_chapter == passage.end_chapter and next_verse_number > passage.end_verse:
            return None

        # Only advance onto the next verse if recent speech actually
        # resembles THAT verse specifically. Elapsed time alone used to be
        # sufficient here, which advanced Genesis 1:1 -> 1:4 across four
        # completely unrelated utterances (confidence trending 0.44 -> 0.28)
        # while still reporting triggered: true.
        window_text = self._window_text()
        if len(window_text.split()) < 8:
            return None
        next_verse_row = self.bible_db.lookup_verse(
            passage.book_number, passage.start_chapter, next_verse_number,
            translation=self.default_translation,
        )
        if next_verse_row is None:
            return None
        similarity = self._similarity_to_text(window_text, next_verse_row["text"])
        if similarity < ADVANCE_SIMILARITY_FLOOR:
            # Time passed but nothing recently said resembles the next
            # verse -- release the anchor instead of silently stalling (or
            # worse, ticking forward anyway) on an unrelated topic.
            logger.info(
                "Narrative advance blocked (similarity=%.2f < %.2f for %s %d:%d) -- "
                "releasing anchor",
                similarity, ADVANCE_SIMILARITY_FLOOR, passage.book,
                passage.start_chapter, next_verse_number,
            )
            self._drop_anchor()
            return None

        self.state.current_verse_pointer = next_pointer
        self.state.last_advance_at = now
        self.state.confidence = similarity
        return self._build_event(verse_number=next_verse_number, is_new_anchor=False)

    def _similarity_to_text(self, window_text: str, verse_text: str) -> float:
        vecs = self._model.encode(
            [window_text, verse_text], normalize_embeddings=True, show_progress_bar=False,
        ).astype("float32")
        return float(np.dot(vecs[0], vecs[1]))

    def _build_event(self, verse_number: int, is_new_anchor: bool):
        passage = self.state.passage
        verse_row = self.bible_db.lookup_verse(
            passage.book_number, passage.start_chapter, verse_number,
            translation=self.default_translation,
        )
        if verse_row is None:
            logger.warning("Narrative pointer landed on missing verse %s %d:%d",
                            passage.book, passage.start_chapter, verse_number)
            return None

        return {
            "triggered": True,
            "source": "narrative",
            "narrative_passage": passage.title,
            "narrative_passage_id": passage.id,
            "book": passage.book,
            "book_number": passage.book_number,
            "chapter": passage.start_chapter,
            "verse": verse_number,
            "text": verse_row["text"],
            "confidence": round(self.state.confidence, 3),
            "confidence_band": "narrative",
            "is_new_anchor": is_new_anchor,
            "latency_ms": None,
        }

    def search_query(self, query: str, min_score: float = 0.38) -> dict | None:
        """One-shot story lookup for manual search (does not change tracker state)."""
        text = (query or "").strip()
        if len(text.split()) < 3:
            return None
        if self._passage_embeddings is None or self._passage_embeddings.shape[0] == 0:
            return None
        query_vec = self._model.encode(
            [text], normalize_embeddings=True, show_progress_bar=False,
        ).astype("float32")[0]
        scores = self._passage_embeddings @ query_vec
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score < min_score:
            return None
        passage = self.passages[best_idx]
        verse_row = self.bible_db.lookup_verse(
            passage.book_number, passage.start_chapter, passage.start_verse,
            translation=self.default_translation,
        )
        if verse_row is None:
            return None
        return {
            "triggered": True,
            "source": "narrative",
            "narrative_passage": passage.title,
            "narrative_passage_id": passage.id,
            "book": passage.book,
            "book_number": passage.book_number,
            "chapter": passage.start_chapter,
            "verse": passage.start_verse,
            "text": verse_row["text"],
            "confidence": round(best_score, 3),
            "confidence_band": "narrative",
            "is_new_anchor": True,
            "latency_ms": None,
        }

    def status(self):
        if self.state.passage is None:
            return {"tracking": False}
        return {
            "tracking": True,
            "passage_title": self.state.passage.title,
            "passage_id": self.state.passage.id,
            "current_verse": self.state.passage.start_verse + self.state.current_verse_pointer,
            "confidence": round(self.state.confidence, 3),
        }

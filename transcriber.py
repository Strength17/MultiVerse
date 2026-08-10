"""
transcriber.py

Engine-agnostic text-windowing utility, kept from the original Whisper-based
build. Nothing here talks to a speech engine directly anymore -- that's
winrt_pipeline.py's job. This file survives purely because
detection_orchestrator.py depends on RollingTranscriptBuffer to catch verse
references that get split across multiple recognizer results
("Genesis chapter 1" / "verse 1").
"""

from __future__ import annotations


class RollingTranscriptBuffer:
    """
    Fixes the chunk-split reference problem: "Genesis chapter 1" / "verse
    1" can land in 2-3 separate recognizer results. Detection must run
    against a rolling window of recent text, not a single result, and only
    "commit" (log/emit) text once it has stopped changing across updates --
    mirrors the LocalAgreement approach used by whisper_streaming.
    """

    def __init__(self, window_seconds: float = 12.0, commit_after_updates: int = 2):
        self.window_seconds = window_seconds
        self.commit_after_updates = commit_after_updates
        self._chunks: list[tuple[float, float, str]] = []  # (start, end, text)
        self._last_committed_text = ""
        self._stable_count = 0

    def add_chunk(self, start: float, end: float, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self._chunks.append((start, end, text))
        cutoff = end - self.window_seconds
        self._chunks = [c for c in self._chunks if c[1] >= cutoff]

    def rolling_text(self) -> str:
        """Full text of the current window -- detection should run on this,
        not on a single chunk, so split references are always whole here."""
        return " ".join(c[2] for c in self._chunks).strip()

    def clear(self) -> None:
        """Drop all buffered chunks. Called once a chunk has fully resolved
        into a triggered detection, so that speech which has already been
        consumed and reported doesn't keep leaking into the NEXT semantic
        embedding call and biasing it back toward the just-triggered verse
        (observed: a stale "no condemnation... Christ Jesus" tail from a
        just-triggered Romans 8:1 outweighed a genuinely new "worship in
        spirit and truth" line and re-reported Romans 8:1 instead of the
        correct John 4:24)."""
        self._chunks = []
        self._last_committed_text = ""
        self._stable_count = 0

    def committed_text(self) -> str | None:
        """
        Returns newly-stable text once the same rolling text has been seen
        across `commit_after_updates` consecutive calls, else None. Avoids
        re-logging the same reference repeatedly as the window slides.
        """
        current = self.rolling_text()
        if current == self._last_committed_text:
            self._stable_count += 1
        else:
            self._stable_count = 1
            self._last_committed_text = current
        if self._stable_count == self.commit_after_updates:
            return current
        return None

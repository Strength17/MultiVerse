"""
reference_context.py  —  V2

Tracks two independent things:

1. CONFIRMED context (last_book/last_chapter) — the existing behavior: a
   bare verse-number utterance ("verse 10", no book spoken) resolves
   against the most recently CONFIRMED book+chapter, with a timeout so
   stale context doesn't misfire long after the speaker moved on.

2. PENDING context (pending_book/pending_chapter) — new. A bare "Book N"
   utterance for a multi-chapter book (e.g. "John 11") is ambiguous
   between "chapter 11" and "verse 11 of whatever chapter we're in", so
   it does NOT immediately confirm anything. It primes a PENDING guess
   (chapter=11) that must be resolved by whatever comes next:
     - "verse 1" next          -> confirm_pending(1) => John 11:1 (medium
       confidence, tagged bare_number_confirmed=True)
     - an explicit full ref    -> discard_pending() (verse_detector calls
       this whenever a higher-priority pattern fires)
     - ~60s pass, nothing else -> check_pending_timeout() converts it to a
       plain CHAPTER-ONLY confirm (matches long-standing "Book chapter N"
       convention) -- never auto-promoted to a guessed VERSE.

Single-chapter books (Obadiah, Philemon, 2/3 John, Jude) never go through
pending at all -- see verse_detector.py, which fires those immediately.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("windowverse.reference_context")


@dataclass
class ReferenceContext:
    timeout_seconds: int = 60
    bare_verse_max_age: int = 8

    # -- Confirmed context (resolves bare "verse N") --
    last_book: str | None = None
    last_book_number: int | None = None
    last_chapter: int | None = None
    last_update: float = 0.0

    # -- Pending context (a bare "Book N" awaiting confirmation) --
    pending_book: str | None = None
    pending_book_number: int | None = None
    pending_chapter: int | None = None
    pending_update: float = 0.0

    # -- Warning-log debounce -- detection_orchestrator tries a bare-verse
    # match at up to 3 text levels per chunk (current chunk alone, two-
    # chunk merge, rolling window) when the chunk contains a digit. Every
    # level that fails independently re-calls resolve_bare_verse(), so a
    # single spoken "verse 16" with no context used to log the exact same
    # warning 2-3 times in a row. This debounces identical consecutive
    # failures within one detection pass instead of silencing warnings
    # generally -- a genuinely NEW bare-verse miss (different number, or
    # more than a second later) still logs normally.
    _last_warned_verse: int | None = None
    _last_warned_at: float = 0.0

    # ── Confirmed context ──────────────────────────────────────────────
    def update(self, book_number: int, book_name: str, chapter: int) -> None:
        """Confirm book+chapter. Also clears any pending guess -- an
        explicit/confirmed reference always supersedes a dangling guess."""
        if self.pending_book is not None:
            logger.info(
                "Confirmed reference %s %s superseded pending guess %s %s -- discarding pending",
                book_name, chapter, self.pending_book, self.pending_chapter,
            )
        self.pending_book = None
        self.pending_book_number = None
        self.pending_chapter = None
        self.last_book_number = book_number
        self.last_book = book_name
        self.last_chapter = chapter
        self.last_update = time.time()

    def update_book_only(self, book_number: int, book_name: str) -> None:
        """'Turn to Romans' -- book known, chapter NOT known yet. Doesn't
        touch last_chapter if the same book is already active (a same-book
        re-mention shouldn't wipe a perfectly good chapter); otherwise
        clears chapter so a bare verse can't silently resolve against a
        stale chapter belonging to a different book."""
        if self.last_book_number != book_number:
            self.last_chapter = None
        self.last_book_number = book_number
        self.last_book = book_name
        self.last_update = time.time()
        logger.info("Book-only context primed: %s (chapter not yet known)", book_name)

    def _should_log_bare_verse_warning(self, verse_number: int) -> bool:
        """Debounce: True only if this isn't an immediate repeat (same verse
        number, within 1s) of the last failure warning already logged --
        which is exactly what the orchestrator's 3-level chunk escalation
        produces for one genuinely-unresolvable utterance."""
        now = time.time()
        if self._last_warned_verse == verse_number and now - self._last_warned_at < 1.0:
            return False
        self._last_warned_verse = verse_number
        self._last_warned_at = now
        return True

    def resolve_bare_verse(self, verse_number: int) -> dict | None:
        """Resolve a bare verse number against CONFIRMED context. Returns
        None (and logs loudly why, at most once per ~1s per verse number)
        if there's no usable context."""
        if self.last_book is None:
            if self._should_log_bare_verse_warning(verse_number):
                logger.warning("Bare 'verse %d' heard with no book context at all -- ignoring", verse_number)
            return None
        if time.time() - self.last_update > self.timeout_seconds:
            if self._should_log_bare_verse_warning(verse_number):
                logger.warning(
                    "Bare 'verse %d' heard but context (%s %s) expired %.0fs ago (timeout=%ds) -- ignoring",
                    verse_number, self.last_book, self.last_chapter,
                    time.time() - self.last_update, self.timeout_seconds,
                )
            return None
        if self.last_chapter is None:
            if self._should_log_bare_verse_warning(verse_number):
                logger.warning(
                    "Bare 'verse %d' heard -- book is known (%s) but chapter is NOT -- "
                    "say the chapter number first",
                    verse_number, self.last_book,
                )
            return None
        age = time.time() - self.last_update
        if age > self.bare_verse_max_age and not self.has_pending():
            if self._should_log_bare_verse_warning(verse_number):
                logger.warning(
                    "Bare 'verse %d' ignored — %s %s context is %.0fs old (max %ds for bare verse)",
                    verse_number, self.last_book, self.last_chapter,
                    age, self.bare_verse_max_age,
                )
            return None
        return {
            "book_number": self.last_book_number,
            "book": self.last_book,
            "chapter": self.last_chapter,
            "verse": verse_number,
        }

    def is_active(self) -> bool:
        return (
            self.last_book is not None
            and self.last_chapter is not None
            and time.time() - self.last_update <= self.timeout_seconds
        )

    def clear(self) -> None:
        """Force-reset all context (e.g. on speaker change or manual override)."""
        self.last_book = None
        self.last_book_number = None
        self.last_chapter = None
        self.last_update = 0.0
        self.pending_book = None
        self.pending_book_number = None
        self.pending_chapter = None
        self.pending_update = 0.0

    # ── Pending context (bare "Book N" for multi-chapter books) ────────
    def prime_pending(self, book_number: int, book_name: str, chapter_guess: int) -> dict:
        self.pending_book_number = book_number
        self.pending_book = book_name
        self.pending_chapter = chapter_guess
        self.pending_update = time.time()
        logger.info(
            "Pending guess primed: %s %d (ambiguous -- awaiting 'verse N' to confirm, "
            "or %ds timeout to fall back to chapter-only)",
            book_name, chapter_guess, self.timeout_seconds,
        )
        # Return a distinguishable "handled, no trigger yet" marker instead
        # of None. A prime succeeding and "no match at all" both used to
        # collapse to None, so the two-chunk/window fallback couldn't tell
        # them apart and kept re-running detection against the same still-
        # ambiguous text -- re-priming (and re-logging) the same guess
        # every escalation level.
        return {"triggered": False, "handled": "primed_pending"}

    def has_pending(self) -> bool:
        if self.pending_book is None:
            return False
        if time.time() - self.pending_update > self.timeout_seconds:
            return False
        return True

    def confirm_pending(self, verse_number: int) -> dict | None:
        """A bare 'verse N' arrived while a pending guess is live -- confirm
        it as book/pending_chapter/verse_number. Returns None if there's no
        live pending guess (caller should fall back to resolve_bare_verse)."""
        if not self.has_pending():
            return None
        result = {
            "book_number": self.pending_book_number,
            "book": self.pending_book,
            "chapter": self.pending_chapter,
            "verse": verse_number,
            "bare_number_confirmed": True,
        }
        logger.info(
            "Pending guess confirmed: %s %d:%d (bare-number match, medium confidence)",
            result["book"], result["chapter"], result["verse"],
        )
        self.update(self.pending_book_number, self.pending_book, self.pending_chapter)
        return result

    def discard_pending(self, reason: str = "") -> None:
        if self.pending_book is None:
            return
        logger.info(
            "Discarding pending guess %s %s%s",
            self.pending_book, self.pending_chapter,
            f" -- {reason}" if reason else "",
        )
        self.pending_book = None
        self.pending_book_number = None
        self.pending_chapter = None
        self.pending_update = 0.0

    def check_pending_timeout(self) -> dict | None:
        """Call this before processing each new chunk. If a pending guess
        has expired without a 'verse N' confirmation, it falls back to a
        plain CHAPTER-ONLY confirm (matches the existing 'Book chapter N'
        convention) -- it is NEVER auto-promoted into a guessed verse.
        Returns the chapter-only event dict if a timeout fired, else None.
        """
        if self.pending_book is None:
            return None
        if time.time() - self.pending_update <= self.timeout_seconds:
            return None
        book, book_number, chapter = self.pending_book, self.pending_book_number, self.pending_chapter
        logger.info(
            "Pending guess %s %d timed out after %ds with no 'verse N' -- "
            "falling back to chapter-only context (NOT a guessed verse)",
            book, chapter, self.timeout_seconds,
        )
        self.update(book_number, book, chapter)
        return {"book_number": book_number, "book": book, "chapter": chapter, "timed_out": True}

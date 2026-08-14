"""
verse_navigation.py

Canonical, DB-backed sequential Bible traversal. The UI never guesses
verse order: every "next verse" / "previous verse" / chapter listing goes
through here, so a book with an unusual chapter count, a chapter with
missing verses, or a single-chapter book all behave correctly without any
hardcoded verse tables.

Everything is driven by what the active BibleDB actually contains
(bible_db.list_book_numbers / list_chapters / list_verse_numbers), so
switching translation or language keeps navigation consistent with the
text that will be displayed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from bible_books import (
    BOOK_NUMBER_TO_CANONICAL,
    NAME_TO_BOOK,
    SINGLE_CHAPTER_BOOKS,
    book_testament,
    french_book_name,
    testament_matches,
)

logger = logging.getLogger("multiverse.verse_navigation")


@dataclass(frozen=True)
class VerseRef:
    book_number: int
    book: str
    chapter: int
    verse: int

    def to_dict(self) -> dict:
        return {
            "book_number": self.book_number,
            "book": self.book,
            "chapter": self.chapter,
            "verse": self.verse,
        }


def resolve_book_number(book: object) -> Optional[int]:
    """Accept a canonical name, an abbreviation, or a book number."""
    if book is None:
        return None
    if isinstance(book, (int, float)) and not isinstance(book, bool):
        return int(book)
    text = str(book).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    lowered = text.lower()
    entry = NAME_TO_BOOK.get(lowered) or NAME_TO_BOOK.get(lowered.replace(" ", ""))
    return entry[0] if entry else None


_REFERENCE_RE = re.compile(
    r"^(?P<book>[0-9a-z\.\s]+?)\s*"
    r"(?P<chapter>\d{1,3})"
    r"(?:\s*[:.\s]\s*(?P<verse>\d{1,3}))?$",
    re.IGNORECASE,
)


def parse_reference(text: str) -> Optional[tuple[int, int, Optional[int]]]:
    """Parse "John 3:16", "1 cor 13", "Jude 4" into (book_number, chapter,
    verse|None). Returns None for anything that isn't a plain reference, so
    phrase searches keep going to the semantic index."""
    if not text:
        return None
    match = _REFERENCE_RE.match(text.strip())
    if not match:
        return None
    book_number = resolve_book_number(" ".join(match.group("book").split()).rstrip("."))
    if book_number is None:
        return None
    chapter = int(match.group("chapter"))
    verse = match.group("verse")
    if verse is None and book_number in SINGLE_CHAPTER_BOOKS:
        # "Jude 4" means Jude 1:4, not chapter 4.
        return book_number, 1, chapter
    return book_number, chapter, int(verse) if verse else None


class VerseNavigator:
    """Sequential navigation over one BibleDB. Cheap per-book caches keep
    repeated arrow presses from re-querying the same chapter list."""

    def __init__(self, bible_db, wrap_books: bool = False):
        self.bible_db = bible_db
        self.wrap_books = wrap_books
        self._books_cache: Optional[list[int]] = None
        self._chapters_cache: dict[int, list[int]] = {}
        self._verses_cache: dict[tuple[int, int], list[int]] = {}

    # ── Structure ────────────────────────────────────────────────────────
    def invalidate(self) -> None:
        self._books_cache = None
        self._chapters_cache.clear()
        self._verses_cache.clear()

    def book_numbers(self) -> list[int]:
        if self._books_cache is None:
            numbers = self.bible_db.list_book_numbers()
            self._books_cache = [n for n in numbers if n in BOOK_NUMBER_TO_CANONICAL]
        return self._books_cache

    def list_books(self, testament: str = "all") -> list[dict]:
        out: list[dict] = []
        for number in self.book_numbers():
            if not testament_matches(number, testament):
                continue
            name = BOOK_NUMBER_TO_CANONICAL[number]
            out.append({
                "book_number": number,
                "book": name,
                "book_french": french_book_name(name),
                "testament": book_testament(number),
                "chapters": len(self.list_chapters(number)),
            })
        return out

    def list_chapters(self, book_number: int) -> list[int]:
        book_number = int(book_number)
        if book_number not in self._chapters_cache:
            self._chapters_cache[book_number] = self.bible_db.list_chapters(book_number)
        return self._chapters_cache[book_number]

    def list_verses(self, book_number: int, chapter: int) -> list[int]:
        key = (int(book_number), int(chapter))
        if key not in self._verses_cache:
            self._verses_cache[key] = self.bible_db.list_verse_numbers(*key)
        return self._verses_cache[key]

    def chapter_verses(self, book_number: int, chapter: int) -> list[dict]:
        return self.bible_db.fetch_chapter(int(book_number), int(chapter))

    # ── Reference resolution ─────────────────────────────────────────────
    def resolve_ref(self, book: object, chapter: object = None,
                    verse: object = None) -> Optional[VerseRef]:
        """Clamp a requested reference onto something this DB actually has.
        A missing chapter/verse resolves to the first available one."""
        book_number = resolve_book_number(book)
        if book_number is None or book_number not in BOOK_NUMBER_TO_CANONICAL:
            return None
        chapters = self.list_chapters(book_number)
        if not chapters:
            return None
        try:
            chapter_num = int(chapter) if chapter is not None else chapters[0]
        except (TypeError, ValueError):
            chapter_num = chapters[0]
        if chapter_num not in chapters:
            return None
        verses = self.list_verses(book_number, chapter_num)
        if not verses:
            return None
        try:
            verse_num = int(verse) if verse is not None else verses[0]
        except (TypeError, ValueError):
            verse_num = verses[0]
        if verse_num not in verses:
            return None
        return VerseRef(
            book_number=book_number,
            book=BOOK_NUMBER_TO_CANONICAL[book_number],
            chapter=chapter_num,
            verse=verse_num,
        )

    def nearest_ref(self, book: object, chapter: object = None,
                    verse: object = None) -> Optional[VerseRef]:
        """Like resolve_ref, but snaps out-of-range chapter/verse to the
        closest existing one instead of failing — used when restoring a
        saved reference after a translation switch."""
        exact = self.resolve_ref(book, chapter, verse)
        if exact is not None:
            return exact
        book_number = resolve_book_number(book)
        if book_number is None:
            return None
        chapters = self.list_chapters(book_number)
        if not chapters:
            return None
        try:
            wanted_chapter = int(chapter)
        except (TypeError, ValueError):
            wanted_chapter = chapters[0]
        chapter_num = min(chapters, key=lambda c: abs(c - wanted_chapter))
        verses = self.list_verses(book_number, chapter_num)
        if not verses:
            return None
        try:
            wanted_verse = int(verse)
        except (TypeError, ValueError):
            wanted_verse = verses[0]
        verse_num = min(verses, key=lambda v: abs(v - wanted_verse))
        return VerseRef(
            book_number=book_number,
            book=BOOK_NUMBER_TO_CANONICAL[book_number],
            chapter=chapter_num,
            verse=verse_num,
        )

    # ── Sequential movement ──────────────────────────────────────────────
    def next_verse(self, ref: VerseRef) -> Optional[VerseRef]:
        return self._step(ref, 1)

    def prev_verse(self, ref: VerseRef) -> Optional[VerseRef]:
        return self._step(ref, -1)

    def navigate(self, ref: VerseRef, direction: int) -> Optional[VerseRef]:
        return self._step(ref, 1 if direction >= 0 else -1)

    def next_chapter(self, ref: VerseRef) -> Optional[VerseRef]:
        return self._step_chapter(ref, 1)

    def prev_chapter(self, ref: VerseRef) -> Optional[VerseRef]:
        return self._step_chapter(ref, -1)

    def _step(self, ref: VerseRef, direction: int) -> Optional[VerseRef]:
        if ref is None:
            return None
        verses = self.list_verses(ref.book_number, ref.chapter)
        if ref.verse in verses:
            index = verses.index(ref.verse) + direction
            if 0 <= index < len(verses):
                return VerseRef(ref.book_number, ref.book, ref.chapter, verses[index])
        elif verses:
            # Verse missing from this file (gap or bad restore) — land on the
            # nearest existing verse in the requested direction.
            candidates = [v for v in verses if (v > ref.verse if direction > 0 else v < ref.verse)]
            if candidates:
                pick = min(candidates) if direction > 0 else max(candidates)
                return VerseRef(ref.book_number, ref.book, ref.chapter, pick)
        return self._step_into_adjacent_chapter(ref, direction)

    def _step_into_adjacent_chapter(self, ref: VerseRef, direction: int) -> Optional[VerseRef]:
        chapters = self.list_chapters(ref.book_number)
        if ref.chapter in chapters:
            index = chapters.index(ref.chapter) + direction
            if 0 <= index < len(chapters):
                chapter = chapters[index]
                verses = self.list_verses(ref.book_number, chapter)
                if verses:
                    verse = verses[0] if direction > 0 else verses[-1]
                    return VerseRef(ref.book_number, ref.book, chapter, verse)
        return self._step_into_adjacent_book(ref, direction)

    def _step_into_adjacent_book(self, ref: VerseRef, direction: int) -> Optional[VerseRef]:
        books = self.book_numbers()
        if ref.book_number not in books:
            return None
        index = books.index(ref.book_number) + direction
        if index < 0 or index >= len(books):
            if not self.wrap_books:
                return None
            index = index % len(books)
        book_number = books[index]
        chapters = self.list_chapters(book_number)
        if not chapters:
            return None
        chapter = chapters[0] if direction > 0 else chapters[-1]
        verses = self.list_verses(book_number, chapter)
        if not verses:
            return None
        verse = verses[0] if direction > 0 else verses[-1]
        return VerseRef(
            book_number=book_number,
            book=BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number)),
            chapter=chapter,
            verse=verse,
        )

    def _step_chapter(self, ref: VerseRef, direction: int) -> Optional[VerseRef]:
        chapters = self.list_chapters(ref.book_number)
        if ref.chapter in chapters:
            index = chapters.index(ref.chapter) + direction
            if 0 <= index < len(chapters):
                chapter = chapters[index]
                verses = self.list_verses(ref.book_number, chapter)
                if verses:
                    return VerseRef(ref.book_number, ref.book, chapter, verses[0])
        edge = VerseRef(
            ref.book_number, ref.book, ref.chapter,
            (self.list_verses(ref.book_number, ref.chapter) or [ref.verse])[-1 if direction > 0 else 0],
        )
        return self._step_into_adjacent_book(edge, direction)

    # ── Verse payloads ───────────────────────────────────────────────────
    def verse_event(self, ref: VerseRef, source: str = "manual") -> Optional[dict]:
        """Build the same shape a detection event has, so preview/broadcast
        rendering (and secondary-language attachment) is identical whether a
        verse came from speech, search, or manual navigation."""
        if ref is None:
            return None
        row = self.bible_db.lookup_verse(ref.book_number, ref.chapter, ref.verse)
        if not row or not row.get("text"):
            logger.warning("No verse row for %s %s:%s", ref.book, ref.chapter, ref.verse)
            return None
        return {
            "triggered": True,
            "source": source,
            "book": ref.book,
            "book_number": ref.book_number,
            "chapter": ref.chapter,
            "verse": ref.verse,
            "text": row["text"],
            "translation": row.get("translation"),
            "confidence": 1.0,
            "confidence_band": "high",
        }

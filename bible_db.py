"""
bible_db.py  —  V4

Replaces the old "guess two or three hardcoded schema variants" approach
with real schema detection (see bible_schema.py). On init, BibleDB resolves
the actual table/column names in the given SQLite file (cached by file
hash, so it only re-scans when the file changes) and builds all queries
from that mapping. No more silent "no such table" failures — if the file
can't be understood, __init__ raises immediately with a clear explanation
of what was found.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional

from bible_schema import resolve_schema, SchemaMapping, SchemaDetectionError

logger = logging.getLogger("windowverse.bible_db")

RANGE_CACHE_PATH = Path("data/range_cache.json")

# Some Bible SQLite exports (this NKJV file included) store verse text with
# embedded markup: <pb/> page-break markers and <f>[1†]</f>-style footnote
# refs. Neither belongs in what gets spoken/displayed. Footnote tags are
# stripped WITH their contents (the bracketed marker isn't verse text);
# everything else that looks like a tag is stripped bare.
_FOOTNOTE_TAG_RE = re.compile(r"<f>.*?</f>", re.IGNORECASE | re.DOTALL)
_ANY_TAG_RE = re.compile(r"<[^>]+>")


def _clean_verse_text(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return raw
    cleaned = _FOOTNOTE_TAG_RE.sub("", raw)
    cleaned = _ANY_TAG_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


class BibleDB:
    def __init__(self, db_path: str, translation: str = "NKJV", force_rescan: bool = False):
        self.db_path = db_path
        self.translation = translation
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Bible DB not found: {db_path}")

        # Resolve schema up front — fail fast and loud, not later mid-session.
        self.schema: SchemaMapping = resolve_schema(db_path, force_rescan=force_rescan)

        # Test connection
        with sqlite3.connect(db_path) as conn:
            conn.execute(f'SELECT 1 FROM "{self.schema.table}" LIMIT 1')

        logger.info(
            "BibleDB connected: %s (table=%s, columns=[%s,%s,%s,%s])",
            db_path, self.schema.table, self.schema.col_book,
            self.schema.col_chapter, self.schema.col_verse, self.schema.col_text,
        )

        # bible_books.py's book_number scheme (10, 20, ..., 660) is one
        # common convention -- not universal. Trusting it blindly against
        # whatever numbering THIS SQLite file actually uses is exactly what
        # produced Job's text for "Song of Solomon 8:1" and an Old
        # Testament line for "Romans 8:1": the regex/lookup machinery ran
        # correctly, it just asked the DB for the wrong row number. Discover
        # the DB's real scheme instead of assuming ours matches it.
        self._book_number_map: dict[int, int] = {}
        self._book_number_map_reverse: dict[int, int] = {}
        if self.schema.book_is_numeric:
            self._book_number_map = self._discover_book_number_map()
            self._book_number_map_reverse = {
                db_num: canon_num for canon_num, db_num in self._book_number_map.items()
            }

        # Chapter/verse bounds, discovered from THIS file (not hardcoded --
        # same "trust the DB, not our assumptions" reasoning as the book-
        # number mapping above). canonical_book_number -> max_chapter, and
        # canonical_book_number -> {chapter: max_verse}. Used by
        # validate_reference() so an out-of-range chapter/verse gets a
        # loud, specific log/UI message instead of a generic "not found".
        self._max_chapter: dict[int, int] = {}
        self._max_verse: dict[int, dict[int, int]] = {}
        self._load_or_build_range_table()

    # ── Chapter/verse range discovery (out-of-range validation) ──────────────
    def _load_or_build_range_table(self) -> None:
        cache = self._read_range_cache()
        if cache is not None:
            self._max_chapter = {int(k): v for k, v in cache["max_chapter"].items()}
            self._max_verse = {
                int(bk): {int(ch): v for ch, v in chmap.items()}
                for bk, chmap in cache["max_verse"].items()
            }
            logger.info("Chapter/verse range table loaded from cache (%s)", RANGE_CACHE_PATH)
            return

        s = self.schema
        from bible_books import BOOKS
        canonical_numbers = {num for num, _, _ in BOOKS}
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f'SELECT "{s.col_book}" AS b, "{s.col_chapter}" AS c, '
                    f'MAX("{s.col_verse}") AS mv FROM "{s.table}" '
                    f'GROUP BY "{s.col_book}", "{s.col_chapter}"'
                ).fetchall()
        except Exception as e:
            logger.error(
                "Could not build chapter/verse range table from %s: %s -- "
                "out-of-range detection will be DISABLED (every reference "
                "will be treated as potentially valid until the DB lookup "
                "itself fails).", self.db_path, e,
            )
            return

        max_chapter: dict[int, int] = {}
        max_verse: dict[int, dict[int, int]] = {}
        unmapped = 0
        for row in rows:
            raw_book, chapter, mv = row["b"], row["c"], row["mv"]
            if s.book_is_numeric:
                # Same identity-fallback convention as _book_lookup_value:
                # an empty reverse map means discovery couldn't build one
                # (see _discover_book_number_map), so assume the DB's own
                # numbers already ARE canonical numbers rather than losing
                # every row to "unmapped".
                book_number = self._book_number_map_reverse.get(raw_book, raw_book)
            else:
                from bible_books import CANONICAL_TO_BOOK_NUMBER
                book_number = CANONICAL_TO_BOOK_NUMBER.get(str(raw_book))
            if book_number is None or book_number not in canonical_numbers:
                unmapped += 1
                continue
            max_chapter[book_number] = max(max_chapter.get(book_number, 0), chapter)
            max_verse.setdefault(book_number, {})[chapter] = mv

        if unmapped:
            logger.warning(
                "%d (book, chapter) rows in %s could not be mapped to a canonical "
                "book number and were skipped while building the range table -- "
                "out-of-range checks for those rows will be unavailable.",
                unmapped, self.db_path,
            )

        self._max_chapter = max_chapter
        self._max_verse = max_verse
        self._write_range_cache()
        logger.info(
            "Chapter/verse range table built from %s: %d books mapped",
            self.db_path, len(max_chapter),
        )

    def _read_range_cache(self) -> Optional[dict]:
        if not RANGE_CACHE_PATH.exists():
            return None
        try:
            data = json.loads(RANGE_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("range_cache.json unreadable (%s) -- rebuilding", e)
            return None
        if data.get("file_hash") != self.schema.file_hash or data.get("db_path") != self.db_path:
            return None
        return data

    def _write_range_cache(self) -> None:
        try:
            RANGE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            RANGE_CACHE_PATH.write_text(
                json.dumps({
                    "db_path": self.db_path,
                    "file_hash": self.schema.file_hash,
                    "max_chapter": self._max_chapter,
                    "max_verse": self._max_verse,
                }),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Could not write range_cache.json: %s -- will rebuild every run", e)

    def validate_reference(self, book_number: int, chapter: int, verse: Optional[int] = None) -> dict:
        """
        Bounds-check a parsed reference against THIS file's real chapter/verse
        counts (discovered at init, see _load_or_build_range_table). Always
        returns a dict -- never raises, never silently passes.

        {"valid": True}                                  -- in range
        {"valid": False, "reason": "no_range_data", ...}  -- book not in the
            discovered table at all (unknown book, or range discovery failed)
        {"valid": False, "reason": "chapter_out_of_range", "max_chapter": N}
        {"valid": False, "reason": "verse_out_of_range", "max_verse": N}
        """
        from bible_books import BOOK_NUMBER_TO_CANONICAL
        book_name = BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number))

        max_ch = self._max_chapter.get(book_number)
        if max_ch is None:
            return {"valid": False, "reason": "no_range_data", "book": book_name}

        if chapter > max_ch or chapter < 1:
            logger.warning(
                "OUT OF RANGE: chapter %d requested for %s, but %s only has %d chapter%s",
                chapter, book_name, book_name, max_ch, "" if max_ch == 1 else "s",
            )
            return {
                "valid": False, "reason": "chapter_out_of_range",
                "book": book_name, "requested_chapter": chapter, "max_chapter": max_ch,
            }

        if verse is not None:
            max_v = self._max_verse.get(book_number, {}).get(chapter)
            if max_v is None:
                return {"valid": False, "reason": "no_range_data", "book": book_name}
            if verse > max_v or verse < 1:
                logger.warning(
                    "OUT OF RANGE: verse %d requested for %s %d, but %s %d only has %d verse%s",
                    verse, book_name, chapter, book_name, chapter, max_v, "" if max_v == 1 else "s",
                )
                return {
                    "valid": False, "reason": "verse_out_of_range",
                    "book": book_name, "chapter": chapter,
                    "requested_verse": verse, "max_verse": max_v,
                }

        return {"valid": True}

    def _discover_book_number_map(self) -> dict[int, int]:
        """
        Read the DB's own distinct book numbers, ascending, and assume (true
        for essentially every canonical 66-book export) that ascending
        book_number == canonical reading order Genesis..Revelation. Zip that
        1:1 against bible_books.py's 66 canonical numbers to build a real
        canonical -> DB translation table. If the DB doesn't have exactly 66
        distinct book numbers, this assumption isn't safe -- log loudly and
        fall back to identity (old behavior) rather than guessing further.
        """
        from bible_books import BOOKS
        s = self.schema
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f'SELECT DISTINCT "{s.col_book}" FROM "{s.table}" ORDER BY "{s.col_book}"'
                ).fetchall()
            db_numbers = [row[0] for row in rows]
        except Exception as e:
            logger.error(
                "Could not discover book-number scheme from %s: %s -- "
                "falling back to hardcoded bible_books.py numbering, which "
                "may be WRONG for this file (verse text could come back "
                "for the wrong book).", self.db_path, e,
            )
            return {}

        canonical_numbers = [num for num, _, _ in BOOKS]
        if len(db_numbers) != len(canonical_numbers):
            logger.error(
                "%s has %d distinct book numbers, expected %d for a "
                "standard 66-book canon -- can't safely auto-map book "
                "numbering. Falling back to hardcoded bible_books.py "
                "numbering; verse lookups may return the WRONG verse for "
                "any book whose number differs from ours. Run "
                "inspect_bible_db.py on this file and check it manually.",
                self.db_path, len(db_numbers), len(canonical_numbers),
            )
            return {}

        mapping = dict(zip(canonical_numbers, db_numbers))
        if mapping == {n: n for n in canonical_numbers}:
            logger.info("DB book-number scheme matches bible_books.py exactly — no mapping needed")
        else:
            sample_canon = canonical_numbers[42]  # John, for a concrete example in the log
            logger.warning(
                "DB book-number scheme differs from bible_books.py's hardcoded "
                "numbering — auto-mapped all %d books to this file's real "
                "numbers (e.g. canonical %d -> DB %d). Verse lookups now use "
                "the discovered mapping instead of the hardcoded one.",
                len(mapping), sample_canon, mapping[sample_canon],
            )
        return mapping

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _book_lookup_value(self, book_number: int):
        """Convert a canonical book_number into whatever the DB's book
        column actually expects — either this file's own discovered
        numbering (see _discover_book_number_map), or the canonical name
        string for non-numeric schemas."""
        if self.schema.book_is_numeric:
            return self._book_number_map.get(book_number, book_number)
        from bible_books import BOOK_NUMBER_TO_CANONICAL
        return BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number))

    def lookup_verse(self, book_number: int, chapter: int, verse: int,
                     translation: Optional[str] = None) -> Optional[dict]:
        """Look up a single verse using the schema resolved at init time."""
        s = self.schema
        book_val = self._book_lookup_value(book_number)
        query = (
            f'SELECT "{s.col_book}" AS b, "{s.col_chapter}" AS c, '
            f'"{s.col_verse}" AS v, "{s.col_text}" AS t FROM "{s.table}" '
            f'WHERE "{s.col_book}" = ? AND "{s.col_chapter}" = ? AND "{s.col_verse}" = ?'
        )
        try:
            with self._connect() as conn:
                row = conn.execute(query, (book_val, chapter, verse)).fetchone()
                if row:
                    return self._format_row(row, book_number, chapter, verse, translation)
        except Exception as e:
            logger.error("lookup_verse failed (table=%s): %s", s.table, e)
        return None

    def _format_row(self, row, book_number: int, chapter: int, verse: int,
                     translation: Optional[str] = None) -> dict:
        from bible_books import BOOK_NUMBER_TO_CANONICAL
        return {
            "book_number": book_number,
            "book": BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number)),
            "chapter": chapter,
            "verse": verse,
            "text": _clean_verse_text(row["t"]),
            "translation": translation or self.translation,
        }

    def get_max_chapter(self, book_number: int) -> Optional[int]:
        """Highest chapter number this file holds for *book_number*."""
        return self._max_chapter.get(int(book_number))

    def get_chapter_verse_count(self, book_number: int, chapter: int) -> Optional[int]:
        """Highest verse number this file holds for book/chapter."""
        return self._max_verse.get(int(book_number), {}).get(int(chapter))

    def list_book_numbers(self) -> list[int]:
        """Canonical book numbers actually present in this file, in order."""
        return sorted(self._max_chapter.keys())

    def list_chapters(self, book_number: int) -> list[int]:
        """Chapter numbers present for *book_number*, ascending."""
        chapters = self._max_verse.get(int(book_number))
        if chapters:
            return sorted(chapters.keys())
        s = self.schema
        book_val = self._book_lookup_value(book_number)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f'SELECT DISTINCT "{s.col_chapter}" AS c FROM "{s.table}" '
                    f'WHERE "{s.col_book}" = ? ORDER BY "{s.col_chapter}"',
                    (book_val,),
                ).fetchall()
            return [row["c"] for row in rows]
        except Exception as e:
            logger.error("list_chapters failed (table=%s): %s", s.table, e)
            return []

    def list_verse_numbers(self, book_number: int, chapter: int) -> list[int]:
        """Verse numbers present for book/chapter, ascending. Read from the
        DB rather than assuming 1..max — some exports have gaps."""
        s = self.schema
        book_val = self._book_lookup_value(book_number)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f'SELECT "{s.col_verse}" AS v FROM "{s.table}" '
                    f'WHERE "{s.col_book}" = ? AND "{s.col_chapter}" = ? '
                    f'ORDER BY "{s.col_verse}"',
                    (book_val, chapter),
                ).fetchall()
            return [row["v"] for row in rows]
        except Exception as e:
            logger.error("list_verse_numbers failed (table=%s): %s", s.table, e)
            return []

    def fetch_chapter(self, book_number: int, chapter: int,
                      translation: Optional[str] = None) -> list[dict]:
        """Every verse of one chapter, ascending — for the Scripture Browser."""
        s = self.schema
        book_val = self._book_lookup_value(book_number)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f'SELECT "{s.col_verse}" AS v, "{s.col_text}" AS t FROM "{s.table}" '
                    f'WHERE "{s.col_book}" = ? AND "{s.col_chapter}" = ? '
                    f'ORDER BY "{s.col_verse}"',
                    (book_val, chapter),
                ).fetchall()
        except Exception as e:
            logger.error("fetch_chapter failed (table=%s): %s", s.table, e)
            return []
        from bible_books import BOOK_NUMBER_TO_CANONICAL
        book_name = BOOK_NUMBER_TO_CANONICAL.get(book_number, str(book_number))
        return [{
            "book_number": book_number,
            "book": book_name,
            "chapter": chapter,
            "verse": row["v"],
            "text": _clean_verse_text(row["t"]),
            "translation": translation or self.translation,
        } for row in rows]

    def fetch_all_verses(self, translation: Optional[str] = None) -> list[dict]:
        """Return all verses for building the semantic index."""
        s = self.schema
        query = (
            f'SELECT "{s.col_book}" AS b, "{s.col_chapter}" AS c, '
            f'"{s.col_verse}" AS v, "{s.col_text}" AS t FROM "{s.table}" '
            f'ORDER BY "{s.col_book}", "{s.col_chapter}", "{s.col_verse}"'
        )
        try:
            with self._connect() as conn:
                rows = conn.execute(query).fetchall()
                from bible_books import BOOK_NUMBER_TO_CANONICAL, CANONICAL_TO_BOOK_NUMBER
                result = []
                for row in rows:
                    raw_book = row["b"]
                    if s.book_is_numeric:
                        bn = self._book_number_map_reverse.get(raw_book, raw_book)
                    else:
                        bn = CANONICAL_TO_BOOK_NUMBER.get(str(raw_book), None)
                    result.append({
                        "book_number": bn,
                        "book": BOOK_NUMBER_TO_CANONICAL.get(bn, str(raw_book)),
                        "chapter": row["c"],
                        "verse": row["v"],
                        "text": _clean_verse_text(row["t"]),
                        "translation": translation or self.translation,
                    })
                return result
        except Exception as e:
            logger.error("fetch_all_verses failed (table=%s): %s", s.table, e)
            return []


# V1-compatible module-level function for any code that imports it directly
def get_verse(book_name: str, chapter: int, verse: int) -> Optional[dict]:
    """V1-compatible standalone function. Uses default DB path from config."""
    import configparser
    from bible_books import CANONICAL_TO_BOOK_NUMBER

    cfg = configparser.ConfigParser()
    cfg.read("config/config.ini")
    db_path = cfg.get("database", "db_path", fallback="data/NKJV.SQLite3")
    try:
        db = BibleDB(db_path)
        book_number = CANONICAL_TO_BOOK_NUMBER.get(book_name)
        if book_number is None:
            logger.error("get_verse: unknown book name '%s'", book_name)
            return None
        return db.lookup_verse(book_number, chapter, verse)
    except Exception as e:
        logger.error("get_verse failed: %s", e)
    return None

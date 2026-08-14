"""
bible_schema.py

Automatic schema detection for Bible SQLite databases.

Problem this solves: WindowVerse previously guessed at table/column names
("bible" table with b/c/v/t columns, or BookName/Chapter/VerseNumber/
VerseText) and silently failed when a different Bible database didn't
match those guesses. This module actually inspects the database file
(sqlite_master + PRAGMA table_info) and resolves a mapping, so swapping
in a new translation/database "just works" without editing code.

Public entry point: resolve_schema(db_path) -> SchemaMapping
Results are cached on disk (data/schema_cache.json) keyed by file path
and a hash of the file, so a given DB file is only scanned once until
it changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("windowverse.bible_schema")

CACHE_PATH = Path("data/schema_cache.json")

# Keyword groups used to score candidate columns for each logical field.
# Order matters slightly (first match wins on ties) but scoring is what
# actually decides it.
FIELD_KEYWORDS = {
    "book": ["bookname", "book_name", "book", "bk", "b"],
    "chapter": ["chapter", "chap", "ch", "c"],
    "verse": ["versenumber", "verse_number", "verse", "vs", "v"],
    "text": ["versetext", "verse_text", "scripturetext", "scripture_text",
              "text", "content", "scripture", "t"],
}

# Minimum combined confidence (0-4, one point per required field found)
# before we trust a table as "the" Bible verse table.
MIN_REQUIRED_FIELDS = 4  # book, chapter, verse, text must ALL be found


@dataclass
class SchemaMapping:
    table: str
    col_book: str
    col_chapter: str
    col_verse: str
    col_text: str
    book_is_numeric: bool  # True if the book column holds numbers, not names
    file_hash: str
    db_path: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "SchemaMapping":
        return SchemaMapping(**d)


class SchemaDetectionError(Exception):
    """Raised when no table in the database looks like a usable verse table."""
    pass


def _file_hash(db_path: str, block_size: int = 65536) -> str:
    """Hash file size + first/last blocks — fast, good enough to detect
    'this is a different file than last time', not meant to be cryptographic."""
    p = Path(db_path)
    size = p.stat().st_size
    h = hashlib.sha256()
    h.update(str(size).encode())
    with open(p, "rb") as f:
        h.update(f.read(block_size))
        if size > block_size:
            f.seek(max(0, size - block_size))
            h.update(f.read(block_size))
    return h.hexdigest()[:16]


def _score_column(col_name: str, keywords: list[str]) -> int:
    """Higher score = better match. Exact match beats substring match."""
    name = col_name.lower().replace(" ", "").replace("_", "")
    for i, kw in enumerate(keywords):
        kw_norm = kw.replace("_", "")
        if name == kw_norm:
            return 100 - i  # exact match, prefer earlier (more specific) keywords
    for i, kw in enumerate(keywords):
        kw_norm = kw.replace("_", "")
        if len(kw_norm) > 1 and kw_norm in name:
            return 50 - i  # substring match
    return 0


def _list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [r[0] for r in rows]


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return [r[1] for r in rows]


def _detect_book_is_numeric(conn: sqlite3.Connection, table: str, col: str) -> bool:
    try:
        row = conn.execute(f'SELECT "{col}" FROM "{table}" LIMIT 1').fetchone()
        if row is None:
            return True  # empty table, assume numeric (matches original default)
        val = row[0]
        return isinstance(val, (int, float))
    except Exception:
        return True


def _score_table(conn: sqlite3.Connection, table: str, columns: list[str]) -> Optional[dict]:
    """Return best column mapping for this table plus a total score,
    or None if it doesn't look like a verse table at all."""
    best = {}
    total_score = 0
    fields_found = 0

    for field, keywords in FIELD_KEYWORDS.items():
        best_col = None
        best_score = 0
        for col in columns:
            s = _score_column(col, keywords)
            if s > best_score:
                best_score = s
                best_col = col
        if best_col and best_score > 0:
            best[field] = best_col
            total_score += best_score
            fields_found += 1

    if fields_found < MIN_REQUIRED_FIELDS:
        return None

    # Row-count sanity check: a real Bible table has thousands of rows
    # (NKJV has ~31,000 verses). This filters out unrelated small tables
    # that happen to have generically-named columns.
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except Exception:
        count = 0

    if count < 1000:
        return None

    return {
        "columns": best,
        "score": total_score,
        "row_count": count,
    }


def detect_schema(db_path: str) -> SchemaMapping:
    """Scan the database file and resolve the best-matching verse table
    and column mapping. Raises SchemaDetectionError if nothing usable
    is found, with details on what WAS found so the user can diagnose it."""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Bible DB not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        tables = _list_tables(conn)
        if not tables:
            raise SchemaDetectionError(
                f"'{db_path}' has no tables at all — is this a valid SQLite file?"
            )

        candidates = []
        inspected = {}
        for table in tables:
            columns = _table_columns(conn, table)
            inspected[table] = columns
            result = _score_table(conn, table, columns)
            if result:
                candidates.append((table, result))

        if not candidates:
            details = "\n".join(f"  - {t}: columns={cols}" for t, cols in inspected.items())
            raise SchemaDetectionError(
                f"Could not find a usable verse table in '{db_path}'.\n"
                f"Tables found:\n{details}\n"
                f"Expected a table with columns identifiable as book/chapter/verse/text "
                f"(e.g. b/c/v/t or BookName/Chapter/VerseNumber/VerseText) and >= 1000 rows."
            )

        # Highest score wins; tie-break by row count (bigger table more likely correct)
        candidates.sort(key=lambda tc: (tc[1]["score"], tc[1]["row_count"]), reverse=True)
        table, result = candidates[0]
        cols = result["columns"]

        book_is_numeric = _detect_book_is_numeric(conn, table, cols["book"])

        mapping = SchemaMapping(
            table=table,
            col_book=cols["book"],
            col_chapter=cols["chapter"],
            col_verse=cols["verse"],
            col_text=cols["text"],
            book_is_numeric=book_is_numeric,
            file_hash=_file_hash(db_path),
            db_path=str(Path(db_path).resolve()),
        )

        logger.info(
            "Schema detected for %s -> table=%s book=%s chapter=%s verse=%s text=%s "
            "(book_is_numeric=%s, row_count=%s, %d table(s) considered)",
            db_path, mapping.table, mapping.col_book, mapping.col_chapter,
            mapping.col_verse, mapping.col_text, mapping.book_is_numeric,
            result["row_count"], len(candidates),
        )

        if len(candidates) > 1:
            others = ", ".join(t for t, _ in candidates[1:])
            logger.info("Other candidate table(s) considered but not chosen: %s", others)

        return mapping


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Schema cache unreadable (%s), ignoring it.", e)
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not write schema cache: %s", e)


def resolve_schema(db_path: str, force_rescan: bool = False) -> SchemaMapping:
    """Main entry point. Returns a cached mapping if the file hasn't
    changed since last time; otherwise re-detects and updates the cache.
    """
    key = str(Path(db_path).resolve())
    cache = _load_cache()

    current_hash = None
    if not force_rescan and key in cache:
        try:
            current_hash = _file_hash(db_path)
        except Exception:
            current_hash = None
        cached_entry = cache[key]
        if current_hash and cached_entry.get("file_hash") == current_hash:
            logger.info("Using cached schema for %s (unchanged since last scan)", db_path)
            return SchemaMapping.from_dict(cached_entry)
        else:
            logger.info("DB file changed since last scan (or force_rescan) — re-detecting schema for %s", db_path)

    mapping = detect_schema(db_path)
    cache[key] = mapping.to_dict()
    _save_cache(cache)
    return mapping


def clear_cache(db_path: Optional[str] = None) -> None:
    """Clear the schema cache. If db_path given, clear only that entry."""
    if db_path is None:
        if CACHE_PATH.exists():
            CACHE_PATH.unlink()
        logger.info("Schema cache cleared entirely.")
        return
    cache = _load_cache()
    key = str(Path(db_path).resolve())
    if key in cache:
        del cache[key]
        _save_cache(cache)
        logger.info("Schema cache entry cleared for %s", db_path)

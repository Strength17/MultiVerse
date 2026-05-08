# core/bible_db.py
import sqlite3
import logging
import configparser
import os
from typing import Optional, List, Dict
from data.book_names import BIBLE_BOOKS

# Locate config file - prioritizing config/config.ini as per project structure
config = configparser.ConfigParser()
config_path = 'config/config.ini'
if not os.path.exists(config_path):
    config_path = 'config.ini' # Fallback to root

if os.path.exists(config_path):
    config.read(config_path)
else:
    logging.warning(f"Config file not found at {config_path}, using defaults.")

DB_PATH = config.get('database', 'db_path', fallback='data/KJVBible_Database.db')

logger = logging.getLogger(__name__)

# ID -> Name mapping (1-based index)
BOOK_ID_TO_NAME = {i + 1: name for i, name in enumerate(BIBLE_BOOKS.keys())}
# Name -> ID mapping
BOOK_NAME_TO_ID = {name: i + 1 for i, name in enumerate(BIBLE_BOOKS.keys())}

def build_ref(book_id_or_name, chapter, verse) -> str:
    """Utility to build reference string with canonical book name."""
    if isinstance(book_id_or_name, int):
        book_name = BOOK_ID_TO_NAME.get(book_id_or_name, str(book_id_or_name))
    else:
        book_name = book_id_or_name
    return f"{book_name} {chapter}:{verse}"

class BibleDB:
    """Interface for the local KJV Bible SQLite database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found at {self.db_path}")
        self._ensure_fts_index()

    def _get_connection(self):
        """Create a new connection for the calling thread."""
        return sqlite3.connect(self.db_path)

    def _ensure_fts_index(self):
        """Ensures FTS5 virtual table exists. Only rebuilds if missing."""
        try:
            with self._get_connection() as conn:
                # Check if bible_fts already exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bible_fts'")
                if not cursor.fetchone():
                    logger.info("FTS5 index missing. Building now...")
                    conn.execute("""
                        CREATE VIRTUAL TABLE bible_fts USING fts5(
                            Book, Chapter, VerseNumber, Verse,
                            content='bible',
                            content_rowid='rowid'
                        )
                    """)
                    conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
                    conn.commit()
                    logger.info("FTS5 index built successfully.")
                else:
                    logger.debug("FTS5 index already exists.")
        except sqlite3.Error as e:
            logger.error(f"FTS5 initialization error: {e}")

    def search_fts(self, query: str, limit: int = 200) -> List[Dict]:
        """Full-text search. Returns list of {reference, verse, snippet} dicts."""
        if not query.strip():
            return []
        clean = query.strip().replace('"', '').replace("'", "")
        fts_query = " OR ".join(f'"{word}"' for word in clean.split()[:5])
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT b.Book, b.Chapter, b.VerseNumber, b.Verse,
                           highlight(bible_fts, 3, '<MATCH>', '</MATCH>') as snippet
                    FROM bible_fts
                    JOIN bible b ON bible_fts.rowid = b.rowid
                    WHERE bible_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (fts_query, limit))
                rows = cursor.fetchall()
            return [{"reference": build_ref(r[0], r[1], r[2]), "verse": r[3], "snippet": r[4]}
                    for r in rows]
        except sqlite3.Error as e:
            logger.error(f"FTS5 search error: {e}")
            return []

    def search_like(self, query: str, limit: int = 200) -> List[Dict]:
        """LIKE-based search for short queries where FTS is less effective."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT Book, Chapter, VerseNumber, Verse FROM bible
                    WHERE LOWER(Verse) LIKE LOWER(?)
                    LIMIT ?
                """, (f"%{query}%", limit))
                return [{"reference": build_ref(r[0], r[1], r[2]), "verse": r[3], "snippet": r[3]}
                        for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database search error: {e}")
            return []

    def lookup_verse(self, book: str | int, chapter: int, verse: int) -> Optional[str]:
        """Lookup verse text by Book (Name or ID), Chapter (INT), VerseNumber (INT)."""
        if isinstance(book, str):
            book_id = BOOK_NAME_TO_ID.get(book)
            if book_id is None:
                # Try fuzzy match as last resort or if it's a name variation
                logger.warning(f"Unknown book name: {book}. DB lookup may fail.")
                book_id = book
        else:
            book_id = book

        query = "SELECT Verse FROM bible WHERE Book=? AND Chapter=? AND VerseNumber=?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (book_id, chapter, verse))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Database lookup error: {e}")
            return None

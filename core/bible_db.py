# core/bible_db.py
import sqlite3
import logging
import configparser
import os
from typing import Optional, List, Dict

# Load config to get db path
config = configparser.ConfigParser()
config.read('config.ini')
DB_PATH = config.get('database', 'db_path', fallback='data/KJVBible_Database.db')

logger = logging.getLogger(__name__)

def build_ref(book, chapter, verse) -> str:
    """Utility to build reference string."""
    return f"{book} {chapter}:{verse}"

class BibleDB:
    """Interface for the local KJV Bible SQLite database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found at {self.db_path}")
        self._build_fts_index()

    def _get_connection(self):
        """Create a new connection for the calling thread."""
        return sqlite3.connect(self.db_path)

    def _build_fts_index(self):
        """Creates FTS5 virtual table for lightning-fast text search. Idempotent."""
        try:
            with self._get_connection() as conn:
                # We need columns that match the 'bible' table for external content
                conn.execute("DROP TABLE IF EXISTS bible_fts")
                conn.execute("""
                    CREATE VIRTUAL TABLE bible_fts USING fts5(
                        Book, Chapter, VerseNumber, Verse,
                        content='bible',
                        content_rowid='rowid'
                    )
                """)
                conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
                conn.commit()
                logger.info("FTS5 index ready.")
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
                           highlight(bible_fts, 1, '<MATCH>', '</MATCH>') as snippet
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

    def lookup_verse(self, book_number: int, chapter: int, verse: int) -> Optional[str]:
        """Lookup verse text by Book (INT), Chapter (INT), VerseNumber (INT)."""
        query = "SELECT Verse FROM bible WHERE Book=? AND Chapter=? AND VerseNumber=?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (book_number, chapter, verse))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Database lookup error: {e}")
            return None

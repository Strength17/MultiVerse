# core/bible_db.py
import sqlite3
import logging
import configparser
import os
from typing import Optional, List, Tuple

# Load config to get db path
config = configparser.ConfigParser()
config.read('config.ini')
DB_PATH = config.get('database', 'db_path', fallback='data/KJVBible_Database.db')

logger = logging.getLogger(__name__)

class BibleDB:
    """Interface for the local KJV Bible SQLite database."""

    def __init__(self, db_path: str = DB_PATH):
        """Initialize connection path. Connection is opened per-thread."""
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            logger.error(f"Database file not found at {self.db_path}")

    def _get_connection(self):
        """Create a new connection for the calling thread."""
        return sqlite3.connect(self.db_path)

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

    def search_verse(self, keyword: str) -> List[Tuple[int, int, int, str]]:
        """Search in Verse TEXT column for a keyword."""
        query = "SELECT Book, Chapter, VerseNumber, Verse FROM bible WHERE Verse LIKE ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, ('%' + keyword + '%',))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database search error: {e}")
            return []

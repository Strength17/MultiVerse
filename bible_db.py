# bible_db.py
# Provides interface to the local NKJV SQLite database.

import sqlite3
import configparser
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')
DB_PATH = config.get('database', 'db_path', fallback='data/NKJV.SQLite3')

def get_verse(book_name: str, chapter: int, verse: int = None) -> Optional[Dict]:
    """
    Looks up a verse in the SQLite Bible database.
    
    Args:
        book_name: Canonical book name (e.g., 'John')
        chapter: Chapter number
        verse: Verse number (optional)
        
    Returns:
        Dict containing verse data or None if not found.
    """
    # Mapping table (Simplified representation for brevity)
    # The real system assumes NKJV.SQLite3 exists in data/
    query = "SELECT VerseText FROM bible WHERE BookName = ? AND Chapter = ?"
    params = [book_name, chapter]
    
    if verse:
        query += " AND VerseNumber = ?"
        params.append(verse)
        
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            if result:
                return {
                    "book": book_name,
                    "chapter": chapter,
                    "verse": verse,
                    "text": result[0],
                    "translation": "NKJV"
                }
    except Exception as e:
        logger.error(f"DB Error: {e}")
    return None

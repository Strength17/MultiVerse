# bible_db.py

import sqlite3
import re
import configparser
import logging
from typing import Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UPDATED BOOK MAPPING based on actual data/NKJV.SQLite3
BOOK_NAME_TO_NUMBER = {
    "Genesis": 10, "Gen": 10, "Exodus": 20, "Ex": 20, "Leviticus": 30, "Lev": 30,
    "Numbers": 40, "Num": 40, "Deuteronomy": 50, "Deut": 50, "Joshua": 60, "Josh": 60,
    "Judges": 70, "Judg": 70, "Ruth": 80,
    "1 Samuel": 90, "First Samuel": 90, "1Samuel": 90, "1Sam": 90,
    "2 Samuel": 100, "Second Samuel": 100, "2Samuel": 100, "2Sam": 100,
    "1 Kings": 110, "First Kings": 110, "1Kings": 110, "1Kin": 110,
    "2 Kings": 120, "Second Kings": 120, "2Kings": 120, "2Kin": 120,
    "1 Chronicles": 130, "First Chronicles": 130, "1Chron": 130,
    "2 Chronicles": 140, "Second Chronicles": 140, "2Chron": 140,
    "Ezra": 150, "Nehemiah": 160, "Neh": 160, "Esther": 190,
    "Job": 220, "Psalms": 230, "Psalm": 230, "Ps": 230,
    "Proverbs": 240, "Prov": 240, "Ecclesiastes": 250, "Ecc": 250,
    "Song of Solomon": 260, "Song": 260, "Isaiah": 290, "Isa": 290,
    "Jeremiah": 300, "Jer": 300, "Lamentations": 310, "Lam": 310,
    "Ezekiel": 330, "Ezek": 330, "Daniel": 340, "Dan": 340,
    "Hosea": 350, "Joel": 360, "Amos": 370, "Obadiah": 380, "Jonah": 390,
    "Micah": 400, "Nahum": 410, "Habakkuk": 420, "Habakuk": 420,
    "Zephaniah": 430, "Zeph": 430, "Haggai": 440, "Zechariah": 450, "Zech": 450, "Malachi": 460,
    "Matthew": 470, "Matt": 470, "Mark": 480, "Luke": 490, "John": 500, "Acts": 510,
    "Romans": 520, "Rom": 520, "1 Corinthians": 530, "First Corinthians": 530, "1Cor": 530,
    "2 Corinthians": 540, "Second Corinthians": 540, "2Cor": 540, "Galatians": 550, "Gal": 550,
    "Ephesians": 560, "Eph": 560, "Philippians": 570, "Phil": 570, "Philipians": 570,
    "Colossians": 580, "Col": 580, "1 Thessalonians": 590, "First Thessalonians": 590,
    "2 Thessalonians": 600, "Second Thessalonians": 600, "1 Timothy": 610, "First Timothy": 610,
    "2 Timothy": 620, "Second Timothy": 620, "Titus": 630, "Philemon": 640,
    "Hebrews": 650, "Heb": 650, "James": 660, "Jam": 660,
    "1 Peter": 670, "First Peter": 670, "2 Peter": 680, "Second Peter": 680,
    "1 John": 690, "First John": 690, "2 John": 700, "Second John": 700,
    "3 John": 710, "Third John": 710, "Jude": 720, "Revelation": 730, "Rev": 730, "Revelations": 730,
}

BOOK_NUMBER_TO_CANONICAL = {
    10: "Genesis", 20: "Exodus", 30: "Leviticus", 40: "Numbers", 50: "Deuteronomy",
    60: "Joshua", 70: "Judges", 80: "Ruth", 90: "1 Samuel", 100: "2 Samuel",
    110: "1 Kings", 120: "2 Kings", 130: "1 Chronicles", 140: "2 Chronicles",
    150: "Ezra", 160: "Nehemiah", 190: "Esther", 220: "Job", 230: "Psalms",
    240: "Proverbs", 250: "Ecclesiastes", 260: "Song of Solomon", 290: "Isaiah",
    300: "Jeremiah", 310: "Lamentations", 330: "Ezekiel", 340: "Daniel",
    350: "Hosea", 360: "Joel", 370: "Amos", 380: "Obadiah", 390: "Jonah",
    400: "Micah", 410: "Nahum", 420: "Habakkuk", 430: "Zephaniah", 440: "Haggai",
    450: "Zechariah", 460: "Malachi", 470: "Matthew", 480: "Mark", 490: "Luke",
    500: "John", 510: "Acts", 520: "Romans", 530: "1 Corinthians",
    540: "2 Corinthians", 550: "Galatians", 560: "Ephesians", 570: "Philippians",
    580: "Colossians", 590: "1 Thessalonians", 600: "2 Thessalonians",
    610: "1 Timothy", 620: "2 Timothy", 630: "Titus", 640: "Philemon",
    650: "Hebrews", 660: "James", 670: "1 Peter", 680: "2 Peter", 690: "1 John",
    700: "2 John", 710: "3 John", 720: "Jude", 730: "Revelation",
}

# Load config
config = configparser.ConfigParser()
config.read('config.ini')
DB_PATH = config.get('database', 'db_path', fallback='data/NKJV.SQLite3')
TRANSLATION = config.get('database', 'translation', fallback='NKJV')

def clean_verse_text(raw: str) -> str:
    """
    Strips HTML-like markup from raw verse text.
    """
    # Remove footnote references: <f>[1†]</f>
    text = re.sub(r'<f>\[.*?†\]</f>', '', raw)
    # Strip remaining tags: <pb/>, <i>, etc.
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_verse(book_name: str, chapter: int, verse: int) -> Optional[dict]:
    """
    Fetches a verse from the SQLite database.
    """
    # Normalize book name
    book_id = BOOK_NAME_TO_NUMBER.get(book_name)
    if not book_id:
        # Try fuzzy match as fallback in DB module too
        from rapidfuzz import process, fuzz
        result = process.extractOne(book_name, list(BOOK_NAME_TO_NUMBER.keys()), scorer=fuzz.WRatio)
        if result and result[1] >= 85:
            book_id = BOOK_NAME_TO_NUMBER[result[0]]
        else:
            return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            query = "SELECT text FROM verses WHERE book_number = ? AND chapter = ? AND verse = ?"
            cursor.execute(query, (book_id, chapter, verse))
            row = cursor.fetchone()
            
            if row:
                raw_text = row[0]
                clean_text = clean_verse_text(raw_text)
                return {
                    "book": BOOK_NUMBER_TO_CANONICAL[book_id],
                    "chapter": chapter,
                    "verse": verse,
                    "text": clean_text,
                    "translation": TRANSLATION
                }
    except Exception as e:
        logger.error(f"Database error: {e}")
        
    return None

if __name__ == '__main__':
    # Test Phase 2 verification
    res = get_verse('John', 3, 16)
    if res:
        print(f"PASS: {res['book']} {res['chapter']}:{res['verse']} ({res['translation']})")
        print(f"Text: {res['text'][:100]}...")
    else:
        print("FAIL: Verse not found.")

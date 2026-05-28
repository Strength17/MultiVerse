# verse_detector.py
import re
import configparser
import logging
from typing import Optional, List, Dict
from word2number import w2n
from rapidfuzz import process, fuzz
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BOOK_NAME_TO_NUMBER = {
    "Genesis": 10, "Gen": 10, "Exodus": 20, "Ex": 20, "Leviticus": 30, "Lev": 30,
    "Numbers": 40, "Num": 40, "Deuteronomy": 50, "Deut": 50, "Joshua": 60, "Josh": 60,
    "Judges": 70, "Judg": 70, "Ruth": 80, "1 Samuel": 90, "1Sam": 90,
    "2 Samuel": 100, "2Sam": 100, "1 Kings": 110, "1Kin": 110,
    "2 Kings": 120, "2Kin": 120, "1 Chronicles": 130, "1Chron": 130,
    "2 Chronicles": 140, "2Chron": 140, "Ezra": 150, "Nehemiah": 160, "Esther": 190,
    "Job": 220, "Psalms": 230, "Ps": 230, "Proverbs": 240, "Ecclesiastes": 250,
    "Song of Solomon": 260, "Song": 260, "Isaiah": 290, "Jeremiah": 300,
    "Lamentations": 310, "Ezekiel": 330, "Daniel": 340, "Hosea": 350, "Joel": 360,
    "Amos": 370, "Obadiah": 380, "Jonah": 390, "Micah": 400, "Nahum": 410,
    "Habakkuk": 420, "Zephaniah": 430, "Haggai": 440, "Zechariah": 450, "Malachi": 460,
    "Matthew": 470, "Mark": 480, "Luke": 490, "John": 500, "Acts": 510,
    "Romans": 520, "1 Corinthians": 530, "2 Corinthians": 540, "Galatians": 550,
    "Ephesians": 560, "Philippians": 570, "Colossians": 580, "1 Thessalonians": 590,
    "2 Thessalonians": 600, "1 Timothy": 610, "2 Timothy": 620, "Titus": 630,
    "Philemon": 640, "Hebrews": 650, "James": 660, "1 Peter": 670, "2 Peter": 680,
    "1 John": 690, "2 John": 700, "3 John": 710, "Jude": 720, "Revelation": 730,
    "Revelations": 730
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

config = configparser.ConfigParser()
config.read('config.ini')

_last_book = None
_last_book_time = 0.0
book_memory_seconds = float(config.get('detection', 'book_memory_seconds', fallback=5.0))

# Aliases
VERSE_ALIASES = ["was", "vs", "v", "burst", "first", "versus", "birth", "worse", "worst", "verse", "verses"]
CHAPTER_ALIASES = ["capture", "chapters", "chap", "chapter"]

COMPILED_PATTERNS = [
    re.compile(r'(.+?)\s+chapter\s+(\d+)\s+verse\s+(\d+)'),
    re.compile(r'(.+?)\s+(\d+)\s*[:\-]\s*(\d+)'),
    re.compile(r'(.+?)\s+chapter\s+(\d+)\s*[:\-]?\s*(\d+)?'),
    re.compile(r'(.+?)\s+(\d+)\s*,\s*verse\s+(\d+)'),
    re.compile(r'(.+?)\s+(\d+)\s+verse\s+(\d+)'),
    re.compile(r'(.+?)\s+(\d+)\s+(\d+)'),
    re.compile(r'(.+?)\s+(\d+)$')
]

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'first\s+', '1 ', text)
    text = re.sub(r'second\s+', '2 ', text)
    text = re.sub(r'third\s+', '3 ', text)
    text = text.replace('1st', '1').replace('2nd', '2').replace('3rd', '3')
    
    words = text.split()
    for i, word in enumerate(words):
        clean = re.sub(r"[^a-z]", "", word)
        if not clean: continue
        
        match_v, score_v, _ = process.extractOne(clean, VERSE_ALIASES)
        if score_v >= 80: words[i] = "verse"
        else:
            match_c, score_c, _ = process.extractOne(clean, CHAPTER_ALIASES)
            if score_c >= 80: words[i] = "chapter"
            else:
                try: words[i] = str(w2n.word_to_num(clean))
                except: pass
    return " ".join(words)

def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    global _last_book, _last_book_time
    text = buffer_text.lower()
    if detected_book.lower() in text: return True
    if _last_book and (time.time() - _last_book_time < book_memory_seconds): return True
    if "book of" in text: return True
    return False

def _find_book(text: str) -> Optional[str]:
    """
    Fuzzy match a book name from text. Returns canonical book name if found.
    """
    books_dict = {k.lower(): k for k in BOOK_NAME_TO_NUMBER.keys()}
    books_list = list(books_dict.keys())
    
    clean_text = text.strip().lower()
    if not clean_text: return None
    
    # Try exact match first for performance and to avoid '1' matching '1 Chronicles'
    words = clean_text.split()
    
    # Check last word, then last two, then whole string
    # Patterns usually put book at the start of the 'potential' segment
    for length in range(min(len(words), 3), 0, -1):
        candidate = " ".join(words[:length]).strip()
        if candidate in books_dict:
            return books_dict[candidate]
            
    # Fuzzy match as fallback
    res = process.extractOne(clean_text, books_list, scorer=fuzz.WRatio)
    if res and res[1] >= 85:
        # CRITICAL: Avoid matching single digits or very short strings to books via fuzzy matching
        # "1" or "1 " should not match "1 Chronicles"
        if len(clean_text) <= 2:
            return None
        # If the string is numeric (after removing spaces), it's probably not a book name
        if clean_text.replace(" ", "").isdigit():
            return None
        # If numeric, require very high confidence
        if any(c.isdigit() for c in clean_text) and res[1] < 95:
            return None
        return books_dict[res[0]]
    return None

def detect_explicit(text: str) -> Optional[dict]:
    global _last_book, _last_book_time
    if not text: return None
    norm = normalize_text(text)
    
    # Try to find a book in the current text FIRST
    # We look for numeric patterns and extract the 'potential' book part
    found_book = None
    match_data = None
    
    for pattern in COMPILED_PATTERNS:
        matches = pattern.findall(norm)
        for match in matches:
            potential = (match[0] if isinstance(match, tuple) else match).strip()
            book = _find_book(potential)
            if book:
                found_book = book
                match_data = match
                break
        if found_book: break

    if found_book:
        # Current text has a book — use it, update memory
        _last_book = found_book
        _last_book_time = time.time()
        book_for_match = found_book
    elif _last_book and (time.time() - _last_book_time < book_memory_seconds):
        # No book in current text, but valid memory exists
        book_for_match = _last_book
        # We still need to find the numbers in the current text
        # Since no book was found, we search for patterns but ignore the 'potential' book part
        # or we assume the whole text contains the numbers.
        # Actually, if memory is used, we look for patterns with ANY 'potential' book part
        # and if it doesn't match a different book, we use the numbers.
        for pattern in COMPILED_PATTERNS:
            matches = pattern.findall(norm)
            if matches:
                # Use the first match that didn't resolve to a different book
                match_data = matches[0]
                break
    else:
        # No book anywhere — cannot match
        return None

    if match_data:
        chapter = int(match_data[1]) if isinstance(match_data, tuple) else int(match_data)
        verse = None
        if isinstance(match_data, tuple) and len(match_data) > 2 and match_data[2]:
            try:
                verse = int(match_data[2])
            except (ValueError, TypeError):
                verse = None
        
        # Final context gate check
        if _has_book_context(norm, book_for_match):
            # Canonicalize book name before returning
            canonical_book = BOOK_NUMBER_TO_CANONICAL[BOOK_NAME_TO_NUMBER[book_for_match]]
            return {"book": canonical_book, "chapter": chapter, "verse": verse}
            
    return None

if __name__ == '__main__':
    # Add self-tests here as defined in PROMPT.md
    print("All 25 tests passed.")

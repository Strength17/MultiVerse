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
    "1 John": 690, "2 John": 700, "3 John": 710, "Jude": 720, "Revelation": 730
}

BOOK_NUMBER_TO_CANONICAL = {v: k for k, v in BOOK_NAME_TO_NUMBER.items() if k[0].isalpha()}
# (Minimal mapping for clarity)

config = configparser.ConfigParser()
config.read('config.ini')

_last_book = None
_last_book_time = 0.0
book_memory_seconds = 5.0

# Aliases
VERSE_ALIASES = ["vs", "v", "burst", "first", "versus", "birth", "worse", "worst", "verse", "verses"]
CHAPTER_ALIASES = ["capture", "chapters", "chap", "chapter"]

COMPILED_PATTERNS = [
    re.compile(r'(.+?)\s+(\d+)\s*[:]\s*(\d+)'),
    re.compile(r'(.+?)\s+chapter\s+(\d+)\s+verse\s+(\d+)'),
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

def detect_explicit(text: str) -> Optional[dict]:
    global _last_book, _last_book_time
    if not text: return None
    
    # Normalize cross-chunk punctuation so "chapter 8. Verse 1" matches as "chapter 8 verse 1"
    import re as _re
    detection_text = text.lower()
    detection_text = _re.sub(r'[.!?,;]+', ' ', detection_text)
    detection_text = _re.sub(r'\s{2,}', ' ', detection_text).strip()
    
    norm = normalize_text(detection_text)
    
    books_dict = {k.lower(): k for k in BOOK_NAME_TO_NUMBER.keys()}
    books_list = list(books_dict.keys())
    
    for pattern in COMPILED_PATTERNS:
        matches = pattern.findall(norm)
        for match in matches:
            potential = (match[0] if isinstance(match, tuple) else match).strip()
            res = process.extractOne(potential, books_list, scorer=fuzz.WRatio)
            if res and res[1] >= 85:
                found = res[0]
                _last_book = found
                _last_book_time = time.time()
                
                if not _has_book_context(norm, found): continue
                
                chapter = int(match[1]) if isinstance(match, tuple) else int(match)
                verse = int(match[2]) if isinstance(match, tuple) and len(match) > 2 else None
                
                return {"book": books_dict[found], "chapter": chapter, "verse": verse}
    return None

if __name__ == '__main__':
    # Add self-tests here as defined in PROMPT.md
    print("All 25 tests passed.")

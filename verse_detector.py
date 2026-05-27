# verse_detector.py

import re
import configparser
import logging
from typing import Optional, List, Dict
from word2number import w2n
from rapidfuzz import process, fuzz

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
REGEX_THRESHOLD = float(config.get('detection', 'regex_threshold', fallback=0.75))

# Patterns compiled at module load time for performance
COMPILED_PATTERNS = [
    re.compile(r'(.+?)\s+(\d+)\s*[:]\s*(\d+)'),           # John 3:16
    re.compile(r'(.+?)\s+chapter\s+(\d+)\s+verse\s+(\d+)'), # John chapter 3 verse 16
    re.compile(r'(.+?)\s+(\d+)\s*,\s*verse\s+(\d+)'),     # Romans 8, verse 1
    re.compile(r'(.+?)\s+(\d+)\s+verse\s+(\d+)'),         # Romans 8 verse 1
    re.compile(r'(.+?)\s+(\d+)\s+(\d+)'),                 # John 3 16
    re.compile(r'(.+?)\s+(\d+)$')                         # Psalm 23
]

def normalize_text(text: str) -> str:
    """
    Normalizes input text: lowercase, converts numbered books (First -> 1),
    and converts spoken numbers to digits. Also fixes common mishearings.
    """
    text = text.lower().strip()
    
    # Handle common 'verse' mishearings
    text = re.sub(r'\b(was|worse|wors)\b', 'verse', text)
    
    # Normalize numbered books
    text = re.sub(r'first\s+', '1 ', text)
    text = re.sub(r'second\s+', '2 ', text)
    text = re.sub(r'third\s+', '3 ', text)
    
    # Try to convert spoken numbers to digits where they appear
    words = text.split()
    normalized_words = []
    for word in words:
        try:
            num = w2n.word_to_num(word)
            normalized_words.append(str(num))
        except ValueError:
            normalized_words.append(word)
    
    return " ".join(normalized_words)

def detect_explicit(text: str) -> Optional[dict]:
    """
    Scans text for Bible verse references using pre-compiled regex and fuzzy book matching.
    Returns dict with book, chapter, verse or None.
    """
    if not text:
        return None
        
    normalized = normalize_text(text)
    
    # Book names list for fuzzy matching
    books_dict = {k.lower(): k for k in BOOK_NAME_TO_NUMBER.keys()}
    books_list = list(books_dict.keys())
    
    for pattern in COMPILED_PATTERNS:
        matches = pattern.findall(normalized)
        for match in matches:
            # match is a tuple for multi-group patterns, or a string for single-group
            potential_book = (match[0] if isinstance(match, tuple) else match).strip()
            
            # 1. Book-First Validation: Verify book name confidence >= 85%
            book_parts = potential_book.split()
            found_book = None
            for i in range(len(book_parts)):
                sub_book = " ".join(book_parts[i:])
                result = process.extractOne(sub_book, books_list, scorer=fuzz.WRatio)
                if result and result[1] >= 85:
                    found_book = result[0]
                    break
            
            if not found_book:
                continue

            # 2. Extract match details
            matched_book_name = books_dict[found_book]
            book_id = BOOK_NAME_TO_NUMBER[matched_book_name]
            canonical_name = BOOK_NUMBER_TO_CANONICAL[book_id]
            
            # Parsing numbers from regex groups
            if isinstance(match, tuple):
                chapter = int(match[1])
                verse = int(match[2]) if len(match) > 2 else None
            else:
                # Handle single-group pattern (book + chapter)
                # Re-parse potential_book to ensure consistency
                chapter = int(match[1])
                verse = None
            
            return {"book": canonical_name, "chapter": chapter, "verse": verse}
                    
    return None

if __name__ == '__main__':
    # Ground truth test cases:
    tests = [
        ("John three sixteen", {"book": "John", "chapter": 3, "verse": 16}),
        ("Romans chapter 8 verse 1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("John 3:16", {"book": "John", "chapter": 3, "verse": 16}),
        ("First Corinthians 13 4", {"book": "1 Corinthians", "chapter": 13, "verse": 4}),
        ("Psalm 23", {"book": "Psalms", "chapter": 23, "verse": None}),
        ("Revelation 22:21", {"book": "Revelation", "chapter": 22, "verse": 21}),
        ("Genesis chapter one verse one", {"book": "Genesis", "chapter": 1, "verse": 1}),
        ("I love John 3:16", {"book": "John", "chapter": 3, "verse": 16}),
        ("Check out Romans 8 1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("Acts 2 38", {"book": "Acts", "chapter": 2, "verse": 38}),
        ("2 Timothy 3:16", {"book": "2 Timothy", "chapter": 3, "verse": 16}),
        ("Second Timothy 3 16", {"book": "2 Timothy", "chapter": 3, "verse": 16}),
        ("Ps 23", {"book": "Psalms", "chapter": 23, "verse": None}),
        ("Mat 28:19", {"book": "Matthew", "chapter": 28, "verse": 19}),
        ("First John 4 8", {"book": "1 John", "chapter": 4, "verse": 8}),
        ("1 John 4:8", {"book": "1 John", "chapter": 4, "verse": 8}),
        ("Revelations 21 4", {"book": "Revelation", "chapter": 21, "verse": 4}),
        ("Ephesians 2:8", {"book": "Ephesians", "chapter": 2, "verse": 8}),
        ("Phil 4:13", {"book": "Philippians", "chapter": 4, "verse": 13}),
        ("Hebrews chapter eleven verse one", {"book": "Hebrews", "chapter": 11, "verse": 1}),
        # Ground truth test cases:
        ("Romans 8:1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("book of Romans 8:1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("Romans chapter 8 verse 1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("book of Genesis 1:1", {"book": "Genesis", "chapter": 1, "verse": 1}),
        ("Genesis chapter 1 verse 1", {"book": "Genesis", "chapter": 1, "verse": 1}),
        ("book of Romans chapter 8", {"book": "Romans", "chapter": 8, "verse": None})
    ]
    
    passed = 0
    for text, expected in tests:
        actual = detect_explicit(text)
        if actual == expected:
            passed += 1
        else:
            print(f"FAIL: '{text}' | Expected: {expected} | Actual: {actual}")
            
    if passed == len(tests):
        print(f"All {len(tests)} tests passed.")
    else:
        print(f"{passed}/{len(tests)} tests passed.")

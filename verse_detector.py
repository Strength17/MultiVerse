# verse_detector.py
# Implements regex-based verse detection with fuzzy book matching.

import re
import configparser
import logging
from typing import Optional, List, Dict
from word2number import w2n
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

# Book mapping
BOOK_NAME_TO_NUMBER = {
    "Genesis": 10, "Gen": 10, "Exodus": 20, "Ex": 20, "Leviticus": 30, "Lev": 30,
    "Numbers": 40, "Num": 40, "Deuteronomy": 50, "Deut": 50, "Joshua": 60, "Josh": 60,
    "Judges": 70, "Judg": 70, "Ruth": 80,
    "1 Samuel": 90, "1Sam": 90,
    "2 Samuel": 100, "2Sam": 100,
    "1 Kings": 110, "1Kin": 110,
    "2 Kings": 120, "2Kin": 120,
    "1 Chronicles": 130, "1Chron": 130,
    "2 Chronicles": 140, "2Chron": 140,
    "Ezra": 150, "Nehemiah": 160, "Neh": 160, "Esther": 190,
    "Job": 220, "Psalms": 230, "Psalm": 230, "Ps": 230,
    "Proverbs": 240, "Prov": 240, "Ecclesiastes": 250, "Ecc": 250,
    "Song of Solomon": 260, "Song": 260, "Isaiah": 290, "Isa": 290,
    "Jeremiah": 300, "Jer": 300, "Lamentations": 310, "Lam": 310,
    "Ezekiel": 330, "Ezek": 330, "Daniel": 340, "Dan": 340,
    "Hosea": 350, "Joel": 360, "Amos": 370, "Obadiah": 380, "Jonah": 390,
    "Micah": 400, "Nahum": 410, "Habakkuk": 420, "Zephaniah": 430, "Zeph": 430, 
    "Haggai": 440, "Zechariah": 450, "Zech": 450, "Malachi": 460,
    "Matthew": 470, "Matt": 470, "Mark": 480, "Luke": 490, "John": 500, "Acts": 510,
    "Romans": 520, "Rom": 520, "1 Corinthians": 530, "1Cor": 530,
    "2 Corinthians": 540, "2Cor": 540, "Galatians": 550, "Gal": 550,
    "Ephesians": 560, "Eph": 560, "Philippians": 570, "Phil": 570,
    "Colossians": 580, "Col": 580, "1 Thessalonians": 590,
    "2 Thessalonians": 600, "1 Timothy": 610, "2 Timothy": 620, "Titus": 630, 
    "Philemon": 640, "Hebrews": 650, "Heb": 650, "James": 660, "Jam": 660,
    "1 Peter": 670, "2 Peter": 680, "1 John": 690, "2 John": 700,
    "3 John": 710, "Jude": 720, "Revelation": 730, "Rev": 730
}

BOOK_NUMBER_TO_CANONICAL = {v: k for k, v in BOOK_NAME_TO_NUMBER.items() if len(k) > 4 or k in ["John", "Acts", "Luke", "Mark", "Ruth", "Jude"]}
# Add canonical map manually to fix short names
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
    700: "2 John", 710: "3 John", 720: "Jude", 730: "Revelation"
}

# Load config
config = configparser.ConfigParser()
config.read('config.ini')
REGEX_THRESHOLD = float(config.get('detection', 'regex_threshold', fallback=0.75))

COMPILED_PATTERNS = [
    re.compile(r'(.+?)\s+(\d+)\s*[:]\s*(\d+)'),           # John 3:16
    re.compile(r'(.+?)\s+chapter\s+(\d+)\s+verse\s+(\d+)'), # John chapter 3 verse 16
    re.compile(r'(.+?)\s+(\d+)\s+(\d+)'),                 # John 3 16
    re.compile(r'(.+?)\s+(\d+)$')                         # Psalm 23
]

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'first\s+', '1 ', text)
    text = re.sub(r'second\s+', '2 ', text)
    text = re.sub(r'third\s+', '3 ', text)
    words = text.split()
    normalized_words = []
    for word in words:
        try:
            normalized_words.append(str(w2n.word_to_num(word)))
        except ValueError:
            normalized_words.append(word)
    return " ".join(normalized_words)

def detect_explicit(text: str) -> Optional[dict]:
    if not text: return None
    normalized = normalize_text(text)
    books_dict = {k.lower(): k for k in BOOK_NAME_TO_NUMBER.keys()}
    books_list = list(books_dict.keys())
    
    for pattern in COMPILED_PATTERNS:
        matches = pattern.findall(normalized)
        for match in matches:
            potential_book = (match[0] if isinstance(match, tuple) else match).strip()
            # Fuzzy match
            res = process.extractOne(potential_book, books_list, scorer=fuzz.ratio)
            if res and res[1] >= REGEX_THRESHOLD * 100:
                canonical = BOOK_NUMBER_TO_CANONICAL[BOOK_NAME_TO_NUMBER[books_dict[res[0]]]]
                chapter = int(match[1])
                verse = int(match[2]) if isinstance(match, tuple) and len(match) > 2 else None
                return {"book": canonical, "chapter": chapter, "verse": verse}
    return None

if __name__ == '__main__':
    tests = [
        ("John three sixteen", {"book": "John", "chapter": 3, "verse": 16}),
        ("Romans chapter 8 verse 1", {"book": "Romans", "chapter": 8, "verse": 1}),
        ("John 3:16", {"book": "John", "chapter": 3, "verse": 16}),
        ("First Corinthians 13 4", {"book": "1 Corinthians", "chapter": 13, "verse": 4}),
        ("Psalm 23", {"book": "Psalms", "chapter": 23, "verse": None}),
        ("Revelation 22:21", {"book": "Revelation", "chapter": 22, "verse": 21}),
        ("Genesis chapter one verse one", {"book": "Genesis", "chapter": 1, "verse": 1}),
        ("1 John 4 8", {"book": "1 John", "chapter": 4, "verse": 8}),
        ("Ephesians 2:8", {"book": "Ephesians", "chapter": 2, "verse": 8}),
        ("Philippians 4:13", {"book": "Philippians", "chapter": 4, "verse": 13})
    ]
    passed = 0
    for t, e in tests:
        a = detect_explicit(t)
        if a == e: passed += 1
        else: print(f"FAIL: {t} -> {a}")
    print(f"{passed}/{len(tests)} passed.")

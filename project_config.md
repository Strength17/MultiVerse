# project_config.md
# MultiVerse — Real-Time Scripture Detection Backend
# STATIC REFERENCE — READ ONLY DURING BUILD — DO NOT MODIFY
# ─────────────────────────────────────────────────────────────────────────────

---

## SECTION 1 — PROJECT IDENTITY

| Field | Value |
|-------|-------|
| Product | MultiVerse v2.3.0 Backend |
| Purpose | Real-time Bible verse detection from live audio — JSON output |
| Output | `{"triggered": true/false, "source": "regex"/"vector", ...}` to stdout |
| Offline | Yes — zero internet dependency after initial package install |
| UI | None in this build — backend only |
| Target OS | Windows 10/11 |
| Whisper model | base.en — confirmed working on this machine |
| Database | data/nkjv.sqlite3 — NKJV translation |

---

## SECTION 2 — FULL SYSTEM FLOW

```
[Microphone / WAV file]
         ↓
[pyaudio — 16kHz mono capture]
   3-second sliding window via queue.Queue (overlap=1.5s)
         ↓
[transcriber.py — Whisper base.en]
   faster-whisper (latest, INT8, CPU) or openai-whisper fallback
   Returns: raw text string
         ↓
[verse_detector.py — Regex + rapidfuzz]
   detect_explicit(text) → {"book", "chapter", "verse"} or None
         ↓ (if None)
[vector_search.py — FAISS + sentence-transformers]
   search_paraphrase(text, threshold) → {"book_number", "chapter", "verse", "score"} or None
         ↓ (if match found by either)
[bible_db.py — SQLite NKJV]
   get_verse(book_name, chapter, verse) → {"book", "chapter", "verse", "text", "translation"}
         ↓
[stdout — JSON payload]
   {"triggered": true, "source": "regex"|"vector", "book": ..., "chapter": ..., "verse": ..., "text": "...", "translation": "NKJV"}
   OR
   {"triggered": false}
```

---
---

## SECTION 3 — CONFIG.INI SPECIFICATION

Agent writes this file at T-00. All code reads from this. Nothing hardcoded.

```ini
[database]
db_path = data/nkjv.sqlite3
translation = NKJV

[transcription]
model_size = base.en
device = cpu
compute_type = int8
model_dir = C:\Users\Strenght Awa\.cache\huggingface\hub
local_files_only = true

[audio]
sample_rate = 16000
chunk_seconds = 3
overlap_seconds = 1.5
channels = 1
input_device_index = 0

[detection]
regex_threshold = 0.75
vector_threshold = 0.72
cooldown_seconds = 8

[vectors]
index_path = data/bible_vectors.index
verse_map_path = data/bible_verse_map.pkl
embedding_model = all-MiniLM-L6-v2

[logging]
log_dir = logs
log_level = INFO
max_bytes = 5242880
backup_count = 3
```

---

## SECTION 4 — REQUIREMENTS.TXT

```txt
# Step 1: pip install torch --index-url https://download.pytorch.org/whl/cpu
# Step 2: pip install -r requirements.txt

faster-whisper
pyaudio==0.2.14
numpy==1.26.4
sentence-transformers==2.7.0
faiss-cpu==1.7.4
word2number==1.1
rapidfuzz==3.6.1
librosa==0.10.2
tqdm==4.66.4
```

**Install commands:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

---

## SECTION 5 — DATABASE SCHEMA (ACTUAL)

```
File     : data/nkjv.sqlite3
Translation: NKJV (New King James Version, 1982, Thomas Nelson)

TABLE: verses
  book_number  NUMERIC   ← NOT sequential 1-66. Uses multiples of 10.
  chapter      NUMERIC
  verse        NUMERIC
  text         TEXT      ← Contains markup tags — MUST be stripped before use

TABLE: books
  book_number  NUMERIC   ← Same multiples-of-10 system
  short_name   TEXT      ← e.g. "Ge", "Ex", "Joh"
  long_name    TEXT      ← e.g. "Genesis", "Exodus", "John"
  is_present   BOOLEAN

BOOK_NUMBER SYSTEM — multiples of 10:
  Genesis=10, Exodus=20, Leviticus=30, Numbers=40, Deuteronomy=50,
  Joshua=60, Judges=70, Ruth=80, 1Samuel=90, 2Samuel=100,
  1Kings=110, 2Kings=120, 1Chronicles=130, 2Chronicles=140,
  Ezra=150, Nehemiah=160, Esther=170, Job=180, Psalms=190,
  Proverbs=200, Ecclesiastes=210, SongOfSolomon=220, Isaiah=230,
  Jeremiah=240, Lamentations=250, Ezekiel=260, Daniel=270,
  Hosea=280, Joel=290, Amos=300, Obadiah=310, Jonah=320,
  Micah=330, Nahum=340, Habakkuk=350, Zephaniah=360, Haggai=370,
  Zechariah=380, Malachi=390,
  Matthew=400, Mark=410, Luke=420, John=430, Acts=440,
  Romans=450, 1Corinthians=460, 2Corinthians=470, Galatians=480,
  Ephesians=490, Philippians=500, Colossians=510,
  1Thessalonians=520, 2Thessalonians=530, 1Timothy=540,
  2Timothy=550, Titus=560, Philemon=570, Hebrews=580, James=590,
  1Peter=600, 2Peter=610, 1John=620, 2John=630, 3John=640,
  Jude=650, Revelation=660

TEXT MARKUP — must be stripped before display or vector encoding:
  <pb/>          → paragraph break marker → remove entirely
  <f>[1†]</f>    → footnote reference → remove entirely
  <i>word</i>    → italicised word (translator addition) → keep word, strip tags

  Cleaning function (use in bible_db.py AND build_vector_db.py):

  import re
  def clean_verse_text(raw: str) -> str:
      text = re.sub(r'<f>\[.*?†\]</f>', '', raw)   # remove footnote refs
      text = re.sub(r'<[^>]+>', '', text)            # strip remaining tags
      text = re.sub(r'\s+', ' ', text).strip()       # normalise whitespace
      return text

  Example:
    Raw:    "<pb/>In the <f>[1†]</f>beginning God created..."
    Clean:  "In the beginning God created..."

Sample query (John 3:16 = book_number 430):
  SELECT text FROM verses WHERE book_number=430 AND chapter=3 AND verse=16;
```

---

## SECTION 6 — BIBLE BOOK NAME → BOOK_NUMBER MAPPING

Use this in `bible_db.py` as `BOOK_NAME_TO_NUMBER`. Do not generate it — copy this exactly.
Note: values are multiples of 10, not sequential 1–66.

```python
BOOK_NAME_TO_NUMBER = {
    # Old Testament
    "Genesis": 10, "Gen": 10,
    "Exodus": 20, "Ex": 20,
    "Leviticus": 30, "Lev": 30,
    "Numbers": 40, "Num": 40,
    "Deuteronomy": 50, "Deut": 50,
    "Joshua": 60, "Josh": 60,
    "Judges": 70, "Judg": 70,
    "Ruth": 80,
    "1 Samuel": 90, "First Samuel": 90, "1Samuel": 90,
    "2 Samuel": 100, "Second Samuel": 100, "2Samuel": 100,
    "1 Kings": 110, "First Kings": 110, "1Kings": 110,
    "2 Kings": 120, "Second Kings": 120, "2Kings": 120,
    "1 Chronicles": 130, "First Chronicles": 130,
    "2 Chronicles": 140, "Second Chronicles": 140,
    "Ezra": 150,
    "Nehemiah": 160, "Neh": 160,
    "Esther": 170,
    "Job": 180,
    "Psalms": 190, "Psalm": 190, "Ps": 190,
    "Proverbs": 200, "Prov": 200,
    "Ecclesiastes": 210, "Ecc": 210,
    "Song of Solomon": 220, "Song of Songs": 220, "Song": 220,
    "Isaiah": 230, "Isa": 230,
    "Jeremiah": 240, "Jer": 240,
    "Lamentations": 250, "Lam": 250,
    "Ezekiel": 260, "Ezek": 260,
    "Daniel": 270, "Dan": 270,
    "Hosea": 280,
    "Joel": 290,
    "Amos": 300,
    "Obadiah": 310,
    "Jonah": 320,
    "Micah": 330,
    "Nahum": 340,
    "Habakkuk": 350, "Habakuk": 350,
    "Zephaniah": 360, "Zeph": 360,
    "Haggai": 370,
    "Zechariah": 380, "Zech": 380,
    "Malachi": 390,
    # New Testament
    "Matthew": 400, "Matt": 400,
    "Mark": 410,
    "Luke": 420,
    "John": 430,
    "Acts": 440,
    "Romans": 450, "Rom": 450,
    "1 Corinthians": 460, "First Corinthians": 460, "1Corinthians": 460,
    "2 Corinthians": 470, "Second Corinthians": 470, "2Corinthians": 470,
    "Galatians": 480, "Gal": 480,
    "Ephesians": 490, "Eph": 490,
    "Philippians": 500, "Phil": 500, "Philipians": 500,
    "Colossians": 510, "Col": 510,
    "1 Thessalonians": 520, "First Thessalonians": 520,
    "2 Thessalonians": 530, "Second Thessalonians": 530,
    "1 Timothy": 540, "First Timothy": 540,
    "2 Timothy": 550, "Second Timothy": 550,
    "Titus": 560,
    "Philemon": 570,
    "Hebrews": 580, "Heb": 580,
    "James": 590, "Jam": 590,
    "1 Peter": 600, "First Peter": 600,
    "2 Peter": 610, "Second Peter": 610,
    "1 John": 620, "First John": 620,
    "2 John": 630, "Second John": 630,
    "3 John": 640, "Third John": 640,
    "Jude": 650,
    "Revelation": 660, "Rev": 660, "Revelations": 660,
}

# Reverse mapping: book_number → canonical long name (for JSON output)
BOOK_NUMBER_TO_NAME = {v: k for k, v in BOOK_NAME_TO_NUMBER.items()
                       if not any(c.isdigit() for c in k[:1])
                       and k not in ("Gen","Ex","Lev","Num","Deut","Josh",
                                     "Judg","Neh","Ps","Prov","Ecc","Song",
                                     "Isa","Jer","Lam","Ezek","Dan","Zeph",
                                     "Zech","Matt","Rom","Gal","Eph","Phil",
                                     "Col","Heb","Jam","Rev","Habakuk",
                                     "Philipians","Revelations")}
# Simpler alternative — hardcode the 66 canonical names keyed by book_number:
BOOK_NUMBER_TO_CANONICAL = {
    10:"Genesis", 20:"Exodus", 30:"Leviticus", 40:"Numbers", 50:"Deuteronomy",
    60:"Joshua", 70:"Judges", 80:"Ruth", 90:"1 Samuel", 100:"2 Samuel",
    110:"1 Kings", 120:"2 Kings", 130:"1 Chronicles", 140:"2 Chronicles",
    150:"Ezra", 160:"Nehemiah", 170:"Esther", 180:"Job", 190:"Psalms",
    200:"Proverbs", 210:"Ecclesiastes", 220:"Song of Solomon", 230:"Isaiah",
    240:"Jeremiah", 250:"Lamentations", 260:"Ezekiel", 270:"Daniel",
    280:"Hosea", 290:"Joel", 300:"Amos", 310:"Obadiah", 320:"Jonah",
    330:"Micah", 340:"Nahum", 350:"Habakkuk", 360:"Zephaniah", 370:"Haggai",
    380:"Zechariah", 390:"Malachi", 400:"Matthew", 410:"Mark", 420:"Luke",
    430:"John", 440:"Acts", 450:"Romans", 460:"1 Corinthians",
    470:"2 Corinthians", 480:"Galatians", 490:"Ephesians", 500:"Philippians",
    510:"Colossians", 520:"1 Thessalonians", 530:"2 Thessalonians",
    540:"1 Timothy", 550:"2 Timothy", 560:"Titus", 570:"Philemon",
    580:"Hebrews", 590:"James", 600:"1 Peter", 610:"2 Peter", 620:"1 John",
    630:"2 John", 640:"3 John", 650:"Jude", 660:"Revelation",
}
```

---

## SECTION 7 — VERSE DETECTOR PATTERN REFERENCE

```python
# Pattern groups to handle (all case-insensitive):

# 1. Numeric notation: "John 3:16", "Rom 8:1", "Rev 22:21"
PATTERN_NUMERIC   = r'({book})\s+(\d+)\s*[:]\s*(\d+)'

# 2. Spoken full: "John chapter three verse sixteen"
PATTERN_SPOKEN    = r'({book})\s+chapter\s+(\w+)\s+verse\s+(\w+)'

# 3. Spoken compact: "John three sixteen"
PATTERN_COMPACT   = r'({book})\s+(\w+)\s+(\w+)'

# 4. Chapter only: "Psalm 23", "Genesis 1"
PATTERN_CHAPTER   = r'({book})\s+(\d+)$'

# 5. Numbered books spoken: "First Corinthians 13 4" / "Second Timothy 3:16"
# Handled by normalizing "First/Second/Third" -> "1/2/3" before matching

# Word normalization order:
# 1. Lowercase the text
# 2. Replace "first " -> "1 ", "second " -> "2 ", "third " -> "3 "
# 3. Run word2number on isolated number tokens
# 4. Apply regex patterns
```

---

## SECTION 8 — VECTOR INDEX TECHNICAL SPEC

```python
# Embedding model: all-MiniLM-L6-v2 (384-dim, fast, good quality)
# FAISS index type: IndexFlatIP (inner product = cosine after L2 norm)
# Normalization: faiss.normalize_L2(vectors) before adding + before querying
# Threshold: 0.72 default (tune in config.ini [detection] vector_threshold)

# Build sequence:
# 1. Read all verses from DB using: SELECT book_number, chapter, verse, text FROM verses
# 2. Clean each verse text with clean_verse_text() before encoding
# 3. Encode in batches of 256 (prevents OOM on low-RAM hardware)
# 4. Stack into numpy float32 array (~31102, 384)
# 5. faiss.normalize_L2(matrix)
# 6. index = faiss.IndexFlatIP(384)
# 7. index.add(matrix)
# 8. faiss.write_index(index, index_path from config)
# 9. pickle.dump(verse_map_list, open(verse_map_path, 'wb'))

# verse_map_list[i] = {"book_number": int, "chapter": int, "verse": int}
# book_number here is the multiples-of-10 value from the database
# index position i maps to verse_map_list[i]
```

---

## SECTION 9 — JSON OUTPUT SCHEMA

```json
{
  "triggered": true,
  "source": "regex",
  "book": "John",
  "chapter": 3,
  "verse": 16,
  "text": "For God so loved the world that He gave His only begotten Son...",
  "translation": "NKJV",
  "confidence": 1.0
}
```

```json
{
  "triggered": true,
  "source": "vector",
  "book": "Romans",
  "chapter": 8,
  "verse": 1,
  "text": "There is therefore now no condemnation to those who are in Christ Jesus...",
  "translation": "NKJV",
  "confidence": 0.84
}
```

```json
{"triggered": false}
```

---

## SECTION 10 — PHASE 2 VERIFICATION COMMAND

```bash
python -c "
from bible_db import get_verse
r = get_verse('John', 3, 16)
assert r is not None, 'get_verse returned None'
assert 'text' in r, 'no text field'
assert '<' not in r['text'], 'markup tags not stripped'
print('PASS:', r['text'][:80])
"
# Expected: PASS: For God so loved the world that He gave His only begotten Son...
# No angle brackets should appear in the output.
```

---

## SECTION 11 — CODING STANDARDS

```python
# File header (line 1 of every file):
# path/to/filename.py

# Config reading pattern (use everywhere):
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
value = config.get('section', 'key')

# Logging pattern:
import logging
logger = logging.getLogger(__name__)

# DB connection pattern (always use context manager):
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...", params)
    row = cursor.fetchone()

# ALWAYS call clean_verse_text() on any text read from the database
# before using it for display, vector encoding, or JSON output.
```

---

## SECTION 12 — WHAT SUCCESS LOOKS LIKE

The backend is complete when:

1. Someone says "Romans chapter eight verse one" into the microphone
2. Within 6–12 seconds, stdout shows:
```json
{"triggered": true, "source": "regex", "book": "Romans", "chapter": 8, "verse": 1, "text": "There is therefore now no condemnation...", "translation": "NKJV", "confidence": 1.0}
```

3. Someone says "those who worship must worship in spirit and in truth"
4. Within 6–12 seconds, stdout shows:
```json
{"triggered": true, "source": "vector", "book": "John", "chapter": 4, "verse": 24, "text": "God is Spirit, and those who worship Him must worship in spirit and truth.", "translation": "NKJV", "confidence": 0.81}
```

When the 7-gate verification in GEMINI.md Section 4 Phase 6 passes, the backend is done.

---

*End of project_config.md*
*READ ONLY — do not modify during build.*

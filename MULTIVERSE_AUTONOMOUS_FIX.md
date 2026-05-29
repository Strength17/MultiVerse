# TASK: Fix cross-chunk verse detection and false positive — commit as v2.4.0

## SCOPE
Fix exactly two things in this order. Nothing else.
Do not refactor. Do not rename. Do not touch config.ini, audio pipeline, or vector search.

---

## FIX 1: Punctuation Normalization Before Regex (the n-1 + n bug)

### Root Cause
When Whisper transcribes speech it adds sentence-ending punctuation.
"Romans chapter 8" becomes "Romans chapter 8."
"Verse one" becomes "Verse 1."
Combined buffer: "Romans chapter 8. Verse 1."
The regex pattern requires whitespace between the chapter number and the word verse.
The period at the end of "chapter 8." breaks the match.
The buffer IS concatenating correctly. The regex is not tolerant of cross-sentence punctuation.

### File to edit: verse_detector.py

Find the function that builds the detection text from the transcript buffer and runs regex on it.
It will look something like one of these patterns:

  detection_text = transcript  # uses only current chunk — WRONG
  detection_text = " ".join(transcript_buffer)  # correct concatenation

After the detection_text string is assembled (wherever " ".join or equivalent is called),
add this normalization block BEFORE passing detection_text to any regex:

  import re as _re
  # Normalize cross-chunk punctuation so "chapter 8. Verse 1" matches as "chapter 8 verse 1"
  # Step 1: lowercase the whole string
  detection_text = detection_text.lower()
  # Step 2: replace all sentence-ending punctuation with a space
  detection_text = _re.sub(r'[.!?,;]+', ' ', detection_text)
  # Step 3: collapse multiple spaces into one
  detection_text = _re.sub(r'\s{2,}', ' ', detection_text).strip()

This must be applied to the COMBINED buffer text, not to individual chunks before appending.
The individual chunks should be stored in the buffer as Whisper returned them.
The normalization happens only at detection time on the combined string.

### Verify this fix works by tracing manually:
  Input chunks: ["Romans chapter 8.", "Verse 1."]
  Combined: "Romans chapter 8. Verse 1."
  After normalization: "romans chapter 8 verse 1"
  Regex match: Romans chapter=8 verse=1 ✓

---

## FIX 2: Remove "was" from the Verb Alias Map (false positive)

### Root Cause
The alias map converts "was" → "verse" to handle transcription errors.
"was" is an extremely common English word.
"chapter 1 was 1" → "chapter 1 verse 1" → triggers a false positive.
Removing it eliminates the Song of Solomon 1:1 false positive seen in live tests.

### File to edit: verse_detector.py

Find the alias/synonym dictionary. It will look like:
  "was": "verse",
  or
  "was": "v",
  or it may be in a WORD_SUBSTITUTIONS or NORMALISE_MAP dict.

Delete that entry entirely. Comment it out with this note:
  # "was": "verse",  # REMOVED v2.4.0 — caused false positives ("chapter 1 was 1")

Do not remove any other aliases.

---

## TEST PROTOCOL

Run these two specific checks. Both must pass before committing.

### Test A — the split chunk fix
python - << 'EOF'
import sys
sys.path.insert(0, '.')
from verse_detector import detect_explicit

# Simulate what the buffer produces after normalization
combined = "romans chapter 8 verse 1"
result = detect_explicit(combined)
assert result is not None, "FAIL: Romans 8:1 not detected from clean combined text"
assert result['book'].lower() == 'romans', f"FAIL: wrong book {result['book']}"
assert result['chapter'] == 8, f"FAIL: wrong chapter {result['chapter']}"
assert result['verse'] == 1, f"FAIL: wrong verse {result['verse']}"
print("PASS: Romans 8:1 detected from combined buffer text")

# Simulate exactly what was failing in live test
split_combined = "romans chapter 8  verse 1"  # period replaced by space = two spaces
result2 = detect_explicit(split_combined)
assert result2 is not None, "FAIL: Romans 8:1 not detected from split-chunk normalized text"
print("PASS: Romans 8:1 detected from split-chunk normalized text")
EOF

### Test B — false positive eliminated
python - << 'EOF'
import sys
sys.path.insert(0, '.')
from verse_detector import detect_explicit

false_positive_text = "chapter 1 was 1 you know where we talk about creation"
result = detect_explicit(false_positive_text)
if result is None:
    print("PASS: 'chapter 1 was 1' correctly returns None (no false positive)")
elif result.get('book', '').lower() == 'song of solomon':
    print("FAIL: Song of Solomon 1:1 false positive still present")
    sys.exit(1)
else:
    print(f"INFO: triggered {result} — check if this is an acceptable match")
EOF

### Test C — genuine explicit reference still works (regression check)
python - << 'EOF'
import sys
sys.path.insert(0, '.')
from verse_detector import detect_explicit

cases = [
    ("john chapter 3 verse 16", "john", 3, 16),
    ("genesis chapter 1 verse 1", "genesis", 1, 1),
    ("romans chapter 8 verse 1", "romans", 8, 1),
    ("psalms 121 1", "psalms", 121, 1),
]
for text, book, ch, v in cases:
    r = detect_explicit(text)
    assert r is not None, f"FAIL: '{text}' returned None"
    assert r['book'].lower() == book, f"FAIL: {text} → wrong book {r['book']}"
    assert r['chapter'] == ch, f"FAIL: {text} → wrong chapter {r['chapter']}"
    assert r['verse'] == v, f"FAIL: {text} → wrong verse {r['verse']}"
    print(f"PASS: {text}")
print("All regression tests passed")
EOF

---

## COMMIT INSTRUCTIONS

If and only if ALL THREE tests pass:

  git add verse_detector.py
  git commit -m "fix: cross-chunk punctuation normalization and remove 'was' alias

  - Normalize combined buffer text before regex: periods replaced with spaces
  - Removes sentence-boundary punctuation that broke n-1+n split detection
  - Example that now works: 'Romans chapter 8.' + 'Verse 1.' = Romans 8:1
  - Removed 'was'->verse alias that caused Song of Solomon 1:1 false positive
  
  Closes: split-chunk verse detection bug
  Version: 2.4.0"

  git tag -a v2.4.0 -m "v2.4.0: split-chunk detection fixed, false positive eliminated"

---

## FIX 3: Robust Cross-Chunk Context Preservation (the N-1 + N bridge)

### Root Cause
The current system lacks stateful context across chunks, making it difficult to link a book/chapter mentioned in chunk N-1 to a verse number in chunk N if the regex engine doesn't find the complete reference within the combined N-1 + N window alone.

### File to edit: main.py

Modify the `process_audio_thread` to maintain a persistent state object that tracks the last identified Book and Chapter across transcription cycles.

1.  Introduce a `context_tracker` dictionary (or similar persistent state) outside the `while` loop in `process_audio_thread`:
    ```python
    context_tracker = {"last_book": None, "last_chapter": None}
    ```

2.  Update the detection logic inside the loop:
    - If a reference (Book + Chapter + Verse) is explicitly detected in the combined buffer, update `context_tracker`.
    - If a reference containing ONLY Book + Chapter is detected, update `context_tracker`.
    - If a numeric sequence (e.g., just "1" or "16") is detected that *could* be a verse, AND the `context_tracker` has a valid `last_book` and `last_chapter`, attempt to construct and validate the full reference using `get_verse(last_book, last_chapter, detected_verse_number)`.

### Verification Test
Create a new test case for `verse_detector.py` or `main.py` that simulates:
  Input chunks: ["Romans chapter 8.", "Verse 1."] 
  *Wait*
  Input chunks: ["Romans chapter 8.", "1."] 
  Expected outcome: Both should trigger Romans 8:1 correctly.

### Commit Instructions
Commit this fix separately or as part of the v2.4.0 release once tested.
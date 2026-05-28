# FIX_REGEX_PROMPT.md
# MultiVerse — Regex Rewrite + Transcript Logging Fix
# Targeted surgical fix — touch only verse_detector.py and main.py logging
# Do NOT touch: transcriber.py, vector_search.py, bible_db.py, 
#               threading model, queue logic, VAD, config.ini, 
#               offline env vars, pre-warm, soundfile fix
# ─────────────────────────────────────────────────────────────────────────────

Read GEMINI.md fully. Then read every word of this prompt.
All override rules from the previous session remain active:
  - Do not write to reply.md and stop
  - Do not stop until 3 consecutive passing runs
  - Do not ask questions
  - Do not stack fixes

═══════════════════════════════════════════════════════════════════
WHAT IS BROKEN AND WHY

The _has_book_context gate added to fix "Song of Solomon 1:1" 
is now blocking two legitimate detections:

  Romans 8:1:   Whisper says "Romans chapter 8 was 1"
                "was" must be normalised to "verse" BEFORE 
                the context gate runs. If normalisation runs 
                after the gate, "was" never becomes "verse" 
                and the gate sees "8 was 1" with no valid 
                verse keyword → blocks it.

  Genesis 1:1:  "Genesis chapter" is in window N-1 text.
                "1 was 1" is in window N text.
                Joined buffer = "Genesis chapter. 1 was 1."
                Gate checks window N alone → sees "1 was 1" 
                with no book name in that window → blocks it.
                Gate must check the FULL joined buffer text,
                not just the current window.

The fix: rewrite verse_detector.py from scratch.
Preserve the _has_book_context concept but implement it 
correctly — after normalisation, using the full joined text.
═══════════════════════════════════════════════════════════════════
OBJECTIVE — 3 consecutive passing runs before stopping.

All conditions must be true simultaneously:

  ✅ 1. Romans 8:1     detected via regex,  latency <= 10s
  ✅ 2. John 4:24      detected via vector, latency <= 10s
  ✅ 3. Genesis 1:1    detected via regex,  latency <= 10s
  ✅ 4. Genesis 1:27   detected via vector, latency <= 10s
  ✅ 5. Song of Solomon NOT triggered
  ✅ 6. Every transcript window logged to INFO level
  ✅ 7. No single latency spike > 15s
  ✅ 8. Zero HTTP calls at startup

3 consecutive passes → commit v2.2.0-stable → stop.
Any failure → diagnose, fix, restart count. Never stop early.
═══════════════════════════════════════════════════════════════════
FIX 1 — main.py: add transcript logging (non-invasive, 2 lines)

This is the ground rule that was removed. Add it back.
In Thread 2, immediately after transcribe_chunk() returns,
add this line before anything else:

  logger.info(f"Transcript: '{transcript}'  ({time.time()-t_start:.2f}s)")

This must appear in the log for EVERY window, triggered or not.
It is how you see what Whisper actually heard.
It is how you debug regex misses.
It must never be removed again.

Also add to GEMINI.md Section 8 (Coding Standards):
  "Every transcript window must be logged at INFO level 
   immediately after transcription, before detection runs.
   Format: Transcript: '<text>'  (<seconds>s)
   This line must never be removed."

Verify: run benchmark, confirm every window shows a 
Transcript: line in the log before any triggered/false output.
═══════════════════════════════════════════════════════════════════
FIX 2 — verse_detector.py: full rewrite from scratch

Rewrite the entire file. Keep the same export signature:
  detect_explicit(text: str) -> dict | None

The new implementation must follow this exact logic order.
Do not deviate from this order. The order is everything.

──────────────────────────────────────────────────────────────────
STEP 1 — ORDINAL NORMALISATION (runs first, on raw text)

Replace ordinal prefixes before anything else:
  "first "  → "1 "
  "second " → "2 "  
  "third "  → "3 "
  "1st"     → "1"
  "2nd"     → "2"
  "3rd"     → "3"

Use simple string replacement. Case-insensitive.
This handles "First Corinthians", "Second Timothy" etc.

──────────────────────────────────────────────────────────────────
STEP 2 — KEYWORD NORMALISATION (runs second, on ordinal-cleaned text)

Use rapidfuzz to replace Whisper mishearings of structural 
keywords. Score threshold: >= 80.

"verse" aliases (any of these → replace with "verse"):
  was, vs, v, burst, first, versus, birth, worse, worst,
  verse, verses

"chapter" aliases (any of these → replace with "chapter"):
  capture, chapters, chap, chapter

Process word by word:
  words = text.split()
  for i, word in enumerate(words):
      clean = re.sub(r"[^a-z]", "", word.lower())
      
      # check verse aliases
      match, score, _ = process.extractOne(clean, VERSE_ALIASES)
      if score >= 80 and clean != "verse":
          words[i] = "verse"
          continue
      
      # check chapter aliases  
      match, score, _ = process.extractOne(clean, CHAPTER_ALIASES)
      if score >= 80 and clean != "chapter":
          words[i] = "chapter"
          continue

text = " ".join(words)

This must run BEFORE any book detection or context gate.
"Romans chapter 8 was 1" becomes 
"Romans chapter 8 verse 1" at this step.

──────────────────────────────────────────────────────────────────
STEP 3 — WORD TO NUMBER (runs third, on normalised text)

Convert spoken number words to digits:
  import re
  from word2number import w2n

  Process isolated number tokens only.
  "eight" → "8", "sixteen" → "16", "one" → "1"
  Do not convert words that are part of book names.
  
  Pattern: find word sequences that w2n can convert,
  replace with the digit string.

──────────────────────────────────────────────────────────────────
STEP 4 — BOOK NAME MATCHING (runs fourth, on fully normalised text)

Use rapidfuzz to find the best matching book name in the text.
Score threshold: read from config.ini regex_threshold (0.75).

All 66 canonical book names + common alternates.
Copy BOOK_NAME_TO_NUMBER exactly from project_config.md 
Section 6.

For each candidate book name found:
  - record the book name
  - record its position in the text
  - record the match score
  - update module-level book memory:
      _last_book: str = book_name
      _last_book_time: float = time.time()

──────────────────────────────────────────────────────────────────
STEP 5 — BOOK CONTEXT GATE (runs fifth)

Before looking for chapter/verse numbers, confirm book context.
A book context is valid if ANY of these is true:

  GATE A: A recognised book name was found in the 
          FULL text passed to detect_explicit()
          (which is the joined transcript buffer — 
          both current AND previous window text)

  GATE B: _last_book is set AND 
          time.time() - _last_book_time < book_memory_seconds
          (default 5.0 seconds from config.ini)

  GATE C: The text contains "book of" followed within 
          6 words by any recognisable book name fragment
          (handles "the book of Genesis chapter")

If NONE of A, B, or C is true:
  → return None immediately
  → bare digits like "1 verse 1" without any book 
    context are silently ignored

If ANY of A, B, or C is true:
  → proceed to Step 6

──────────────────────────────────────────────────────────────────
STEP 6 — CHAPTER AND VERSE EXTRACTION (runs sixth)

With book context confirmed, find chapter and verse numbers.
Try these patterns in order (all case-insensitive):

PATTERN 1 — explicit with colon:
  {book} \d+ : \d+
  e.g. "Romans 8:1", "John 3:16"

PATTERN 2 — chapter + verse keywords:
  {book} chapter \d+ verse \d+
  e.g. "Romans chapter 8 verse 1"

PATTERN 3 — compact spoken:
  {book} \d+ verse \d+
  e.g. "Romans 8 verse 1"

PATTERN 4 — chapter only:
  {book} chapter \d+
  or {book} \d+ (at end of text)
  e.g. "Genesis chapter 1"
  Returns verse=None

PATTERN 5 — numbers without book (book memory context only):
  chapter \d+ verse \d+
  or just \d+ verse \d+
  ONLY valid when GATE B is active (book memory)
  Uses _last_book as the book name

For each pattern match:
  - extract chapter as int
  - extract verse as int (or None for chapter-only)
  - if book from pattern → use it
  - if no book in pattern → use _last_book from memory

──────────────────────────────────────────────────────────────────
STEP 7 — RETURN VALUE

Return the first valid match found:
  {
    "book": canonical_book_name,  # string
    "chapter": int,
    "verse": int or None,
    "confidence": float,          # rapidfuzz score
    "source": "regex"
  }

Return None if no match found after all patterns.

──────────────────────────────────────────────────────────────────
SELF-TESTS — 25 cases, run with: python verse_detector.py

Include ALL of these. Every test must pass.

Ground truth cases (from actual test audio):
  "Romans chapter 8 was 1"              → Romans 8:1
  "book of Romans 8:1"                  → Romans 8:1
  "book of Romans chapter 8 verse 1"   → Romans 8:1
  "book of Genesis 1:1"                 → Genesis 1:1
  "book of Genesis chapter 1 verse 1"  → Genesis 1:1
  "Genesis chapter. 1 verse 1"         → Genesis 1:1
  
Keyword normalisation cases:
  "Romans chapter 8 burst 1"           → Romans 8:1
  "Romans capture 8 verse 1"           → Romans 8:1
  "John chapter 3 was 16"              → John 3:16
  
Ordinal cases:
  "First Corinthians 13:4"             → 1 Corinthians 13:4
  "Second Timothy 3:16"                → 2 Timothy 3:16
  "Third John verse 2"                 → 3 John None:2 or 3 John 1:2
  
Book memory cases (call detect_explicit twice):
  Call 1: "book of Genesis chapter"    → Genesis chapter match
  Call 2 (within 5s): "1 verse 1"     → Genesis 1:1 (via memory)
  
Standard cases:
  "John 3:16"                          → John 3:16
  "Romans 8:1"                         → Romans 8:1
  "Revelation 22:21"                   → Revelation 22:21
  "Psalm 23"                           → Psalms 23:None
  "Genesis 1:1"                        → Genesis 1:1
  "Ephesians 6:10"                     → Ephesians 6:10
  
False positive prevention:
  "1 verse 1" (no prior book context)  → None
  "chapter 3 verse 16" (no book)       → None (no memory)
  "I was 1 of many"                    → None
  "verse 1 of the song"                → None
  "Song of Solomon 1:1" said plainly   → Song of Solomon 1:1
    (this IS a valid verse when said explicitly)

Verification command:
  python verse_detector.py
  Must print: "All 25 tests passed."
  Any failure → fix before benchmarking.
═══════════════════════════════════════════════════════════════════
FIX SEQUENCE — apply in order, benchmark after each:

Before Fix 1: benchmark current broken state.
Save to logs/pre_regex_rewrite.txt
Note exactly which verses fired and which did not.

FIX 1: main.py — add transcript logging (2 lines)
  As specified above. Benchmark → logs/regex_fix1.txt
  Verify: every window shows Transcript: line in log.
  Do not proceed until transcript lines are visible.

FIX 2: verse_detector.py — full rewrite
  Implement all 7 steps exactly as specified above.
  Run: python verse_detector.py → all 25 tests pass.
  If any test fails → fix the rewrite, do not benchmark yet.
  Only benchmark after all 25 tests pass.
  Benchmark → logs/regex_fix2.txt
  
  Expected after Fix 2:
    Romans 8:1   → detected via regex ✅
    Genesis 1:1  → detected via regex ✅
    John 4:24    → detected via vector ✅ (unchanged)
    Genesis 1:27 → detected via vector ✅ (unchanged)
    Song of Solomon → NOT triggered ✅

FIX 3 (only if Song of Solomon returns after Fix 2):
  The false positive means GATE A or B is too permissive.
  Tighten GATE A: require the book name to appear within 
  15 words of the chapter/verse numbers, not anywhere 
  in the full buffer text.
  Re-run 25 self-tests → all must pass.
  Benchmark → logs/regex_fix3.txt

FIX 4 (only if a regex verse is still missing after Fix 2-3):
  Add temporary debug line in detect_explicit():
    logger.debug(f"[REGEX] normalised text: '{text}'")
    logger.debug(f"[REGEX] book found: '{book}' score:{score}")
    logger.debug(f"[REGEX] gate result: {gate_passed}")
  Run benchmark with log_level = DEBUG in config.ini.
  Read the debug output to find exactly where detection fails.
  Fix the specific failing step. Remove debug lines after fix.
  Benchmark → logs/regex_fix4.txt
═══════════════════════════════════════════════════════════════════
LOOP PROTOCOL — identical to previous session:

  consecutive_passes = 0

  LOOP:
    run: python main.py --test-file tests/test_audio.wav
    
    check all 8 conditions:
      1. Romans 8:1 detected, latency <= 10s
      2. John 4:24 detected, latency <= 10s
      3. Genesis 1:1 detected, latency <= 10s
      4. Genesis 1:27 detected, latency <= 10s
      5. Song of Solomon NOT triggered
      6. Every window has Transcript: line in log
      7. No spike > 15s
      8. Zero HTTP calls
    
    if all 8 pass:
      consecutive_passes += 1
      if consecutive_passes == 3: → COMMIT AND STOP
      else: run again immediately
    
    else:
      consecutive_passes = 0
      identify which conditions failed
      apply next targeted fix from fix sequence
      run verse_detector.py self-tests if regex changed
      loop again

  No other exit exists. Loop until 3 consecutive passes.
═══════════════════════════════════════════════════════════════════
FINAL COMMIT:

  git add -A
  git commit -m "fix: regex rewrite + transcript logging restored

  Romans 8:1:   Xs avg (3 runs) — regex
  John 4:24:    Xs avg — vector
  Genesis 1:1:  Xs avg — regex  
  Genesis 1:27: Xs avg — vector
  Song of Solomon: not triggered
  Transcript logging: restored, every window
  HTTP calls: 0
  Consecutive passes: 3/3

  verse_detector.py rewritten from scratch:
  normalisation → book detection → context gate → 
  chapter/verse extraction → 25 self-tests pass"

  git tag v2.2.0-stable

  Update build_progress.md with final metrics.
  Then stop.
═══════════════════════════════════════════════════════════════════
WHAT YOU MUST NOT TOUCH:

  transcriber.py        ← working, do not touch
  vector_search.py      ← working, do not touch
  bible_db.py           ← working, do not touch
  build_vector_db.py    ← do not run or touch
  data/ folder          ← do not touch
  threading model       ← working, do not touch
  queue logic           ← working, do not touch
  VAD gate              ← working, do not touch
  offline env vars      ← working, do not touch
  pre-warm logic        ← working, do not touch
  config.ini values     ← do not change any values

Only verse_detector.py and the transcript logging line 
in main.py are permitted to change in this session.
Everything else is locked.
ENDOFFILE
echo "Done"
Output

Done
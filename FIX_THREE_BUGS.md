# FIX_THREE_BUGS.md
# MultiVerse — Three Code Bug Fixes
# Autonomous loop — stops only when all objectives pass across 3 consecutive runs
# Based on: repo_report.md v2.2.0-stable
# ─────────────────────────────────────────────────────────────────────────────
# AGENT: Read GEMINI.md first. Then read every word of this file.
# All previous override rules remain active:
#   - Do NOT write to reply.md and stop
#   - Do NOT ask questions
#   - Do NOT stop until 3 consecutive full passes
#   - Do NOT stack multiple fixes simultaneously
# ─────────────────────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════
SECTION 1 — THE THREE BUGS (understand before touching any code)
═══════════════════════════════════════════════════════════════════

BUG 1 — VAD GATE NOT BLOCKING SILENCE (main.py)
─────────────────────────────────────────────────
Evidence from live log:
  INFO: Transcript: ''  (54.86s)
  INFO: Transcript: ''  (59.93s)
  INFO: Transcript: ''  (36.35s)

Empty transcripts should never reach Whisper.
Whisper running on silence takes 30–60s and produces nothing.
The VAD (Voice Activity Detection) gate exists in config.ini
as vad_rms_threshold = 0.015 but is either:
  (a) not being checked before the window enters the queue, OR
  (b) threshold is too low to catch near-silence audio

Root cause: VAD check position in the pipeline is wrong.
It must run BEFORE audio_queue.put() — not after.
If it runs after, silence still enters the queue and 
still reaches Whisper before being discarded.

Fix: Move RMS check to be the first thing that happens
when a new audio window is generated. If RMS < threshold,
discard immediately. Never touch the queue. Never touch Whisper.

─────────────────────────────────────────────────────────────────
BUG 2 — BOOK MEMORY DOUBLE-FIRE (verse_detector.py)
─────────────────────────────────────────────────────
Evidence from live log:
  "Job chapter 4 verse 4. See."
  → TRIGGERED: Ruth 4:4  ← WRONG
  "Job."
  → TRIGGERED: Job 4:4   ← correct but one window late

What happened:
  _last_book from a previous citation was still active.
  When "Job chapter 4 verse 4" was processed, the gate
  found the chapter/verse pattern and used the stale
  _last_book instead of the "Job" that was right there
  in the same text.

Root cause: Book extraction runs AFTER the context gate.
The gate checks _last_book_time first. If memory is active,
it uses that stored book instead of looking for a book in
the CURRENT text. "Job" is right there but ignored.

Fix: When a book name is found in the CURRENT text,
it ALWAYS takes priority over book memory.
Book memory is only used when NO book name is found
in the current window at all.
Clear _last_book immediately when a new book name
is detected in the current window.

─────────────────────────────────────────────────────────────────
BUG 3 — HYPHEN SEPARATOR NOT HANDLED (verse_detector.py)
─────────────────────────────────────────────────────────
Evidence from live log:
  Transcript: 'Revelation chapter.'   → no trigger
  Transcript: 'The wind was one.'     → no trigger
  Transcript: 'Revelations 1-1.'      → no trigger

"Revelations 1-1" should match Revelation 1:1.
The regex expects colon (1:1) or space (1 1) as separator.
Whisper sometimes outputs hyphens between numbers.
The pattern "Book N-N" is never matched.

Fix: Add hyphen as a valid chapter-verse separator
in all regex patterns alongside colon and space.
Also normalise "Revelations" → "Revelation" as an alias.
(already in book list but verify it is fuzzy-matched)

═══════════════════════════════════════════════════════════════════
SECTION 2 — FILES PERMITTED TO CHANGE
═══════════════════════════════════════════════════════════════════

PERMITTED:
  main.py           ← BUG 1 fix (VAD gate position)
  verse_detector.py ← BUG 2 fix (book priority) + BUG 3 fix (hyphen)

LOCKED — DO NOT TOUCH:
  transcriber.py
  vector_search.py
  bible_db.py
  build_vector_db.py
  config.ini        ← values stay the same, only code changes
  data/ folder
  requirements.txt
  GEMINI.md

═══════════════════════════════════════════════════════════════════
SECTION 3 — OBJECTIVES (all must pass for 3 consecutive runs)
═══════════════════════════════════════════════════════════════════

OBJ-01 | Romans 8:1      detected, latency <= 10s
OBJ-02 | John 4:24       detected, latency <= 10s
OBJ-03 | Genesis 1:1     detected, latency <= 10s
OBJ-04 | Genesis 1:27    detected, latency <= 10s
OBJ-05 | No empty transcript window exceeds 10s
         (silence windows discarded before Whisper)
OBJ-06 | "Job chapter 4 verse 4" fires Job 4:4 ONLY
         not Ruth 4:4 first then Job 4:4
OBJ-07 | "Revelation 1-1" or "Revelations 1-1" 
         fires Revelation 1:1
OBJ-08 | Zero HTTP calls at startup
OBJ-09 | Every transcript window logged at INFO level
OBJ-10 | All unit tests pass (Section 4)

A run PASSES only when OBJ-01 through OBJ-10 are ALL true.
3 consecutive passes → commit and tag → stop.

═══════════════════════════════════════════════════════════════════
SECTION 4 — TEST SUITE (test-driven, run before and after each fix)
═══════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────
TEST GROUP A — VAD Unit Tests (test in isolation, no audio file)
Run with: python -c "<test code>"

TEST A-01: VAD blocks silence
  import numpy as np
  silence = np.zeros(48000, dtype=np.float32)
  rms = float(np.sqrt(np.mean(silence ** 2)))
  assert rms < 0.015, f"FAIL: silence RMS={rms} should be < 0.015"
  print("PASS A-01: silence RMS correctly below threshold")

TEST A-02: VAD passes speech-level audio
  import numpy as np
  speech_sim = np.random.uniform(-0.05, 0.05, 48000).astype(np.float32)
  rms = float(np.sqrt(np.mean(speech_sim ** 2)))
  assert rms >= 0.015, f"FAIL: speech RMS={rms} should be >= 0.015"
  print(f"PASS A-02: speech-level RMS={rms:.4f} correctly above threshold")

TEST A-03: VAD runs before queue (structural test)
  # Open main.py and verify VAD check appears BEFORE queue.put()
  # by checking line order in the source file
  with open('main.py', 'r') as f:
      content = f.read()
  vad_pos = content.find('vad_rms_threshold')
  queue_pos = content.find('audio_queue.put')
  assert vad_pos < queue_pos, (
      f"FAIL A-03: VAD check (line pos {vad_pos}) must appear "
      f"BEFORE queue.put (line pos {queue_pos})"
  )
  print("PASS A-03: VAD gate confirmed before queue.put()")

────────────────────────────────────────────────────────────────
TEST GROUP B — Book Priority Unit Tests
Run with: python verse_detector.py (self-tests at bottom of file)

These exact cases MUST be in the self-test block:

TEST B-01: Current book overrides memory
  # Simulate: _last_book = "Ruth", _last_book_time = recent
  # Input: "Job chapter 4 verse 4"
  # Expected: Job 4:4 (NOT Ruth 4:4)
  result = detect_explicit("Job chapter 4 verse 4")
  assert result is not None, "FAIL B-01: no match returned"
  assert result['book'] == 'Job', (
      f"FAIL B-01: expected Job, got {result['book']} "
      f"(book memory not overridden by current text)"
  )
  assert result['chapter'] == 4, f"FAIL B-01: expected ch 4, got {result['chapter']}"
  assert result['verse'] == 4, f"FAIL B-01: expected v 4, got {result['verse']}"
  print("PASS B-01: current book correctly overrides stale memory")

TEST B-02: Memory used when no book in current window
  # Call detect_explicit with Genesis to set memory
  detect_explicit("book of Genesis chapter 1")
  import time; time.sleep(0.1)
  # Now call with just numbers — should use Genesis from memory
  result = detect_explicit("verse 1")
  assert result is not None, "FAIL B-02: memory not used for bare verse reference"
  assert result['book'] == 'Genesis', (
      f"FAIL B-02: expected Genesis from memory, got {result['book']}"
  )
  print("PASS B-02: book memory correctly used when no book in current text")

TEST B-03: Memory expires after book_memory_seconds
  import time
  detect_explicit("book of Romans 8:1")  # set memory
  time.sleep(6)  # wait past 5s expiry
  result = detect_explicit("verse 1")   # no book in text
  assert result is None, (
      f"FAIL B-03: expired memory should not match, got {result}"
  )
  print("PASS B-03: expired book memory correctly ignored")

────────────────────────────────────────────────────────────────
TEST GROUP C — Hyphen Separator Unit Tests
Run with: python verse_detector.py (self-tests at bottom of file)

TEST C-01: Hyphen separator detected
  result = detect_explicit("Revelation 1-1")
  assert result is not None, "FAIL C-01: Revelation 1-1 not matched"
  assert result['book'] == 'Revelation', (
      f"FAIL C-01: expected Revelation, got {result['book']}"
  )
  assert result['chapter'] == 1, f"FAIL C-01: expected ch 1, got {result['chapter']}"
  assert result['verse'] == 1, f"FAIL C-01: expected v 1, got {result['verse']}"
  print("PASS C-01: hyphen separator correctly parsed")

TEST C-02: "Revelations" alias resolves to Revelation
  result = detect_explicit("Revelations 1-1")
  assert result is not None, "FAIL C-02: Revelations 1-1 not matched"
  assert result['book'] == 'Revelation', (
      f"FAIL C-02: expected Revelation, got {result['book']}"
  )
  print("PASS C-02: Revelations alias correctly resolves to Revelation")

TEST C-03: Hyphen with chapter keyword
  result = detect_explicit("Revelation chapter 22-21")
  assert result is not None, "FAIL C-03: Revelation chapter 22-21 not matched"
  assert result['chapter'] == 22, f"FAIL C-03: expected ch 22, got {result['chapter']}"
  assert result['verse'] == 21, f"FAIL C-03: expected v 21, got {result['verse']}"
  print("PASS C-03: hyphen with chapter keyword correctly parsed")

────────────────────────────────────────────────────────────────
TEST GROUP D — Regression Tests (must still pass after all fixes)
These were passing before — must remain passing.

TEST D-01: Romans 8:1 explicit
  result = detect_explicit("Romans chapter 8 verse 1")
  assert result['book'] == 'Romans' and result['chapter'] == 8 and result['verse'] == 1
  print("PASS D-01: Romans 8:1 explicit")

TEST D-02: Romans 8:1 with "was" normalisation
  result = detect_explicit("Romans chapter 8 was 1")
  assert result is not None and result['book'] == 'Romans'
  print("PASS D-02: Romans 8:1 with was→verse normalisation")

TEST D-03: Genesis 1:1 explicit
  result = detect_explicit("book of Genesis 1:1")
  assert result['book'] == 'Genesis' and result['chapter'] == 1 and result['verse'] == 1
  print("PASS D-03: Genesis 1:1 explicit")

TEST D-04: Genesis cross-window via book memory
  detect_explicit("book of Genesis chapter")
  import time; time.sleep(0.1)
  result = detect_explicit("1 verse 1")
  assert result is not None and result['book'] == 'Genesis'
  print("PASS D-04: Genesis cross-window via book memory")

TEST D-05: Song of Solomon false positive prevention
  result = detect_explicit("1 verse 1")  # no prior book context
  assert result is None, f"FAIL D-05: bare '1 verse 1' should return None, got {result}"
  print("PASS D-05: bare digit sequence correctly returns None")

TEST D-06: John 3:16 standard
  result = detect_explicit("John 3:16")
  assert result['book'] == 'John' and result['chapter'] == 3 and result['verse'] == 16
  print("PASS D-06: John 3:16 standard")

TEST D-07: First Corinthians ordinal
  result = detect_explicit("First Corinthians 13:4")
  assert result['book'] == '1 Corinthians'
  print("PASS D-07: First Corinthians ordinal normalised")

────────────────────────────────────────────────────────────────
TEST GROUP E — Full Pipeline Integration Test
Run with: python main.py --test-file tests/test_audio.wav

All of these must appear in the output:

REQUIRED TRIGGERS (verse + detection method):
  Romans 8:1      regex     ✅
  John 4:24       vector    ✅
  Genesis 1:1     regex     ✅
  Genesis 1:27    vector    ✅

REQUIRED LOG BEHAVIOUR:
  Every window shows: INFO: Transcript: '<text>'  (Xs)
  No empty transcript window takes > 10s
  No double-fire: same verse fires maximum once per cooldown period

REQUIRED ABSENCE (must NOT appear):
  Ruth 4:4        ← book memory bug
  Song of Solomon ← false positive

LATENCY REQUIREMENT:
  All four target verses: latency_ms <= 10000 (10s)

════════════════════════════════════════════════════════════════
SECTION 5 — FIX IMPLEMENTATION SPECS
════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────
FIX 1 — main.py: Move VAD gate before queue

CURRENT (wrong):
  audio enters queue
  → dequeued by processing thread
  → VAD checked
  → if silent, discarded
  → but Whisper may already be called

CORRECT:
  audio window generated
  → RMS calculated immediately
  → if RMS < threshold: log skip, continue, never touch queue
  → if RMS >= threshold: put in queue
  → processing thread always receives speech audio only

Implementation:
  # In the audio window generation loop (Thread 1 or file reader):
  
  rms = float(np.sqrt(np.mean(window ** 2)))
  vad_threshold = float(config['audio']['vad_rms_threshold'])
  
  if rms < vad_threshold:
      logger.debug(f"VAD: silence skipped (RMS={rms:.4f})")
      # Print triggered:false so output stream stays continuous
      print(json.dumps({
          "triggered": False,
          "transcript": {"current": "", "tail": "", "full_window": ""}
      }))
      continue  # Never reaches queue.put()
  
  # Only speech reaches here
  try:
      audio_queue.put_nowait(window.copy())
  except queue.Full:
      try:
          audio_queue.get_nowait()
          logger.warning("Queue full — dropped oldest window to stay current")
      except queue.Empty:
          pass
      audio_queue.put_nowait(window.copy())

────────────────────────────────────────────────────────────────
FIX 2 — verse_detector.py: Book priority over memory

CURRENT LOGIC (wrong):
  1. Check if _last_book is active (memory)
  2. If memory active → use it as book context
  3. Look for chapter/verse numbers
  4. Return match using memory book

  Problem: Step 2 uses memory BEFORE checking current text.
  "Job chapter 4 verse 4" → memory was "Ruth" → fires Ruth.

CORRECT LOGIC:
  1. Extract book name from CURRENT text (fuzzy match)
  2. If book found in current text:
       → use it as the book
       → update _last_book to this new book
       → clear old memory
  3. If NO book found in current text:
       → check if _last_book memory is still valid
       → if valid: use memory book
       → if expired: no book context → return None
  4. With confirmed book context: extract chapter/verse
  5. Return match

Implementation change in detect_explicit():

  # STEP 1: Try to find book in current text FIRST
  current_book = _find_book_in_text(normalised_text)
  
  if current_book:
      # Current text has a book — use it, update memory
      _last_book = current_book
      _last_book_time = time.time()
      book_for_match = current_book
  
  elif _last_book and (time.time() - _last_book_time) < book_memory_seconds:
      # No book in current text, but valid memory exists
      book_for_match = _last_book
  
  else:
      # No book anywhere — cannot match
      return None
  
  # STEP 2: Find chapter and verse using book_for_match
  # ... rest of extraction logic

────────────────────────────────────────────────────────────────
FIX 3 — verse_detector.py: Hyphen as valid separator

Add hyphen to all chapter-verse separator patterns.
Current patterns use [:] or [\s] — add [-] to both.

Pattern changes needed:

  # Before (colon only):
  PATTERN_COLON = r'(\d+)\s*:\s*(\d+)'
  
  # After (colon or hyphen):
  PATTERN_SEPARATOR = r'(\d+)\s*[:\-]\s*(\d+)'

Apply this change to every pattern that extracts 
chapter:verse pairs. Not just one pattern — all of them.

Also verify "Revelations" is in the BOOK_ALIASES dict:
  "Revelations": "Revelation"
  
Add if missing. This is separate from the BOOK_NAME_TO_NUMBER
mapping — it is a pre-normalisation alias replacement that
runs before fuzzy matching.

════════════════════════════════════════════════════════════════
SECTION 6 — FIX SEQUENCE AND LOOP PROTOCOL
════════════════════════════════════════════════════════════════

BEFORE ANY FIX:
  Step 1: Run all unit tests (Groups A, B, C, D)
          Record which pass and which fail.
          Save results to logs/pre_fix_tests.txt
  
  Step 2: Run pipeline test (Group E)
          Save output to logs/pre_fix_pipeline.txt
          Record: which verses triggered, latencies,
          silence spike count, double-fire count.

──────────────────────────────────────────────────────────────
FIX 1 — VAD gate position (main.py only)

  Apply fix as specified in Section 5 Fix 1.
  
  Run TEST GROUP A immediately after:
    python -c "<TEST A-01 code>"
    python -c "<TEST A-02 code>"
    python -c "<TEST A-03 code>"
  
  All 3 must print PASS before proceeding.
  Save test output to logs/fix1_unit_tests.txt
  
  Run pipeline test:
    python main.py --test-file tests/test_audio.wav
  Save to logs/fix1_pipeline.txt
  
  Verify:
    □ No transcript takes > 10s with empty text
    □ All 4 target verses still detected
    □ OBJ-05 satisfied
  
  If all pass: git add main.py
               git commit -m "fix(vad): move RMS gate before queue — silence never reaches Whisper"
  If any fail: revert main.py, log failure, diagnose.

──────────────────────────────────────────────────────────────
FIX 2 — Book priority over memory (verse_detector.py only)

  Apply fix as specified in Section 5 Fix 2.
  
  Run TEST GROUP B immediately after:
    python verse_detector.py
  Tests B-01, B-02, B-03 must all print PASS.
  Save to logs/fix2_unit_tests.txt
  
  Also run regression tests D-01 through D-07.
  ALL must pass — fixes must not break existing behaviour.
  
  Run pipeline test:
    python main.py --test-file tests/test_audio.wav
  Save to logs/fix2_pipeline.txt
  
  Verify:
    □ Ruth 4:4 does NOT appear in output
    □ Job 4:4 fires correctly when "Job chapter 4 verse 4" is said
    □ OBJ-06 satisfied
    □ All 4 target verses still detected
  
  If all pass: git add verse_detector.py
               git commit -m "fix(regex): current book always overrides stale memory — eliminates double-fire"
  If any fail: revert verse_detector.py, log failure, diagnose.

──────────────────────────────────────────────────────────────
FIX 3 — Hyphen separator (verse_detector.py only)

  Apply fix as specified in Section 5 Fix 3.
  
  Run TEST GROUP C immediately after:
    python verse_detector.py
  Tests C-01, C-02, C-03 must all print PASS.
  Save to logs/fix3_unit_tests.txt
  
  Also run all regression tests D-01 through D-07.
  ALL must still pass.
  
  Run pipeline test:
    python main.py --test-file tests/test_audio.wav
  Save to logs/fix3_pipeline.txt
  
  Verify:
    □ "Revelation 1-1" type input fires Revelation 1:1
    □ OBJ-07 satisfied
    □ All 4 target verses still detected
  
  If all pass: git add verse_detector.py
               git commit -m "fix(regex): hyphen accepted as chapter-verse separator — Revelation 1-1 now matches"
  If any fail: revert verse_detector.py to post-Fix-2 state,
               log failure, diagnose, retry.

════════════════════════════════════════════════════════════════
SECTION 7 — FULL VERIFICATION LOOP
════════════════════════════════════════════════════════════════

After all three fixes are committed individually,
run the full verification loop:

  consecutive_passes = 0

  LOOP:
    Step 1: Run ALL unit tests (Groups A + B + C + D)
      python verse_detector.py
      python -c "<A-01>" && python -c "<A-02>" && python -c "<A-03>"
      Save all output to logs/full_verify_run_N.txt

    Step 2: Run pipeline test (Group E)
      python main.py --test-file tests/test_audio.wav
      Append output to logs/full_verify_run_N.txt

    Step 3: Evaluate all 10 objectives:
      OBJ-01: Romans 8:1 detected, latency <= 10s    ✅/❌
      OBJ-02: John 4:24 detected, latency <= 10s     ✅/❌
      OBJ-03: Genesis 1:1 detected, latency <= 10s   ✅/❌
      OBJ-04: Genesis 1:27 detected, latency <= 10s  ✅/❌
      OBJ-05: No silence window > 10s                ✅/❌
      OBJ-06: No Ruth 4:4 false fire                 ✅/❌
      OBJ-07: Revelation 1-1 fires Revelation 1:1    ✅/❌
      OBJ-08: Zero HTTP calls at startup             ✅/❌
      OBJ-09: Every window logged at INFO level      ✅/❌
      OBJ-10: All unit tests pass                    ✅/❌

    Step 4: All 10 pass?
      YES → consecutive_passes += 1
            log "PASS (N/3)"
            if consecutive_passes == 3 → FINAL COMMIT (Section 8)
            else → loop immediately

      NO  → consecutive_passes = 0
            identify exactly which objectives failed
            identify which fix is responsible
            re-apply that specific fix (not all three)
            re-run that fix's unit tests and pipeline test
            loop again

    LOOP NEVER STOPS until consecutive_passes == 3.
    No other exit condition exists.

════════════════════════════════════════════════════════════════
SECTION 8 — FINAL COMMIT
════════════════════════════════════════════════════════════════

After 3 consecutive full passes, run exactly this:

  git add -A
  git commit -m "fix(bugs): three code fixes — VAD gate + book priority + hyphen separator

  BUG 1 FIXED: VAD gate moved before queue.put()
    - Silence windows no longer reach Whisper
    - 30-60s empty transcript spikes eliminated
    - Silent chunks discarded at capture, not at processing

  BUG 2 FIXED: Current book always overrides stale memory
    - 'Job chapter 4 verse 4' now fires Job 4:4 directly
    - No more double-fire (Ruth 4:4 then Job 4:4)
    - Book memory only used when NO book in current text

  BUG 3 FIXED: Hyphen accepted as chapter-verse separator
    - 'Revelation 1-1' now matches Revelation 1:1
    - 'Revelations' alias confirmed in normalisation
    - All existing colon and space separators unchanged

  Test results (3 consecutive runs):
    Unit tests:     A-01 A-02 A-03 B-01 B-02 B-03 C-01 C-02 C-03
                    D-01 D-02 D-03 D-04 D-05 D-06 D-07 — ALL PASS
    Pipeline:       Romans 8:1 Xs | John 4:24 Xs |
                    Genesis 1:1 Xs | Genesis 1:27 Xs
    Silence spikes: 0
    False fires:    0
    HTTP calls:     0
    Consecutive passes: 3/3"

  git tag v2.3.0-bugfix

  Write final summary to build_progress.md:
    - All unit test results
    - Pipeline latencies (min/max/avg across 3 runs)
    - Silence spikes before fix vs after fix
    - False fires before fix vs after fix
    - Tag: v2.3.0-bugfix
    - "Build complete."

  Then stop. The job is done.

════════════════════════════════════════════════════════════════
SECTION 9 — WHAT YOU MUST NOT DO
════════════════════════════════════════════════════════════════

  - Do not apply all three fixes at once
  - Do not commit a failing state
  - Do not skip unit tests before pipeline tests
  - Do not declare a fix complete without unit test PASS output
  - Do not change config.ini values
  - Do not touch transcriber.py, vector_search.py, bible_db.py
  - Do not re-run build_vector_db.py
  - Do not write to reply.md and stop
  - Do not stop for any reason except 3 consecutive full passes


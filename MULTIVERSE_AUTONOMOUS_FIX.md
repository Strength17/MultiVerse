# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop.

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop.

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop.

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop.

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.# MULTIVERSE_AUTONOMOUS_FIX.md
# Paste this entire file to Gemini CLI: gemini -m gemini-2.5-pro < MULTIVERSE_AUTONOMOUS_FIX.md
# You are a senior systems engineer. Execute this loop without stopping until SUCCESS CRITERIA are met.
# ─────────────────────────────────────────────────────────────────────────────

## YOUR MANDATE

You are running an autonomous optimization loop on the MultiVerse scripture detection backend.
You will execute fixes from the IMPROVEMENT QUEUE in strict order.
After each fix, you will run the benchmark and compare against SUCCESS CRITERIA.
You will not stop until all SUCCESS CRITERIA pass or you have exhausted the queue.
You will commit every improvement and revert every regression automatically.
You will report your final state when done.

---

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop.

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.

## SUCCESS CRITERIA — THE DEFINITION OF DONE
All six criteria must pass simultaneously before you stop. 

```
SC-01: vector_search load time       <= 6.0 seconds
SC-02: warm latency average (all 4)  <= 6.0 seconds per verse
SC-03: Romans 8:1 latency            <= 10.0 seconds
SC-04: John 4:24 latency             <= 8.0 seconds
SC-05: Song of Solomon false positive = 0 (must NOT trigger)
SC-06: Zero HTTP requests to huggingface.co on startup
```

---

## BASELINE (What you are measuring against)

```
vector_search load:  29.50s  ← HTTP calls to HuggingFace on every startup
Romans 8:1 latency:  18.98s  ← avg across 2 runs
John 4:24 latency:   19.21s  ← thread contention regression
Genesis 1:27:         3.65s  ← acceptable (wrong verse but close)
Song of Solomon 1:1:  3.93s  ← FALSE POSITIVE — must be eliminated
HTTP calls on start: ~23     ← system is NOT offline despite spec
```

---

## BENCHMARK PROTOCOL
Run after every single fix. Do not skip.

```bash
# Step 1: Run the benchmark, capture ALL output including stderr
python main.py --test-file tests/test_audio.wav > logs/bench_FIXNAME.txt 2>&1

# Step 2: Extract and display key metrics
python - << 'MEASURE'
import re, sys

name = "FIXNAME"  # replace with actual fix name each time
log = open(f"logs/bench_{name}.txt").read()

# Check for HTTP calls (offline violation)
http_calls = log.count("huggingface.co")
print(f"HTTP calls to HuggingFace: {http_calls}  {'FAIL' if http_calls > 0 else 'PASS'}")

# Vector search load time
load_match = re.search(r"Vector search resources loaded in ([\d.]+)s", log)
load_time = float(load_match.group(1)) if load_match else 999.0
print(f"Vector search load: {load_time:.2f}s  {'PASS' if load_time <= 6.0 else 'FAIL'}")

# Per-verse latencies
latencies = re.findall(r"TRIGGERED: (.+?) via .+? \(latency ([\d.]+)s\)", log)
print(f"\nDetected verses and latencies:")
for verse, lat in latencies:
    print(f"  {verse}: {float(lat):.2f}s")

# False positive check
false_pos = "Song of Solomon" in log and "TRIGGERED" in log and \
            log.index("Song of Solomon") < log.rindex("TRIGGERED")
# More precise check
import re as _re
triggered = _re.findall(r"TRIGGERED: (.+?) via", log)
has_sol = any("Song of Solomon" in t for t in triggered)
print(f"\nSong of Solomon false positive: {'PRESENT - FAIL' if has_sol else 'ABSENT - PASS'}")

# All-verse average latency
lats = [float(l) for _, l in latencies if "Song of Solomon" not in _]
avg = sum(lats)/len(lats) if lats else 999.0
print(f"\nWarm avg latency (excl. false pos): {avg:.2f}s  {'PASS' if avg <= 6.0 else 'FAIL'}")

# Summary
print("\n--- CRITERIA CHECK ---")
print(f"SC-01 load <= 6.0s:        {'PASS' if load_time <= 6.0 else 'FAIL'} ({load_time:.2f}s)")
print(f"SC-02 warm avg <= 6.0s:    {'PASS' if avg <= 6.0 else 'FAIL'} ({avg:.2f}s)")

romans = next((float(l) for v,l in latencies if "Romans" in v), 999.0)
john = next((float(l) for v,l in latencies if "John" in v), 999.0)
print(f"SC-03 Romans <= 10.0s:     {'PASS' if romans <= 10.0 else 'FAIL'} ({romans:.2f}s)")
print(f"SC-04 John <= 8.0s:        {'PASS' if john <= 8.0 else 'FAIL'} ({john:.2f}s)")
print(f"SC-05 no false positive:   {'PASS' if not has_sol else 'FAIL'}")
print(f"SC-06 zero HTTP calls:     {'PASS' if http_calls == 0 else 'FAIL'} ({http_calls} calls)")
MEASURE
```

---

## IMPROVEMENT QUEUE
Execute in this EXACT order. One fix at a time. Benchmark between every fix.

---

### FIX-01: Force True Offline Mode
**Root cause:** `sentence_transformers` calls HuggingFace to verify model files on every load.
**Impact:** Eliminates ~23 HTTP calls. Drops vector search load from 29.5s to under 6s.
**Files:** `vector_search.py` (top of file, before ALL other imports)

Add these lines as the VERY FIRST executable lines in `vector_search.py`, before any import:
```python
# vector_search.py
# OFFLINE MODE: Force sentence_transformers to use only cached local files.
# This eliminates ~23 HTTP round trips to huggingface.co on every startup.
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Also add the same block to the TOP of `main.py` (before any imports), to ensure it is set
before any lazy imports trigger a HuggingFace call:
```python
# main.py
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# --- all other imports below this line ---
```

**Benchmark after applying. Expect:**
- HTTP calls: 0 (SC-06 should PASS)
- Vector load: under 6s (SC-01 should PASS)

**Commit if SC-01 and SC-06 both pass:**
```bash
git add vector_search.py main.py
git commit -m "fix(FIX-01): force offline mode | HF HTTP calls 23→0 | load time ~29s→<6s"
```

**Revert if SC-01 fails or app crashes:**
```bash
git revert HEAD --no-edit
```

---

### FIX-02: Eliminate Thread Contention (Fix John 4:24 Regression)
**Root cause:** Transcription thread (CPU-heavy) and vector search thread (CPU-heavy) run concurrently
on the same N3530 core, starving each other. One chunk took 19.36s because the previous vector
search was still running.
**Impact:** Brings John 4:24 from 19.21s back toward 6s range.
**File:** `main.py`

Find the section where audio chunks are pulled from the queue and processed.
The fix is to make transcription and detection run in the SAME thread sequentially,
not in competing threads. Change the architecture:

Current (broken):
```
Thread A: audio capture → queue
Thread B: transcribe → detect  (runs concurrently with Thread A, competes for CPU)
```

Target (fixed):
```
Thread A: audio capture → audio_queue (minimal CPU, just buffering)
Thread B: transcribe chunk (blocks until done)
          detect on result (blocks until done, then loop)
```

In `main.py`, find the processing worker function. Ensure it processes ONE chunk
completely (transcribe + detect) before picking up the NEXT chunk from the queue.
Do NOT use thread pool or concurrent.futures for the transcription+detection step.

Also: add a queue size limit to prevent backpressure buildup:
```python
# When creating the queue:
audio_queue = queue.Queue(maxsize=2)  # Drop old chunks if falling behind
```

And in the audio capture thread, use non-blocking put:
```python
try:
    audio_queue.put_nowait(chunk)
except queue.Full:
    logger.warning("[QUEUE] Dropped chunk — processing cannot keep up with capture rate")
```

This is better than letting the queue grow unbounded and processing audio from 30 seconds ago.

**Benchmark after applying. Expect:**
- John 4:24 latency: under 8s (SC-04 should PASS)
- No 19s+ individual chunk transcription times

**Commit if SC-04 passes:**
```bash
git add main.py
git commit -m "fix(FIX-02): serialize transcription+detection | eliminated thread contention | John 4:24 regression fixed"
```

---

### FIX-03: Fix the "was"→"verse" Alias False Positive
**Root cause:** The regex alias map converts "was" → "verse" to handle transcription errors.
But "was" is an extremely common English word. "1 was 1" becomes "1 verse 1" which
triggers "Song of Solomon 1:1" as a false positive.
**Impact:** Eliminates the Song of Solomon false positive entirely.
**File:** `verse_detector.py`

**Step 1:** Remove "was" from the alias list completely. It causes more harm than good.
Find the alias/synonym dictionary and delete the "was": "verse" entry:
```python
# DELETE this line or comment it out:
# "was": "verse",   # removed: causes false positives with "1 was 1" etc.
```

**Step 2:** Add a BOOK-NAME CONTEXT REQUIREMENT to the regex engine.
A verse reference should only trigger if a valid Bible book name appears in the
SAME chunk or the immediately preceding chunk (already in the transcript buffer).
Add this validation gate at the end of the `detect_explicit` function, BEFORE returning a result:

```python
def _has_book_context(buffer_text: str, detected_book: str) -> bool:
    """
    Validates that the detected book name (or a known alias) actually appears
    in the transcript text. Prevents digit-only patterns like '1:1' from
    triggering without an explicit book mention.
    
    Args:
        buffer_text: The combined transcript text being searched.
        detected_book: The book name returned by the regex match.
    Returns:
        True if the book name or a known alias appears in the text.
    """
    if not detected_book:
        return False
    text_lower = buffer_text.lower()
    book_lower = detected_book.lower()
    # Check canonical name
    if book_lower in text_lower:
        return True
    # Check known aliases (add your alias list here)
    BOOK_ALIASES = {
        "genesis": ["gen"],
        "exodus": ["exod", "exo"],
        "psalms": ["psalm", "psa"],
        "proverbs": ["prov"],
        "romans": ["rom"],
        "revelation": ["rev", "revelations"],
        "song of solomon": ["song of songs", "song", "solomon"],
        # ... add all others from your existing alias map
    }
    for alias in BOOK_ALIASES.get(book_lower, []):
        if alias in text_lower:
            return True
    return False
```

In the main `detect_explicit` function, before returning any result:
```python
# At the point where you have a match (book, chapter, verse):
if not _has_book_context(text, book_name):
    logger.debug(f"[REGEX] Rejected match '{book_name} {chapter}:{verse}' — no book name in context")
    return None
```

**Benchmark after applying. Expect:**
- Song of Solomon false positive: GONE (SC-05 should PASS)
- All genuine verses still detected

**Commit if SC-05 passes and no genuine verses are lost:**
```bash
git add verse_detector.py
git commit -m "fix(FIX-03): remove 'was' alias, add book-context gate | Song of Solomon false positive eliminated"
```

**If a genuine verse is now missed after this fix:** The book name is not appearing
in the transcript at all — that is a transcription quality issue, not a regex issue.
Do not revert the safety fix. Note the miss in the log and continue.

---

### FIX-04: Tune Transcript Buffer Depth
**Root cause:** Buffer depth=2 (6s context) helped Romans 8:1 but hurt John 4:24
and shifted Genesis verse numbers. Need to find the optimal depth.
**File:** `config.ini` (or wherever buffer depth is configured), `main.py`

**Step 1:** Check current buffer depth:
```bash
python -c "
import configparser, re
# Try config.ini first
try:
    c = configparser.ConfigParser()
    c.read('config.ini')
    for section in c.sections():
        for k, v in c[section].items():
            if 'buffer' in k or 'depth' in k or 'context' in k:
                print(f'[{section}] {k} = {v}')
except: pass
# Also grep main.py
import subprocess
result = subprocess.run(['grep', '-n', 'depth\|buffer\|deque', 'main.py'],
                       capture_output=True, text=True)
print(result.stdout[:500])
"
```

**Step 2:** Test with depth=1 (3s context). Change the buffer depth to 1:
- In `main.py` find `deque(maxlen=...)` or `depth=2` and change to `depth=1`
- Run benchmark

**Step 3:** Compare depth=1 vs depth=2 results:
- If depth=1: John 4:24 is detected AND latency is better → keep depth=1
- If depth=1: John 4:24 is MISSED → revert to depth=2 and accept the tradeoff
- Record which depth gives best results

**Commit whichever depth gives most SC criteria passing:**
```bash
git add main.py config.ini
git commit -m "tune(FIX-04): transcript buffer depth=X | trigger_count=4 | avg_latency=Xs"
```

---

### FIX-05: Whisper Temperature=0 (Greedy Decode — 20-40% Faster)
**Root cause:** By default, openai-whisper uses beam search (temperature > 0).
Temperature=0 forces greedy decoding: pick the most probable token at each step.
On a slow CPU this saves significant compute per chunk.
**Impact:** Reduces per-chunk transcription time by 20-40% at minor accuracy cost.
**File:** `transcriber.py`

Find the `model.transcribe(...)` call (openai-whisper branch) and add:
```python
result = model.transcribe(
    audio_array,
    language="en",
    fp16=False,           # must be False on CPU
    temperature=0,        # greedy decode: faster, slightly less accurate
    compression_ratio_threshold=2.4,
    logprob_threshold=-1.0,
    no_speech_threshold=0.6,
    condition_on_previous_text=False,  # saves memory, avoids error propagation
)
```

`condition_on_previous_text=False` is important: it prevents each chunk from
being conditioned on the previous chunk's transcription. On a slow CPU this
saves computation and also prevents error cascading (where one mistranscription
poisons the next chunk).

**Benchmark after applying. Expect:**
- Per-chunk transcription time: 3.5s → 2.5-3.0s range
- SC-02 and SC-03/SC-04 may improve further

**Commit if any latency metric improves and no verses are lost:**
```bash
git add transcriber.py
git commit -m "perf(FIX-05): whisper temperature=0 greedy decode | transcription -20-40% | condition_on_prev=False"
```

---

### FIX-06: FAISS Search Warm-Up at Import (Not at First Query)
**Root cause:** FAISS inner-product search has JIT compilation cost on the very first query.
This adds latency to whichever verse happens to be first.
**File:** `vector_search.py`

After loading the index, add a warm-up search using a zero vector:
```python
# After: index = faiss.read_index(index_path)
# Add warm-up:
import numpy as _np
import time as _time
_t = _time.perf_counter()
_dummy = _np.zeros((1, index.d), dtype='float32')
faiss.normalize_L2(_dummy)
index.search(_dummy, 3)
logger.info(f"[PREWARM] FAISS index warmed in {_time.perf_counter()-_t:.3f}s")
```

Also warm the sentence transformer model with a dummy encode:
```python
# After model is loaded:
_model.encode(["warm up"], convert_to_numpy=True, normalize_embeddings=True)
logger.info("[PREWARM] Embedding model warmed")
```

**Benchmark. Expect:** First-verse latency drop of 1-3 seconds.

**Commit if first-verse latency improves:**
```bash
git add vector_search.py
git commit -m "perf(FIX-06): FAISS and embedding model prewarm at import | first-verse latency reduced"
```

---

## AUTONOMOUS LOOP LOGIC
Execute this pseudocode exactly:

```
BASELINE = {romans: 18.98s, john: 19.21s, load: 29.5s, false_pos: 1, http: 23}
CRITERIA_MET = False

FOR each FIX in [FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06]:
    
    APPLY the fix to the relevant file(s)
    
    RUN benchmark: python main.py --test-file tests/test_audio.wav > logs/bench_FIX-XX.txt 2>&1
    
    EXTRACT metrics using the BENCHMARK PROTOCOL script above
    
    IF any SUCCESS CRITERION that previously PASSED now FAILS:
        REVERT: git revert HEAD --no-edit
        LOG: "FIX-XX caused regression in SC-XX. Reverted."
        CONTINUE to next fix
    
    IF metrics are same as before (no improvement, no regression):
        KEEP the fix (it is safe and may help later)
        git add -A && git commit -m "chore(FIX-XX): no measurable change but safe"
        CONTINUE to next fix
    
    IF metrics improved:
        git add -A
        improvement = calculate percentage improvement vs baseline
        git commit -m "perf(FIX-XX): [metric] improved by [X]%"
        LOG the improvement
        CONTINUE to next fix
    
    CHECK all 6 SUCCESS CRITERIA:
    IF all 6 PASS:
        SET CRITERIA_MET = True
        BREAK out of loop

IF CRITERIA_MET:
    git tag -a v0.3.0-optimized -m "All 6 success criteria met"
    PRINT final summary table

IF NOT CRITERIA_MET after all fixes:
    PRINT which criteria still fail and what was tried
    PRINT the best state achieved (which git commit)
```

---

## FINAL REPORT FORMAT
When the loop ends (success or exhausted), print this table:

```
=== MULTIVERSE OPTIMIZATION FINAL REPORT ===

FIX APPLIED        | BEFORE        | AFTER         | RESULT
─────────────────────────────────────────────────────────
FIX-01 offline     | load: 29.5s   | load: Xs      | PASS/FAIL
FIX-02 threading   | john: 19.21s  | john: Xs      | PASS/FAIL
FIX-03 regex gate  | false_pos: 1  | false_pos: 0  | PASS/FAIL
FIX-04 buf depth   | depth: 2      | depth: X      | PASS/FAIL
FIX-05 greedy      | warm avg: Xs  | warm avg: Xs  | PASS/FAIL
FIX-06 prewarm     | cold: Xs      | cold: Xs      | PASS/FAIL

SUCCESS CRITERIA STATUS:
SC-01 load <= 6.0s:        [PASS/FAIL] (Xs)
SC-02 warm avg <= 6.0s:    [PASS/FAIL] (Xs)
SC-03 Romans <= 10.0s:     [PASS/FAIL] (Xs)
SC-04 John <= 8.0s:        [PASS/FAIL] (Xs)
SC-05 no false positive:   [PASS/FAIL]
SC-06 zero HTTP calls:     [PASS/FAIL]

OVERALL: [ALL CRITERIA MET / X OF 6 CRITERIA MET]
BEST VERSION: [git commit hash]
```

---

## STOP CONDITIONS
Stop immediately and report to the user if:
- The test audio file is missing or produces zero transcription output
- `git revert` fails
- The Python environment crashes on import after any fix
- ALL 6 criteria pass (success — tag and stop)
- The queue is exhausted with fewer than 6 criteria passing (report best state)

---

## IMPORTANT NOTES FOR THE AGENT

1. The model files for `all-MiniLM-L6-v2` MUST already be in the HuggingFace cache
   at `~/.cache/huggingface/hub/` for FIX-01 to work. If they are not cached,
   FIX-01 will cause an error. In that case: run WITHOUT FIX-01 first (let it
   download once), then apply FIX-01 on the next run.

2. Never modify `tests/test_audio.wav`. It is the benchmark reference.

3. Never modify the SUCCESS CRITERIA. They are fixed.

4. If you discover a new bug not covered by this queue, add it as FIX-07 at the
   bottom of the queue with the same format. Do not insert it mid-queue.

5. Always run `python -c "import main; print('imports OK')"` after any file
   change before running the full benchmark. Catch import errors early.
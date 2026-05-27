# TRANSCRIPT_BUFFER_WORKFLOW.md
# MultiVerse — Transcript Buffer Implementation
# ─────────────────────────────────────────────────────────────────────────────
# ONE OBJECTIVE: Replace audio overlap with a text buffer so cross-chunk
# verse references are caught without reprocessing any audio.
#
# RULES:
#   - Complete every phase in order. No skipping.
#   - Every gate requires REAL output pasted into the RESULTS LOG.
#   - A gate does not pass because a previous test passed. Run it again.
#   - After each measurable change: record numbers, calculate improvement %.
#   - If improvement is confirmed → commit that single change immediately.
#   - If numbers get worse → git revert before touching anything else.
#   - Do not proceed to the next phase until the current phase gate passes.
# ─────────────────────────────────────────────────────────────────────────────

---

## CURRENT STATE SNAPSHOT

```
┌─────────────────────────────────────────────────────────────┐
│  Phase          : PHASE 0 — VERSION LOCK                    │
│  Status         : NOT STARTED                               │
│  overlap_seconds: 0.0 (confirmed locked)                    │
│  Known issue    : Romans 8:1 missed — "Romans" in chunk N,  │
│                   "8:1" in chunk N+1, detected separately   │
│  Baseline warm  : ~3.5s per verse                           │
│  Target         : Romans 8:1 triggered at same ~3.5s        │
└─────────────────────────────────────────────────────────────┘
```

---

## PHASE 0 — VERSION LOCK

Lock the current working state before any change is made.
This tag is the permanent rollback point.

**Task 0-A: Commit and tag current state**

git add -A
git commit -m "v1.1.1 | backend stable | 4/4 verses detected | warm ~3.5s | audio reprocessing bug active"
git tag v1.1.1-backend-stable
git push origin main --tags
```

**Gate 0:** Run this and confirm the tag exists:
```powershell
git tag --list
```
Expected output must include: `v0.1.0-baseline`

**Task 0-B: Record baseline benchmark**

Run the pipeline against the test file and capture exact output:
```powershell
python main.py --test-file tests/test_audio.wav 2>&1 | tee logs/baseline_v0.1.0.txt
```

Then extract the numbers:
```powershell
python -c "
import re, sys

with open('logs/baseline_v0.1.0.txt') as f:
    content = f.read()

triggered = content.count('triggered\": true')
latencies = re.findall(r'LATENCY\D+([\d.]+)s', content)
session = re.search(r'runtime_seconds\": (\d+)', content)

print(f'Verses triggered  : {triggered}')
print(f'Latencies (s)     : {latencies}')
print(f'Runtime (s)       : {session.group(1) if session else \"unknown\"}')
romans = 'triggered' in content and 'Romans' in content
print(f'Romans 8:1 fired  : {romans}')
print(f'John 4:24 fired   : {\"John\" in content and \"4\" in content and \"24\" in content}')
print(f'Genesis 1:1 fired : {\"Genesis\" in content and \"1\" in content}')
"
```

**Paste exact output into RESULTS LOG → PHASE 0 before continuing.**

---

## PHASE 1 — ADD text_buffer_depth TO config.ini

**Single change. One value added. Nothing else.**

Open `config.ini`. In the `[audio]` section, add exactly this line:

```ini
[audio]
sample_rate = 16000
chunk_seconds = 3
overlap_seconds = 0.0
channels = 1
input_device_index = 0
max_queue_size = 2
text_buffer_depth = 2
```

`text_buffer_depth = 2` means: combine the current transcript with the 1 previous
transcript before running detection. Total context = 6 seconds of speech.
This is enough to catch a verse reference split across exactly one chunk boundary.

**Gate 1:**
```powershell
python -c "
import configparser
c = configparser.ConfigParser()
c.read('config.ini')
depth = c.get('audio', 'text_buffer_depth')
overlap = c.get('audio', 'overlap_seconds')
assert depth == '2', f'text_buffer_depth wrong: {depth}'
assert float(overlap) == 0.0, f'overlap must be 0.0, got: {overlap}'
print(f'PASS: text_buffer_depth = {depth}, overlap_seconds = {overlap}')
"
```

**No benchmark needed here — this is config only. Gate must pass before Phase 2.**

---

## PHASE 2 — IMPLEMENT TRANSCRIPT BUFFER IN main.py

This is the core change. Read the full spec before writing a single line.

### What the change replaces

The current pipeline sends individual chunk transcripts directly to detection:
```
audio_chunk → transcribe → detect(transcript) → output
```

The new pipeline adds a text buffer between transcribe and detect:
```
audio_chunk → transcribe → text_buffer.append() → detect(buffer.joined) → output
```

### Exact implementation spec

**Add this import at the top of main.py:**
```python
from collections import deque
```

**Add this near the top of the processing thread setup (read depth from config):**
```python
text_buffer_depth = int(config.get('audio', 'text_buffer_depth', fallback='2'))
transcript_buffer = deque(maxlen=text_buffer_depth)
logger.info("Transcript buffer initialised: depth=%d (%.0fs context)",
            text_buffer_depth,
            text_buffer_depth * float(config.get('audio', 'chunk_seconds')))
```

**In the processing loop, replace the detection call with this pattern:**

```python
def process_loop(audio_queue, config, running_flag):
    """
    Main processing loop. Reads audio chunks from the queue, transcribes
    each chunk exactly once (no audio reprocessing), appends the transcript
    to a rolling text buffer, and runs detection on the combined buffer text.

    Cross-chunk verse references (e.g. 'Romans' in chunk N, '8:1' in chunk N+1)
    are caught because the combined buffer contains both chunks as a single string.

    Args:
        audio_queue:   queue.Queue of numpy float32 audio chunks.
        config:        ConfigParser object with all settings.
        running_flag:  threading.Event — clear to stop the loop.
    """
    text_buffer_depth = int(config.get('audio', 'text_buffer_depth', fallback='2'))
    transcript_buffer = deque(maxlen=text_buffer_depth)
    cooldown_tracker = {}
    cooldown_seconds = float(config.get('detection', 'cooldown_seconds', fallback='8'))

    while running_flag.is_set():
        try:
            chunk = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # ── Step 1: Transcribe new audio ONCE ──────────────────────────────
        t_start = time.time()
        new_text = transcribe_chunk(chunk).strip()
        t_transcribe = time.time() - t_start

        if not new_text:
            logger.debug("Empty transcript — skipping")
            continue

        logger.info("Transcript: '%s'  (%.2fs)", new_text, t_transcribe)

        # ── Step 2: Add to text buffer ──────────────────────────────────────
        # This is O(1) string append — essentially free.
        # Do NOT re-run Whisper on previous chunks. The text is already here.
        transcript_buffer.append(new_text)

        # ── Step 3: Combine buffer for detection ───────────────────────────
        # If depth=2: combined = "previous_chunk_text current_chunk_text"
        # A verse split across the boundary is now a single string.
        combined_text = ' '.join(transcript_buffer)
        logger.debug("Combined buffer (%d chunks): '%s'", len(transcript_buffer), combined_text)

        # ── Step 4: Detect ─────────────────────────────────────────────────
        result = detect_explicit(combined_text)
        source = 'regex'
        if result is None:
            result = search_paraphrase(combined_text)
            source = 'vector'

        if result is None:
            print('{"triggered": false}', flush=True)
            continue

        # ── Step 5: Cooldown check ─────────────────────────────────────────
        verse_key = (result.get('book', ''), result.get('chapter', 0), result.get('verse', 0))
        now = time.time()
        last_trigger = cooldown_tracker.get(verse_key, 0)
        if now - last_trigger < cooldown_seconds:
            logger.debug("Cooldown active for %s — suppressing", verse_key)
            print('{"triggered": false}', flush=True)
            continue

        # ── Step 6: DB lookup and output ───────────────────────────────────
        verse_data = get_verse(result['book'], result['chapter'], result.get('verse'))
        if verse_data:
            cooldown_tracker[verse_key] = now
            latency = time.time() - t_start
            output = {**verse_data, 'triggered': True, 'source': source,
                      'confidence': result.get('score', 1.0)}
            print(json.dumps(output), flush=True)
            logger.info("TRIGGERED: %s %d:%d via %s (latency %.2fs)",
                        result['book'], result.get('chapter', 0),
                        result.get('verse', 0), source, latency)
        else:
            logger.warning("DB lookup failed for %s", result)
            print('{"triggered": false}', flush=True)
```

### Gate 2-A: Syntax check

```powershell
python -c "import main; print('PASS: main.py imports without error')"
```

Must print `PASS` with no traceback.

### Gate 2-B: Verify buffer depth in startup log

```powershell
python main.py --test-file tests/test_audio.wav 2>&1 | head -20
```

Must contain a line like:
```
Transcript buffer initialised: depth=2 (6s context)
```

If this line is absent, the buffer code did not run. Fix before continuing.

### Gate 2-C: Full pipeline test

```powershell
python main.py --test-file tests/test_audio.wav 2>&1 | tee logs/after_transcript_buffer.txt
```

**This gate passes ONLY when ALL THREE appear in the output:**
```
"book": "Romans",  "chapter": 8,  "verse": 1   ← was missing before
"book": "John",    "chapter": 4,  "verse": 24
"book": "Genesis", "chapter": 1,  "verse": 1
```

If Romans 8:1 is still missing:
1. Print the combined buffer text to check what Whisper produced:
   ```python
   logger.debug("Combined buffer: '%s'", combined_text)
   ```
   Run again with `LOG_LEVEL=DEBUG` or change log level temporarily to DEBUG.
2. If combined text contains "Romans" and "8" and "1" but regex doesn't fire,
   the regex pattern needs a looser match for the cross-chunk join.
3. If combined text does NOT contain "Romans" and "8:1" together,
   increase `text_buffer_depth` to 3 in config.ini and re-run.

Do NOT mark this gate complete until Romans 8:1 appears in the output.

---

## PHASE 3 — BENCHMARK AND CALCULATE IMPROVEMENT

Run exact same benchmark as Phase 0 but against the new build:

```powershell
python main.py --test-file tests/test_audio.wav 2>&1 | tee logs/after_v0.2.0.txt
```

Then calculate improvement:

```powershell
python -c "
import re

def parse_log(path):
    with open(path) as f:
        content = f.read()
    triggered = content.count('\"triggered\": true')
    latencies = [float(x) for x in re.findall(r'latency ([\d.]+)s', content)]
    romans = 'Romans' in content and '\"verse\": 1' in content
    return triggered, latencies, romans

before_count, before_lat, before_romans = parse_log('logs/baseline_v0.1.0.txt')
after_count,  after_lat,  after_romans  = parse_log('logs/after_v0.2.0.txt')

warm_before = [x for x in before_lat if x < 30]
warm_after  = [x for x in after_lat  if x < 30]

avg_before = sum(warm_before)/len(warm_before) if warm_before else 0
avg_after  = sum(warm_after) /len(warm_after)  if warm_after  else 0

pct = ((avg_before - avg_after) / avg_before * 100) if avg_before else 0

print('═══════════════════════════════════════')
print('  BENCHMARK COMPARISON')
print('═══════════════════════════════════════')
print(f'  Verses triggered  : {before_count} → {after_count}')
print(f'  Romans 8:1 caught : {before_romans} → {after_romans}')
print(f'  Warm avg latency  : {avg_before:.2f}s → {avg_after:.2f}s')
print(f'  Latency change    : {pct:+.1f}%')
print(f'  Accuracy change   : +{after_count - before_count} verse(s)')
print()
verdict = 'IMPROVEMENT CONFIRMED' if (after_count >= before_count and avg_after <= avg_before * 1.1) else 'REGRESSION'
print(f'  VERDICT: {verdict}')
print('═══════════════════════════════════════')
"
```

**Paste exact output into RESULTS LOG → PHASE 3 before continuing.**

---

## PHASE 4 — COMMIT OR REVERT

### If IMPROVEMENT CONFIRMED:

```powershell
git add main.py config.ini
git commit -m "feat: transcript buffer depth=2 — Romans 8:1 now caught, +1 accuracy, latency [paste %]"
git tag v0.2.0-transcript-buffer
git push origin main --tags
```

Then update the snapshot at the top of this file:
```
Phase          : COMPLETE
Versions       : v0.1.0-baseline → v0.2.0-transcript-buffer
Romans 8:1     : NOW TRIGGERED
Warm latency   : [paste new number]s
```

### If REGRESSION (worse numbers):

```powershell
git checkout v0.1.0-baseline
git checkout -b rollback-from-transcript-buffer
```

Then log exactly what went wrong in RESULTS LOG before trying anything else.

---

## PHASE 5 — FALSE POSITIVE SAFETY CHECK

After the commit, verify the transcript buffer does not create fake matches
from unrelated text being joined across chunks.

Run this isolation test:

```powershell
python -c "
from verse_detector import detect_explicit

# These cross-chunk joins must NOT trigger a false positive
false_positive_cases = [
    'John the Baptist was preaching 3 thousand people came',
    'Mark my words Genesis will come again 1 nation',
    'Romans ruled the world chapter by chapter 8 emperors',
    'the number of Acts committed was 2 verse was the answer',
    'Luke warm water 3 times a day',
]

print('FALSE POSITIVE SAFETY CHECK')
print('─' * 40)
all_safe = True
for text in false_positive_cases:
    result = detect_explicit(text)
    status = 'SAFE' if result is None else f'FALSE POSITIVE: {result}'
    if result is not None:
        all_safe = False
    print(f'{status[:60]:<60}  |  {text[:50]}')

print()
print('RESULT:', 'ALL SAFE' if all_safe else 'FALSE POSITIVES FOUND — FIX REGEX BEFORE PROCEEDING')
"
```

If any false positives are found, tighten the regex pattern in `verse_detector.py`
before marking Phase 5 complete. The fix is to require a colon, or the words
"chapter"/"verse", immediately adjacent to the digits — no nouns between book and number.

**Gate 5:** All cases return `SAFE`. Paste output into RESULTS LOG.

---

## RESULTS LOG

*All gate outputs pasted here. No phase is marked complete without an entry.*

### PHASE 0 — Baseline benchmark:
```
[paste output of baseline benchmark here]
```

### PHASE 0 — Git tag confirmation:
```
[paste output of: git tag --list]
```

### PHASE 1 — config.ini gate:
```
[paste output here]
```

### PHASE 2-A — Syntax check:
```
[paste output here]
```

### PHASE 2-B — Buffer startup log:
```
[paste first 20 lines of startup output here]
```

### PHASE 2-C — Full pipeline (three verses must fire):
```
[paste complete stdout from: python main.py --test-file tests/test_audio.wav]
```

### PHASE 3 — Benchmark comparison:
```
[paste complete benchmark comparison output here]
```

### PHASE 4 — Commit hash:
```
[paste: git log --oneline -3]
```

### PHASE 5 — False positive check:
```
[paste false positive safety check output here]
```

---

## KNOWN LIMITATIONS AT v0.2.0 (document before moving on)

After this workflow completes, record these in build_progress.md:

```
v0.1.0-baseline
  Warm latency   : ~3.5s
  Romans 8:1     : MISSED (cross-chunk split)
  John 4:24      : CAUGHT
  Genesis 1:1    : CAUGHT
  Genesis 1:26   : CAUGHT
  Audio overlap  : 0s (locked)
  Known bug      : First verse cold-start ~59s (model not pre-warmed)

v0.2.0-transcript-buffer
  Warm latency   : [fill in after Phase 3]
  Romans 8:1     : CAUGHT (transcript buffer stitches chunks)
  John 4:24      : CAUGHT
  Genesis 1:1    : CAUGHT
  Genesis 1:26   : CAUGHT
  Audio overlap  : 0s
  Remaining bug  : Cold-start penalty on first verse (next workflow)
  Architecture   : Text buffer depth=2 (6s context, ~0.002ms cost vs 3500ms audio re-transcription)
```

**The cold-start fix (model pre-warm) is the next separate workflow after this one completes.**

---

*Complete every phase gate before resuming workflow_state.md.*
*Roll back to v0.1.0-baseline at any time with: git checkout v0.1.0-baseline*

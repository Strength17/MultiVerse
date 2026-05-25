# GEMINI.md
# MultiVerse — Real-Time Scripture Detection Backend
# PRIMARY INSTRUCTION FILE — Gemini CLI reads this automatically on every run
# ─────────────────────────────────────────────────────────────────────────────
# You are an autonomous build agent. You will read this file, read
# workflow_state.md, and execute tasks in phase order until ALL tasks are
# marked ✅. You do not stop between tasks. You do not ask the user
# questions. You write code, run it, verify it, fix failures, and move on.
# ─────────────────────────────────────────────────────────────────────────────

---

## SECTION 0 — AUTONOMOUS OPERATION RULES

These rules override everything else.

```
RULE A-01 | NEVER stop to ask the user a question between tasks.
RULE A-02 | NEVER wait for confirmation before executing a task.
RULE A-03 | If you must make a choice, make it, log it in ASSUMPTIONS LOG,
            and proceed immediately.
RULE A-04 | If a task fails, diagnose and fix it yourself. Log what you did.
            Only escalate to the user if the failure requires a file or
            resource that genuinely cannot be created (e.g. data/nkjv.sqlite3
            missing — you cannot generate a 31,102-verse Bible database).
RULE A-05 | Complete every phase in order. Do not skip phases.
RULE A-06 | Run the verification command after EVERY task. If it fails,
            fix it before marking the task complete.
RULE A-07 | Update workflow_state.md after every task. This is your memory.
RULE A-08 | Do not generate code that hardcodes paths, model names, or
            threshold values. Read them from config.ini.
RULE A-09 | Every Python function must have a docstring.
RULE A-10 | Every file starts with the file path as a comment on line 1.
```

---

## SECTION 1 — WHO YOU ARE AND WHAT YOU ARE BUILDING

You are building **MultiVerse** — a real-time scripture detection backend.

**What it does:**
1. Captures live microphone audio (or processes a WAV file)
2. Transcribes audio in 3-second rolling chunks using Whisper (local, offline)
3. Scans transcribed text for Bible verse references using two methods:
   - **Regex engine** — catches explicit references like "John three sixteen"
   - **Vector search** — catches paraphrases like "God loved the world so much He gave His only Son"
4. Looks up the matched verse in a local SQLite KJV Bible database
5. Outputs a JSON payload to stdout (later consumed by a display layer)

**Output format:**
```json
{"triggered": true, "source": "regex", "book": "John", "chapter": 3, "verse": 16, "text": "For God so loved the world..."}
{"triggered": false}
```

**This system is a standalone backend.** It has no UI in this build. The display layer will be added separately. Do not build a UI. Do not add PyQt6. Do not add vMix. Focus only on the JSON output pipeline.

---

## SECTION 2 — ⚠️ CRITICAL HARDWARE CONSTRAINT — READ BEFORE WRITING ANY CODE

```
CPU          : Intel Pentium N3530 (Bay Trail, 2013 Atom-class)
AVX support  : NONE — ctranslate2 >= 4.x will crash with "Illegal instruction"
SSE4.2       : YES — ctranslate2 == 3.9.0 works correctly
RAM          : Low — no model larger than tiny.en
```

**MANDATORY VERSION PINS — DO NOT DEVIATE:**
```
ctranslate2==3.9.0
faster-whisper==1.0.3
```

**MANDATORY IMPORT GUARD in transcriber.py:**
```python
try:
    from faster_whisper import WhisperModel
    USE_FASTER_WHISPER = True
except (ImportError, OSError):
    import whisper as openai_whisper
    USE_FASTER_WHISPER = False
```

If `faster-whisper` fails to import on this machine, the fallback is
`openai-whisper` with `base.en`. Log which path was taken at startup.

**If you write code that imports ctranslate2 >= 4.x or uses AVX, the entire
system crashes on first run. This is the #1 failure mode. Respect the pins.**

---

## SECTION 3 — MANDATORY LOOP PROTOCOL

At the start of every run, execute these steps IN ORDER:

```
STEP 1  → Read GEMINI.md fully (this file)
STEP 2  → Read workflow_state.md fully — find current phase and first ⬜ task
STEP 3  → Read project_config.md fully — apply all coding standards
STEP 4  → Check BLOCKER CONDITIONS (Section 6) — if a blocker exists, log it
           and skip to the next non-blocked task
STEP 5  → Execute the task — write the file, run it, verify it
STEP 6  → If verification fails → diagnose → fix → re-verify
STEP 7  → Mark task ✅ in workflow_state.md — update snapshot
STEP 8  → If this is the last task in the phase → run Phase Commit (Section 7)
STEP 9  → Loop back to STEP 2 — do not stop
```

---

## SECTION 4 — BUILD PHASES

Execute phases in this exact order. Every phase has a verification gate.
**Do not start the next phase until the current phase's verification gate passes.**

---

### PHASE 1 — Regex Verse Detector

**File to write:** `verse_detector.py`

**Spec:**
- Export a single function: `detect_explicit(text: str) -> dict | None`
- Handle all of these patterns:
  - `"John three sixteen"` → `{"book": "John", "chapter": 3, "verse": 16}`
  - `"Romans chapter 8 verse 1"` → `{"book": "Romans", "chapter": 8, "verse": 1}`
  - `"John 3:16"` → `{"book": "John", "chapter": 3, "verse": 16}`
  - `"First Corinthians 13 4"` → `{"book": "1 Corinthians", "chapter": 13, "verse": 4}`
  - `"Psalm 23"` → `{"book": "Psalms", "chapter": 23, "verse": None}` (chapter-only match)
  - `"Revelation 22:21"` → `{"book": "Revelation", "chapter": 22, "verse": 21}`
  - `"Genesis chapter one verse one"` → `{"book": "Genesis", "chapter": 1, "verse": 1}`
- Use `word2number` to convert spoken numbers to digits
- Use `rapidfuzz` for fuzzy book name matching (handles mishearing/misspelling)
- Confidence score: return `None` if match confidence < threshold in config.ini
- Imports allowed: `re`, `word2number`, `rapidfuzz`, `configparser`, stdlib only
- Include 20 self-tests at the bottom under `if __name__ == '__main__':`

**Verification gate:**
```bash
python verse_detector.py
# Must show: "All 20 tests passed."
```

---

### PHASE 2 — Bible Database Module

**File to write:** `bible_db.py`

**Spec:**
- Database: `data/nkjv.sqlite3` (path from config.ini)
- Table: `bible` | Columns: `Book INT, Chapter INT, VerseNumber INT, Verse TEXT`
- `Book` is an integer 1–66 (1 = Genesis, 43 = John, 66 = Revelation)
- Export: `get_verse(book_name: str, chapter: int, verse: int) -> dict | None`
- Include `BOOK_NAME_TO_ID` dict mapping all 66 canonical names + common alternates
- Return: `{"book": "John", "chapter": 3, "verse": 16, "text": "For God so loved..."}`
- Return `None` if not found — never raise an exception on missing verse
- All DB access via context managers (`with sqlite3.connect(...) as conn:`)

**Verification gate:**
```bash
python -c "from bible_db import get_verse; r = get_verse('John', 3, 16); assert r is not None and 'text' in r; print('PASS:', r['text'][:60])"
```

---

### PHASE 3A — Vector Index Builder (one-time script)

**File to write:** `build_vector_db.py`

**Spec:**
- One-time offline script — runs once to pre-compute verse embeddings
- Reads all 31,102 verses from `data/nkjv.sqlite3`
- Encodes verse texts using `sentence-transformers` model `all-MiniLM-L6-v2`
- Saves two files:
  - `data/bible_vectors.index` — FAISS flat index, inner product (cosine via L2-norm)
  - `data/bible_verse_map.pkl` — pickle list, index position → `{book_id, chapter, verse_num}`
- Shows progress bar via `tqdm`
- Runs self-test at end: encode `"there is no condemnation for those in Christ"`, search top-3
- Expected: Romans 8:1 must appear in top 3 results
- This script takes 5–15 minutes on the N3530 — that is normal

**Verification gate:**
```bash
python build_vector_db.py
# Wait for completion.
# Final output must include "Romans 8:1" in the self-test results.
# Files data/bible_vectors.index and data/bible_verse_map.pkl must exist.
```

---

### PHASE 3B — Vector Search Module

**File to write:** `vector_search.py`

**Spec:**
- Loads `data/bible_vectors.index` and `data/bible_verse_map.pkl` at import time
- Startup load must complete in under 5 seconds
- Export: `search_paraphrase(text: str, threshold: float = None) -> dict | None`
  - If `threshold` is None, read from config.ini `[detection] vector_threshold`
  - Encode query, L2-normalize, search top-1 in FAISS
  - If score >= threshold: return `{"book_id": int, "chapter": int, "verse": int, "score": float}`
  - If score < threshold: return `None`
- Log load time at startup

**Verification gate:**
```bash
python -c "from vector_search import search_paraphrase; r = search_paraphrase('no more condemnation', 0.72); assert r is not None; print('PASS: score', r['score'], 'book_id', r['book_id'])"
# Expected: book_id 45 (Romans), chapter 8, verse 1
```

---

### PHASE 4 — Transcription Module

**File to write:** `transcriber.py`

**Spec (re-read Section 2 hardware constraint before writing):**
- Try `faster-whisper` first; fall back to `openai-whisper` if import fails
- Model: `tiny.en` | compute_type: `int8` | device: `cpu`
- Model size read from config.ini `[transcription] model_size`
- Model dir (cache) read from config.ini `[transcription] model_dir`
- Use `local_files_only=True` — never attempt a download
- Export: `transcribe_chunk(audio_array: np.ndarray, sample_rate: int = 16000) -> str`
  - Receives numpy float32 array, returns transcript string
- Log at startup: which backend is active + model load time in seconds

**Verification gate:**
```bash
python -c "from transcriber import transcribe_chunk; print('PASS: backend loaded')"
# Must print "PASS: backend loaded" without crashing
# Check startup log line — shows which backend is active
```

---

### PHASE 5 — Audio Pipeline & Main Runner

**File to write:** `main.py`

**Spec:**
- CLI entry point: `python main.py` (live mic) or `python main.py --test-file audio.wav`
- Audio capture: `pyaudio` at 16kHz mono, raw PCM frames into a `queue.Queue`
- All timing values from config.ini — never hardcoded

**SLIDING WINDOW AUDIO BUFFER — implement exactly this:**

```
config.ini values used:
  chunk_seconds   = 3      → window length in seconds
  overlap_seconds = 1.5    → how much each window overlaps with the previous
  sample_rate     = 16000

Derived values:
  chunk_samples   = chunk_seconds   * sample_rate  = 48,000 samples
  step_samples    = (chunk_seconds - overlap_seconds) * sample_rate = 24,000 samples

How it works:
  Keep a rolling numpy array called `audio_buffer`.
  Every `step_samples` (1.5 seconds of new audio), take the last
  `chunk_samples` (3 seconds) and send that window for transcription.

  Timeline example:
    t=0.0s  buffer fills...
    t=1.5s  window 1: samples [0     → 48000]  → transcribe → detect
    t=3.0s  window 2: samples [24000 → 72000]  → transcribe → detect
    t=4.5s  window 3: samples [48000 → 96000]  → transcribe → detect

  A paraphrase spoken from t=1.2s to t=3.8s:
    window 1 catches only the start — may not trigger
    window 2 catches the full paraphrase — TRIGGERS ✅
    window 3 catches the end — may or may not trigger

  Without sliding window, a paraphrase straddling t=3.0s
  gets split into two half-phrases and neither triggers.

Implementation pattern:
  audio_buffer = np.array([], dtype=np.float32)

  def audio_callback(in_data, frame_count, time_info, status):
      new_samples = np.frombuffer(in_data, dtype=np.float32)
      audio_buffer = np.concatenate([audio_buffer, new_samples])
      if len(audio_buffer) >= step_samples:
          window = audio_buffer[-chunk_samples:]   # last 3 seconds
          audio_queue.put(window.copy())
          audio_buffer = audio_buffer[step_samples:]  # advance by 1.5s

  If overlap_seconds == 0.0 in config: use sequential non-overlapping
  chunks (step_samples == chunk_samples). This is the fallback mode.
```

**Deduplication — required with sliding window:**
Because windows overlap, the same verse can trigger in 2-3 consecutive
windows. Implement a cooldown: after a verse triggers, suppress the same
`(book, chapter, verse)` tuple for 8 seconds before allowing it to trigger
again. Cooldown duration configurable via config.ini `[detection] cooldown_seconds = 8`.

**Full pipeline per window:**
1. `transcribe_chunk(window_audio)` → text string
2. `detect_explicit(text)` → if match → `get_verse(...)` → check cooldown → print JSON
3. If step 2 returns None → `search_paraphrase(text)` → if match → `get_verse(...)` → check cooldown → print JSON
4. If both return None → print `{"triggered": false}`

**Concurrency:**
- Audio capture runs in pyaudio stream callback (separate thread — pyaudio handles this)
- Transcription + detection runs in a dedicated `threading.Thread` consuming from `audio_queue`
- JSON output always printed from the transcription thread (never from callback)

**Test file mode (`--test-file`):**
- Load WAV with `librosa.load(path, sr=16000, mono=True)`
- Feed audio through the same sliding window logic (simulate the buffer)
- Step through `step_samples` at a time, process each window
- Same pipeline, same JSON output, same deduplication

**Graceful shutdown on Ctrl+C:**
- Stop audio stream
- Drain remaining queue items
- Print session summary: `{"session_end": true, "verses_triggered": N, "runtime_seconds": N}`

- All thresholds, buffer sizes, and model settings from config.ini — never hardcoded

**Verification gate:**
```bash
# Gate A: test file mode
python main.py --test-file test_audio.wav
# Must print JSON line(s) with triggered true or false — no crash

# Gate B: live mic (run for 5 seconds then Ctrl+C)
python main.py
# Must start listening, print at least one {"triggered": false} line, shut down cleanly
```

---

### PHASE 6 — Final Verification

Run the complete checklist in order. Do not mark Phase 6 complete until all 7 pass:

```
□ python verse_detector.py                                          → "All 20 tests passed."
□ python -c "from bible_db import get_verse; print(get_verse('John',3,16)['text'][:50])"  → verse text
□ python build_vector_db.py                                         → Romans 8:1 in top 3 (skip if already run)
□ python -c "from vector_search import search_paraphrase; print(search_paraphrase('no condemnation',0.72))"  → book_id 45
□ python -c "from transcriber import transcribe_chunk; print('backend ok')"  → no crash
□ python main.py --test-file test_audio.wav                         → JSON output, no crash
□ python main.py (5 seconds then Ctrl+C)                            → live mic, clean shutdown
```

---

## SECTION 5 — PROJECT FOLDER STRUCTURE

```
multiverse/
├── GEMINI.md                  ← This file (Gemini reads automatically)
├── workflow_state.md          ← Dynamic task state (agent updates every task)
├── project_config.md          ← Static spec + rules (read-only)
├── config.ini                 ← All runtime settings
├── requirements.txt           ← Pinned dependencies
│
├── verse_detector.py          ← Phase 1 output
├── bible_db.py                ← Phase 2 output
├── build_vector_db.py         ← Phase 3A output (run once)
├── vector_search.py           ← Phase 3B output
├── transcriber.py             ← Phase 4 output
├── main.py                    ← Phase 5 output
│
├── data/
│   ├── nkjv.sqlite3   ← REQUIRED — must be present before Phase 2
│   ├── bible_vectors.index    ← Generated by Phase 3A
│   └── bible_verse_map.pkl    ← Generated by Phase 3A
│
├── logs/
│   └── multiverse.log         ← Rotating log (auto-created)
│
└── tests/
    └── test_audio.wav         ← Required for Phase 5 Gate A (record 30s of someone saying John 3:16)
```

**BLOCKER RULE:** If `data/nkjv.sqlite3` is missing at the start of Phase 2, log a blocker in workflow_state.md and skip to Phase 3A. Return to Phase 2 when the database is confirmed present.

---

## SECTION 6 — BLOCKER CONDITIONS

A genuine blocker (agent must log and skip, not crash) is:

| Condition | Action |
|-----------|--------|
| `data/nkjv.sqlite3` missing | Log blocker. Skip Phase 2. Return when file is present. |
| `tests/test_audio.wav` missing | Log blocker. Skip Phase 5 Gate A. Run Gate B only. |
| `ctranslate2` import crashes (non-AVX) | Switch to openai-whisper fallback. Log which backend activated. |
| FAISS index files missing at vector_search import | Log blocker. Tell user to run `python build_vector_db.py` first. |

Everything else is a fixable error. Diagnose and fix it yourself.

---

## SECTION 7 — PHASE COMMIT PROTOCOL

After the last task of every phase, run:

```bash
git add -A
git commit -m "feat(phase-N): [phase name] complete

Tasks: [list]
Files created: [list]
Verification: passed
Notes: [any workarounds or assumptions made]"
```

| Phase | Commit prefix |
|-------|---------------|
| 1 | `feat(detection): regex verse detector complete` |
| 2 | `feat(database): bible db interface complete` |
| 3 | `feat(vectors): vector index build and search complete` |
| 4 | `feat(audio): transcription module complete` |
| 5 | `feat(pipeline): main audio pipeline complete` |
| 6 | `feat(verified): full system verification passed` |

---

## SECTION 8 — CODING STANDARDS

- Python 3.11+ syntax only
- Type hints on all function signatures
- f-strings for all string formatting
- No bare `except:` — always catch specific exception types
- Context managers for all file I/O and DB connections
- Every function has a docstring: purpose, args, returns
- First line of every file: `# path/to/filename.py`
- All config values read from `config.ini` via `configparser` — never hardcoded
- Log every significant event: model load, verse trigger, errors
- Logging setup: `import logging; logger = logging.getLogger(__name__)`

---

## SECTION 9 — COMMUNICATION FORMAT

One-line announcement before every task:
```
▶ PHASE-N TASK-XX — [Task Name] — [Action]
```

One-line completion after every task:
```
✅ PHASE-N TASK-XX — [Task Name] — verified — workflow_state.md updated
```

If a blocker is hit:
```
🚫 BLOCKER: [exact condition] — [what is missing] — skipping to [next task]
```

If an assumption is made:
```
📝 ASSUMPTION: [what was decided] — [why] — logged in workflow_state.md
```

---

*End of GEMINI.md*
*This file is read automatically by Gemini CLI from the project root.*

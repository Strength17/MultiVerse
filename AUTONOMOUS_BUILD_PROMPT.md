# AUTONOMOUS BUILD PROMPT
# MultiVerse v2.1.0 — Whisper-Only Bottleneck Optimisation
# Give this entire file to your agent as the starting instruction.
# ─────────────────────────────────────────────────────────────────────────────

Read GEMINI.md fully before touching anything. Then read every word 
of this prompt before writing a single line of code or running a 
single command.

═══════════════════════════════════════════════════════════════════
OVERRIDE RULES — these take priority over GEMINI.md for this session

OVERRIDE A-01: Do NOT write to reply.md and stop under any 
circumstance during this build. reply.md is disabled for this 
session entirely.

OVERRIDE A-02: The "same condition fails twice → stop" rule does 
not exist in this session. If a condition fails more than twice, 
do not stop — try every fix in the fix sequence from the beginning 
before considering any form of escalation. The loop has no exit 
except 3 consecutive passing runs.

OVERRIDE A-03: The only valid stop condition is 3 consecutive 
passing benchmark runs where all 8 objective conditions are 
satisfied simultaneously. Nothing else stops this loop. Ever.

OVERRIDE A-04: If you are stuck on one failing condition, move 
to the next fix in the sequence, apply it, benchmark, and come 
back. You are never allowed to halt, pause, or ask a question. 
You diagnose, fix, and loop. That is all.
═══════════════════════════════════════════════════════════════════

BEFORE ANYTHING ELSE — check soundfile:

  python -c "import soundfile; print('soundfile ok')"
  
  If that fails:
    pip install soundfile
  
  This is the only external dependency not confirmed present.
  Fix it silently and proceed. Do not mention it again.

═══════════════════════════════════════════════════════════════════
OBJECTIVE — 3 consecutive passing runs required to stop.
All 8 conditions must be true simultaneously in every passing run:

  ✅ 1. Romans 8:1     detected, latency <= 10s
  ✅ 2. John 4:24      detected, latency <= 10s
  ✅ 3. Genesis 1:1    detected, latency <= 10s
  ✅ 4. Genesis 1:27   detected, latency <= 10s
  ✅ 5. Song of Solomon 1:1   NOT triggered (false positive gone)
  ✅ 6. No single latency spike > 15s on any chunk
  ✅ 7. Zero HTTP calls at startup (confirmed by absence of 
        httpx log lines)
  ✅ 8. Startup completes in under 10s total

A run PASSES only when all 8 are true.
A run FAILS if even one is false.
3 consecutive PASSES → commit, tag, stop.
Anything less → diagnose, fix, loop.
═══════════════════════════════════════════════════════════════════

CORE PRINCIPLE — burn this into every decision you make:

Whisper is the only component allowed to take time.
Everything else must be instant.

  Whisper transcription    → 3–5s per chunk (acceptable)
  Regex matching           → ~1ms  (pre-compiled patterns)
  FAISS vector search      → ~5ms  (index pre-loaded)
  Transcript buffer join   → ~0ms  (string concat)
  SQLite lookup            → ~2ms  (single indexed query)
  Queue operations         → ~0ms
  JSON print to stdout     → ~0ms
  Audio capture            → ~0ms  (own thread, never blocks)

If any non-Whisper operation exceeds 10ms that is a bug.
Find it. Fix it. Do not benchmark until it is fixed.
═══════════════════════════════════════════════════════════════════

THREADING MODEL — two threads, nothing else, no exceptions:

THREAD 1 — audio capture (pyaudio callback or file reader):
  - Produces 3-second audio windows
  - Drops windows into audio_queue(maxsize=1)
  - Drop-on-full: if queue already has a waiting chunk,
    discard the waiting chunk, insert the new one
  - NEVER waits for Thread 2
  - NEVER blocks for any reason
  - NEVER sleeps
  - Audio capture is always running, always current

THREAD 2 — processing (daemon=True, runs until shutdown):
  while running:
      window = audio_queue.get()            # wait for chunk
      t_start = time.time()

      # VAD gate — silence never reaches Whisper
      rms = float(np.sqrt(np.mean(window ** 2)))
      if rms < vad_rms_threshold:
          print(json.dumps({"triggered": False,
              "transcript": {"current": "", "tail": ""}}))
          continue

      transcript = transcribe_chunk(window)  # ONLY slow step
      transcript_buffer.append(transcript)   # instant
      text = ' '.join(transcript_buffer)     # instant

      match = detect_explicit(text)          # instant ~1ms
      if not match:
          match = search_paraphrase(text)    # instant ~5ms
      if match:
          verse = get_verse(...)             # instant ~2ms
          latency = time.time() - t_start
          print(json.dumps({
              **verse,
              "triggered": True,
              "latency_ms": int(latency * 1000),
              "transcript": {
                  "tail": ' '.join(
                      transcript_buffer[-2].split()[-8:]
                      if len(transcript_buffer) >= 2 else []),
                  "current": transcript,
                  "full_window": text
              }
          }))
          logger.info(f"TRIGGERED: {verse['book']} "
                      f"{verse['chapter']}:{verse['verse']} "
                      f"via {match['source']} "
                      f"(latency {latency:.2f}s)")
      else:
          print(json.dumps({"triggered": False,
              "transcript": {
                  "tail": ' '.join(
                      transcript_buffer[-2].split()[-8:]
                      if len(transcript_buffer) >= 2 else []),
                  "current": transcript,
                  "full_window": text
              }
          }))

NO locks. NO semaphores. NO join(). NO synchronous blocking.
NO serialisation of any kind.
The queue with maxsize=1 and drop-on-full is the ONLY 
concurrency control this system needs or will ever need.
If serialisation exists anywhere in the current code, 
remove it entirely. It kills Romans 8:1.
═══════════════════════════════════════════════════════════════════

TRANSCRIPT BUFFER — text stitching, not audio overlap:

  overlap_seconds = 0.0   ← MUST stay 0.0, never change this

  transcript_buffer = collections.deque(maxlen=2)

  Every processed chunk appends its transcript text.
  Detection always runs on ' '.join(transcript_buffer)
  
  This provides 6 seconds of text context at zero CPU cost:
    chunk N-1 text + chunk N text joined = cross-boundary 
    citations caught without reprocessing any audio.

  Why this works:
    "Genesis chapter 1 verse" ends chunk N-1
    "one in the beginning" starts chunk N
    Joined text = "Genesis chapter 1 verse one in the beginning"
    Regex fires on Genesis 1:1 ✅

  Never change overlap_seconds away from 0.0
  Never change deque maxlen below 2
  These two settings are proven and locked.
═══════════════════════════════════════════════════════════════════

WHISPER CONFIGURATION — exact values, verified at startup:

  beam_size = 1
  temperature = 0
  condition_on_previous_text = False
  fp16 = False
  language = 'en'
  initial_prompt = read from config.ini

What beam_size=1 does:
  Normal Whisper runs the neural network 5 times and picks 
  the best result. beam_size=1 runs it once and outputs 
  immediately. 30-40% faster. Accuracy loss negligible for 
  clear speech. This is the difference between 4s and 20s 
  on a spike window.

What condition_on_previous_text=False does:
  Normal Whisper carries memory of the previous chunk into 
  the next decode, adding computation overhead. With False, 
  every chunk decodes fresh with no memory cost. Faster 
  and prevents bad transcriptions from poisoning subsequent 
  chunks.

MANDATORY: Print these values to the log at startup:
  logger.info(
      f"Whisper config — beam:{beam_size} "
      f"temp:{temperature} "
      f"condition:{condition_on_previous_text} "
      f"fp16:{fp16}"
  )

If the startup log does not show these exact values, 
the config is not being read correctly. Fix it before 
running any benchmark. Do not assume — verify.
═══════════════════════════════════════════════════════════════════

STARTUP SEQUENCE — must complete in under 10s total:

Step 1 — environment variables (must be FIRST, before imports):
  import os
  os.environ['TRANSFORMERS_OFFLINE'] = '1'
  os.environ['HF_DATASETS_OFFLINE'] = '1'
  
  These must be set before sentence_transformers or 
  huggingface_hub are imported. If set after, they have 
  no effect and HTTP calls will still fire.
  Verify by confirming zero httpx log lines on startup.

Step 2 — FAISS + sentence-transformers load:
  Target: under 5s (previously achieved 2.37s)
  If it exceeds 5s the env vars are not active — 
  it is making HTTP calls. Fix Step 1 first.

Step 3 — Whisper model load:
  Target: under 4s (previously achieved 3.20s)
  local_files_only = true must be set in config.ini

Step 4 — pre-warm both models (eliminates cold-start spikes):

  # Pre-warm Whisper — first inference is always slow,
  # do it now with silence so the first real chunk is fast
  import numpy as np
  _dummy_audio = np.zeros(16000, dtype=np.float32)
  transcribe_chunk(_dummy_audio)
  logger.info("Whisper pre-warmed")

  # Pre-warm sentence-transformers embedding model
  search_paraphrase("God so loved the world")
  logger.info("Embedding model pre-warmed")

Step 5 — startup confirmation log:
  logger.info("══════════════════════════════════")
  logger.info("MultiVerse v2.1.0 ready")
  logger.info(f"Whisper: beam=1 temp=0 condition=False")
  logger.info(f"Vector threshold: 0.70")
  logger.info(f"Transcript buffer: depth=2")
  logger.info(f"Overlap: 0.0s (text buffer active)")
  logger.info(f"VAD threshold: 0.015")
  logger.info(f"HTTP calls: 0")
  logger.info("══════════════════════════════════")
═══════════════════════════════════════════════════════════════════

CONFIG.INI — write these exact values:

  [audio]
  sample_rate = 16000
  chunk_seconds = 3
  overlap_seconds = 0.0
  max_queue_size = 1
  channels = 1
  input_device_index = 0
  vad_rms_threshold = 0.015

  [transcription]
  model_size = tiny.en
  beam_size = 1
  temperature = 0
  condition_on_previous_text = false
  fp16 = false
  local_files_only = true
  initial_prompt = Romans 8:1. John 3:16. Genesis 1:1. John 4:24. In spirit and in truth. God created man in his image. No condemnation in Christ Jesus.

  [detection]
  vector_threshold = 0.70
  regex_threshold = 0.75
  cooldown_seconds = 8

  [database]
  db_path = data/NKJV.SQLite3
  translation = NKJV

  [vectors]
  index_path = data/bible_vectors.index
  verse_map_path = data/bible_verse_map.pkl
  embedding_model = all-MiniLM-L6-v2

  [logging]
  log_dir = logs
  log_level = INFO
  max_bytes = 5242880
  backup_count = 3

  [output]
  transcript_tail_words = 8
═══════════════════════════════════════════════════════════════════

NON-WHISPER PERFORMANCE — verify once, log results, never revisit:

These must all be true before any benchmark is run.
Check each one. Fix any that fail. Log the result.

  □ REGEX: patterns pre-compiled at module level with 
    re.compile() — NOT compiled inside detect_explicit()
    on every call. If compiled inside the function, move 
    them to module level immediately.

  □ FAISS INDEX: loaded once in module-level code in 
    vector_search.py — NOT inside search_paraphrase().
    If loaded inside the function, move to module level.

  □ SENTENCE-TRANSFORMER MODEL: loaded once at module 
    level — NOT inside search_paraphrase(). Same fix.

  □ TRANSCRIPT BUFFER: only one operation per chunk —
    buffer.append(transcript). No sorting, no 
    deduplication, no iteration over buffer contents 
    beyond the join.

  □ SQLITE: uses context manager per query:
    with sqlite3.connect(db_path) as conn:
    NOT a persistent open connection.

  □ JSON OUTPUT: print(json.dumps(...)) only —
    no file writes in the hot path, no logging 
    of the JSON payload itself.

  □ SOUNDFILE: import soundfile before librosa in main.py
    The PySoundFile warning must not appear in any run.
    If it appears: pip install soundfile, add import.
═══════════════════════════════════════════════════════════════════

FIX SEQUENCE — if objective not met, apply in this order.
One fix at a time. Benchmark after each. Never stack two fixes.

Before Fix 1: run benchmark, save to logs/pre_fix_baseline.txt
Record: which verses fired, each latency, total runtime,
        queue warnings, startup time, HTTP call count.

FIX 1 — config.ini
  Confirm all values match the config spec above exactly.
  Pay special attention to:
    overlap_seconds = 0.0
    vector_threshold = 0.70
    beam_size = 1
    temperature = 0
    condition_on_previous_text = false
  Benchmark → logs/fix1.txt
  Expected result: Genesis 1:1 present, no HTTP calls.

FIX 2 — main.py threading
  Confirm two-thread model is active exactly as specified.
  If serialisation exists anywhere — remove it entirely.
  Confirm audio_queue maxsize=1 with drop-on-full logic.
  Confirm Thread 2 is daemon=True.
  Confirm Thread 1 never waits for Thread 2.
  Benchmark → logs/fix2.txt
  Expected result: Romans 8:1 latency drops below 15s.

FIX 3 — transcriber.py
  Confirm transcribe() call passes all 4 parameters:
    beam_size, temperature, condition_on_previous_text, fp16
  Read values from config.ini — do not hardcode them.
  Add startup log line confirming all 4 values.
  Benchmark → logs/fix3.txt
  Expected result: no single chunk latency > 15s.

FIX 4 — pre-warm
  Confirm both pre-warm calls exist in startup sequence.
  Whisper pre-warm: np.zeros(16000) dummy transcription.
  Embedding pre-warm: search_paraphrase("God so loved the world")
  Both must complete before first real audio window is processed.
  Benchmark → logs/fix4.txt
  Expected result: first verse latency consistent with others.

FIX 5 — VAD gate
  Confirm RMS check exists before audio_queue.put()
  threshold = float(config['audio']['vad_rms_threshold'])
  Windows below threshold never enter queue, never hit Whisper.
  Benchmark → logs/fix5.txt
  Expected result: total runtime decreases, silence skipped.

FIX 6 — soundfile + librosa
  pip install soundfile (if not already installed)
  import soundfile before import librosa in main.py
  Benchmark → logs/fix6.txt
  Expected result: PySoundFile warning gone.

FIX 7 — Song of Solomon false positive
  If still firing: the _has_book_context gate must require 
  a recognised book name OR verified book memory hit within 
  the last 5 seconds before any digit sequence can trigger 
  regex detection. Bare digits ("1 was 1") must never match 
  without a book name present in the same or previous window.
  Benchmark → logs/fix7.txt
  Expected result: Song of Solomon never appears.

After Fix 7 — if any objective condition still fails:
  Start the fix sequence again from Fix 1.
  Something changed while applying later fixes.
  Find what regressed and revert it.
  The loop does not end until 3 consecutive passes.
═══════════════════════════════════════════════════════════════════

BENCHMARK PROTOCOL — run after every single fix:

  python main.py --test-file tests/test_audio.wav

Record from output — every field, every run:
  - Startup time (launch to "MultiVerse v2.1.0 ready")
  - HTTP calls (count of httpx log lines — must be 0)
  - Which verses triggered (list all by name)
  - Latency for each verse individually (from log)
  - Total runtime (from session_end JSON line)
  - Any chunk latency > 10s (note transcript text)
  - Queue-full warning count
  - PySoundFile warning present? yes/no

Log to build_progress.md after every run in this format:
  RUN N | fixes applied: [list] | 
  triggers: Romans Xs / John Xs / Gen1:1 Xs / Gen1:27 Xs |
  runtime: Xs | spikes: N | queue warns: N | HTTP: N |
  PASS/FAIL | conditions failed: [list if fail]

Calculate and log % change vs previous run:
  latency improvement = ((prev - current) / prev) * 100
  Log as: "Avg latency: +N% improvement" or 
          "N% regression — investigating"
═══════════════════════════════════════════════════════════════════

LOOP PROTOCOL — run this loop until done:

  consecutive_passes = 0
  fix_index = 1

  LOOP:
    run benchmark
    evaluate all 8 objective conditions
    
    if all 8 pass:
      consecutive_passes += 1
      log "PASS (consecutive: N/3)"
      if consecutive_passes == 3:
        → FINAL COMMIT (see below)
        → STOP
      else:
        → run benchmark again immediately
    
    else:
      consecutive_passes = 0
      identify which conditions failed
      log exact failure reason per condition
      apply next fix in sequence
      fix_index moves forward
      if fix_index > 7: fix_index = 1 (restart sequence)
      → run benchmark again

  There is no other exit from this loop.
  The loop runs until 3 consecutive passes.
  The loop never stops for any other reason.
═══════════════════════════════════════════════════════════════════

FINAL COMMIT — only after 3 consecutive passes:

  git add -A
  git commit -m "perf: Whisper-only bottleneck, all else instant

  Romans 8:1:   Xs avg (3 runs)
  John 4:24:    Xs avg
  Genesis 1:1:  Xs avg
  Genesis 1:27: Xs avg
  Startup:      Xs
  HTTP calls:   0
  Runtime:      Xs avg
  Consecutive passes: 3/3

  beam=1 temp=0 condition=False fp16=False
  VAD=0.015 threshold=0.70
  transcript buffer depth=2 overlap=0.0
  two-thread model, queue maxsize=1 drop-on-full"

  git tag v2.1.0-stable

Then write final summary to build_progress.md:
  - All latencies (min, max, avg across 3 passing runs)
  - Each fix applied and its % improvement
  - Final pass rate
  - Confirmation: "v2.1.0-stable tagged. Build complete."

Then stop. The job is done.
═══════════════════════════════════════════════════════════════════

FINAL REMINDER:

You do not stop until v2.1.0-stable is tagged.
You do not ask questions.
You do not write to reply.md.
You do not wait for confirmation.
You fix, benchmark, log, loop.
The objective is the only thing that ends this session.


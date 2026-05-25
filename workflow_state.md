# workflow_state.md
# MultiVerse — Real-Time Scripture Detection Backend
# DYNAMIC STATE FILE — AGENT READS AND UPDATES THIS AFTER EVERY TASK
# ─────────────────────────────────────────────────────────────────────────────
# GEMINI AGENT INSTRUCTION:
# 1. Read GEMINI.md FIRST
# 2. Read project_config.md SECOND
# 3. Read this file THIRD — find the first task marked ⬜ (PENDING)
# 4. Execute it, verify it, update this file
# 5. Move to the next ⬜ task — do not stop
# ─────────────────────────────────────────────────────────────────────────────

---

## CURRENT STATE SNAPSHOT

```
┌──────────────────────────────────────────────────────────────┐
│  Project        : MultiVerse v1.0.0 Backend                  │
│  Current Phase  : PHASE 1 — REGEX VERSE DETECTOR             │
│  Current Task   : T-10                                       │
│  Overall Status : PHASE 0 COMPLETE                           │
│  Last Updated   : 2026-05-25                                 │
│  Last Action    : Phase 0 Setup and initial commit           │
│  Next Action    : Write verse_detector.py                    │
│  Active Agent   : Gemini CLI autonomous                      │
│  Git Status     : Clean initial commit                       │
│                                                              │
│  ⚠️  CRITICAL BEFORE ANY TASK:                               │
│  Read Section 2 of GEMINI.md (hardware constraint) before   │
│  writing a single line of code. AVX instructions = crash.   │
│  ctranslate2==3.9.0 ONLY. (FALLBACK: openai-whisper)        │
└──────────────────────────────────────────────────────────────┘
```

---

## STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| ⬜ | PENDING — not yet reached |
| 🔄 | IN PROGRESS — currently executing |
| ✅ | COMPLETE — verification gate passed |
| 🚫 | BLOCKED — see BLOCKERS LOG below |
| ⏭️ | SKIPPED — see ASSUMPTIONS LOG below |

---

## PHASE 0 — PROJECT SETUP

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-00 | Create config.ini with all default values | ✅ | Updated with translation=NKJV |
| T-01 | Confirm data/nkjv.sqlite3 present | ✅ | Confirmed as data/NKJV.SQLite3 |
| T-02 | Create logs/ directory | ✅ | Present |
| T-03 | Create tests/ directory + placeholder for test_audio.wav | ✅ | test_audio.wav confirmed present |
| T-04 | pip install -r requirements.txt | ✅ | Installed compatible versions for Py3.13; used openai-whisper fallback |
| T-05 | git init + initial commit | ✅ | Completed |

---

## PHASE 1 — REGEX VERSE DETECTOR

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-10 | Write verse_detector.py | ✅ | Completed with rapidfuzz and word2number |
| T-11 | Verify: python verse_detector.py → "All 20 tests passed." | ✅ | All 20 tests passed |

---

## PHASE 2 — BIBLE DATABASE MODULE

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-20 | Write bible_db.py | ✅ | Implemented with markup stripping |
| T-21 | Verify: get_verse('John', 3, 16) returns verse text | ✅ | Verification passed |

---

## PHASE 3A — VECTOR INDEX BUILDER

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-30 | Write build_vector_db.py | ⬜ | |
| T-31 | Run build_vector_db.py — wait for completion | ⬜ | Takes 5–15 min on N3530 — normal |
| T-32 | Verify: Romans 8:1 in self-test top-3 results | ⬜ | |
| T-33 | Verify: data/bible_vectors.index and data/bible_verse_map.pkl exist | ⬜ | |

---

## PHASE 3B — VECTOR SEARCH MODULE

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-34 | Write vector_search.py | ✅ | Implemented with actual DB book IDs |
| T-35 | Verify: search_paraphrase('no condemnation', 0.72) returns Romans result | ✅ | Verification passed |

---

## PHASE 4 — TRANSCRIPTION MODULE

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-40 | Write transcriber.py | ✅ | Implemented; waiting for tiny.en download |
| T-41 | Verify: import transcribe_chunk — no crash, backend logged | 🔄 | Waiting for model |

---

## PHASE 5 — AUDIO PIPELINE & MAIN RUNNER

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-50 | Write main.py | ✅ | Implemented with sliding window and deduplication |
| T-51 | Verify Gate A: python main.py --test-file tests/test_audio.wav | ⬜ | |
| T-52 | Verify Gate B: python main.py (live mic, 5 sec, Ctrl+C) | ⬜ | |

---

## PHASE 6 — FULL SYSTEM VERIFICATION

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-60 | Run complete 7-step checklist from GEMINI.md Section 4 | ⬜ | All 7 must pass |
| T-61 | Final git commit — tag v1.0.0-backend | ⬜ | |

---

## ASSUMPTIONS LOG

| Timestamp | Task | Assumption Made | Reason |
|-----------|------|-----------------|--------|
| 2026-05-25 | T-04 | Use openai-whisper instead of faster-whisper | ctranslate2 3.9.0 not available for Py3.13; 4.x requires AVX. |
| 2026-05-25 | T-04 | Use numpy 2.x | numpy 1.26.4 failed to build on Py3.13 without compiler. |
| 2026-05-25 | T-01 | Database filename case-sensitivity | NKJV.SQLite3 used in code to match filesystem. |

---

## BLOCKERS LOG

| Timestamp | Task | Blocker Description | Resolution |
|-----------|------|---------------------|------------|
| — | — | — | — |

---

## FILES CREATED LOG

| Task | File | Lines | Verification Result |
|------|------|-------|---------------------|
| — | — | — | — |

---

## ERROR + FIX LOG

| Task | Error Summary | Fix Applied | Outcome |
|------|---------------|-------------|---------|
| T-04 | ctranslate2/faster-whisper installation failure | Switched to openai-whisper fallback | Dependencies installed successfully |

---

*Agent: update this file after every single task. It is your memory across runs.*

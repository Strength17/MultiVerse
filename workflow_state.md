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
│  Current Task   : T-01                                       │
│  Overall Status : NOT STARTED                                │
│  Last Updated   : —                                          │
│  Last Action    : —                                          │
│  Next Action    : Write verse_detector.py                    │
│  Active Agent   : Gemini CLI autonomous                      │
│  Git Status     : Init required                              │
│                                                              │
│  ⚠️  CRITICAL BEFORE ANY TASK:                               │
│  Read Section 2 of GEMINI.md (hardware constraint) before   │
│  writing a single line of code. AVX instructions = crash.   │
│  ctranslate2==3.9.0 ONLY.                                    │
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
| T-00 | Create config.ini with all default values | ⬜ | See project_config.md Section 3 |
| T-01 | Confirm data/nkjv.sqlite3 present | ⬜ | If missing → log BLOCKER, continue to Phase 1 |
| T-02 | Create logs/ directory | ⬜ | Auto-create in code if not present |
| T-03 | Create tests/ directory + placeholder for test_audio.wav | ⬜ | Log blocker if WAV absent; Phase 5 Gate A skipped |
| T-04 | pip install -r requirements.txt | ⬜ | Run inside venv; log any version conflicts |
| T-05 | git init + initial commit | ⬜ | |

---

## PHASE 1 — REGEX VERSE DETECTOR

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-10 | Write verse_detector.py | ⬜ | |
| T-11 | Verify: python verse_detector.py → "All 20 tests passed." | ⬜ | Fix failures before marking complete |

---

## PHASE 2 — BIBLE DATABASE MODULE

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-20 | Write bible_db.py | ⬜ | Requires data/nkjv.sqlite3 |
| T-21 | Verify: get_verse('John', 3, 16) returns verse text | ⬜ | |

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
| T-34 | Write vector_search.py | ⬜ | |
| T-35 | Verify: search_paraphrase('no condemnation', 0.72) returns Romans result | ⬜ | |

---

## PHASE 4 — TRANSCRIPTION MODULE

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-40 | Write transcriber.py | ⬜ | Re-read hardware constraint first |
| T-41 | Verify: import transcribe_chunk — no crash, backend logged | ⬜ | |

---

## PHASE 5 — AUDIO PIPELINE & MAIN RUNNER

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-50 | Write main.py | ⬜ | |
| T-51 | Verify Gate A: python main.py --test-file tests/test_audio.wav | ⬜ | Skip if test_audio.wav absent; log blocker |
| T-52 | Verify Gate B: python main.py (live mic, 5 sec, Ctrl+C) | ⬜ | |

---

## PHASE 6 — FULL SYSTEM VERIFICATION

| ID | Task | Status | Notes |
|----|------|--------|-------|
| T-60 | Run complete 7-step checklist from GEMINI.md Section 4 | ⬜ | All 7 must pass |
| T-61 | Final git commit — tag v1.0.0-backend | ⬜ | |

---

## ASSUMPTIONS LOG

*Agent fills this in as decisions are made during the run.*

| Timestamp | Task | Assumption Made | Reason |
|-----------|------|-----------------|--------|
| — | — | — | — |

---

## BLOCKERS LOG

*Agent fills this in when a blocker is hit. Skips the task and continues.*

| Timestamp | Task | Blocker Description | Resolution |
|-----------|------|---------------------|------------|
| — | — | — | — |

---

## FILES CREATED LOG

*Agent fills this in as files are created.*

| Task | File | Lines | Verification Result |
|------|------|-------|---------------------|
| — | — | — | — |

---

## ERROR + FIX LOG

*Agent fills this in when an error is encountered and resolved.*

| Task | Error Summary | Fix Applied | Outcome |
|------|---------------|-------------|---------|
| — | — | — | — |

---

*Agent: update this file after every single task. It is your memory across runs.*

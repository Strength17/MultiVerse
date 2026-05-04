# workflow_state.md
# MultiVerse — Real-Time Scripture Detection & Display System
# DYNAMIC STATE FILE — AGENT READS AND UPDATES THIS EVERY LOOP ITERATION
# ─────────────────────────────────────────────────────────────────────────────
# OPENCODE AGENT INSTRUCTION:
# 1. Read project_config.md FIRST (static cache content)
# 2. Read lessons_learned.md SECOND (apply all lessons)
# 3. Read this file THIRD (dynamic state content)
# 4. Find CURRENT PHASE and first task marked ⬜ (PENDING)
# 5. Check AGENT column — switch to @architect before writing code if needed
# 6. Check Section 12 of project_config.md for parallel group membership
# 7. After completing a task: update status, snapshot, progress bar,
#    files log, verification log
# 8. After completing the LAST task in a phase: run Phase Commit
#    (see Section 3 of project_config.md for commit format)
# 9. Never end a session without updating this file first
# ─────────────────────────────────────────────────────────────────────────────

---

## CURRENT STATE SNAPSHOT

```
┌──────────────────────────────────────────────────────────────┐
│  Project        : MultiVerse v1.0.0                          │
│  Current Phase  : PHASE 0 — Environment & Setup              │
│  Current Task   : T-09 — Write utils/logger.py               │
│  Overall Status : COMPLETE (Phase 0)                         │
│  Last Updated   : Mon May 04 2026                            │
│  Last Action    : T-09 completed — Phase 0 setup complete    │
│  Next Action    : Phase 1 — T-10 — Write core/audio_capture.py│
│  Active Agent   : @build (default)                            │
│  Active Agents  : 1 (main)                                   │
│  Git Status     : Initialised, remote set, 1 commit pushed   │
│  Last Commit    : Initial commit                             │
└──────────────────────────────────────────────────────────────┘
```

---

## STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| ⬜ | PENDING — not yet reached |
| 🔄 | IN PROGRESS — currently being worked on |
| ✅ | COMPLETE — verified against Section 10 protocol |
| 🚫 | BLOCKED — see BLOCKERS LOG |
| ❓ | AWAITING USER INPUT |
| ⏭️ | SKIPPED — documented reason in ASSUMPTIONS LOG |
| 🔀 | PARALLEL — running simultaneously with sibling tasks |

---

## PHASE 0 — ENVIRONMENT & PROJECT SETUP

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-00 | Check git/gh status → create GitHub repo → push initial files | ✅ | @build | See Section 3 of project_config.md |
| T-01 | Confirm Python 3.11+ available on target machine | ✅ | @build | Also confirm ffmpeg installed (faster-whisper req on Windows — C++ runtimes) |
| T-02 | Confirm vMix installed and version noted | ✅ | @build | vMix 24.0.0.72 confirmed |
| T-03 | Scaffold full folder structure + .gitignore | ✅ | @build | Write .gitignore from Section 3.4 |
| T-04 | Write requirements.txt with all pinned dependencies | ✅ | @build | |
| T-05 | Write config.ini with all default values | ✅ | @build | |
| T-06 | Write .env.example | ✅ | @build | |
| T-07 | Verify  and validate KJVBible_Database.db (SQLite3 Bible dataset) | ✅ | @build | File already at ./data/KJVBible_Database.db — run: sqlite3 data/KJVBible_Database.db "SELECT count(*) FROM bible;" → expect 31,102 rows. Schema: table=bible, cols=Book/Chapter/VerseNumber/Verse. KJV only. Path abstracted in config.ini [database] db_path |
| T-08 | Write data/book_names.py (all 66 books + variants) | ✅ | @build | Parallel Group B-a |
| T-09 | Write utils/logger.py (structured logging + rotation) | ✅ | @build | Parallel Group B-b |

**Phase 0 done when:** T-00 through T-09 all ✅
**Git action:** Phase commit after T-09 → `chore(setup): environment and project scaffold complete`
**Parallel opportunity:** T-08 and T-09 → spawn simultaneously (Group B)

---

## PHASE 1 — CORE ENGINE: AUDIO & TRANSCRIPTION

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-10 | Write core/audio_capture.py (sounddevice stream manager) | ⬜ | @architect | Threading — Group A-audio |
| T-11 | Write core/transcriber.py (faster-whisper wrapper) | ⬜ | @architect | Whisper integration — Group A-audio |
| T-12 | Implement Bible vocabulary injection into Whisper prompt | ⬜ | @build | Group A-audio |
| T-13 | Implement 5-second rolling chunk processing | ⬜ | @architect | Audio buffer logic — Group A-audio |
| T-14 | Write utils/number_words.py (spoken number → integer) | ⬜ | @build | |
| T-15 | Test transcription on sample audio file | ⬜ | @architect | |

**Phase 1 done when:** T-10 through T-15 all ✅
**Git action:** Phase commit after T-15 → `feat(audio): audio capture and transcription engine complete`
**Parallel opportunity:** T-10–T-13 run as Group A alongside T-23–T-26 and T-28–T-31

---

## PHASE 2 — CORE ENGINE: VERSE DETECTION

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-16 | Write core/verse_detector.py (regex pattern library) | ⬜ | @architect | Architecture decision |
| T-17 | Implement spoken reference patterns (chapter/verse) | ⬜ | @architect | Regex complexity |
| T-18 | Implement fuzzy book name matching (rapidfuzz) | ⬜ | @build | |
| T-19 | Implement confidence scoring per detection | ⬜ | @architect | Scoring logic |
| T-20 | Implement configurable confidence threshold filter | ⬜ | @build | |
| T-21 | Write tests/test_verse_detector.py (30+ test cases) | ⬜ | @build | Group C-a |
| T-22 | Write tests/test_number_words.py | ⬜ | @build | Group C-a |

**Phase 2 done when:** T-16 through T-22 all ✅, all tests passing
**Git action:** Phase commit after T-22 → `feat(detection): verse detection engine complete`
**Parallel opportunity:** T-21, T-22 alongside T-27 and T-33 (Group C)

---

## PHASE 3 — CORE ENGINE: BIBLE DATABASE

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-23 | Write core/bible_db.py (sqlite3 interface) | ⬜ | @build | Group A-db. DB path from config.ini [database] db_path. Table: bible |
| T-24 | Implement lookup by book + chapter + verse | ⬜ | @build | Group A-db. Query: SELECT Verse FROM bible WHERE Book=? AND Chapter=? AND VerseNumber=? |
| T-25 | Implement translation label display (KJV only — no switching) | ⬜ | @build | Group A-db. KJVBible_Database.db is single-translation. Multi-translation is OUT of MVP scope |
| T-26 | Implement manual search (keyword or reference string) | ⬜ | @build | Group A-db. Search in Verse TEXT column |
| T-27 | Write tests/test_bible_db.py | ⬜ | @build | Group C-b |

**Phase 3 done when:** T-23 through T-27 all ✅, all tests passing
**Git action:** Phase commit after T-27 → `feat(database): bible database interface complete (KJV only)`
**Parallel opportunity:** T-23–T-26 run as Group A alongside T-10–T-13 and T-28–T-31

---

## PHASE 4 — VMIX BRIDGE

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-28 | Write core/vmix_bridge.py (HTTP API wrapper) | ⬜ | @build | Group A-vmix |
| T-29 | Implement send_verse(text, reference, translation) | ⬜ | @build | Group A-vmix |
| T-30 | Implement clear_overlay() | ⬜ | @build | Group A-vmix |
| T-31 | Implement test_connection() → returns bool + version | ⬜ | @build | Group A-vmix |
| T-32 | Implement graceful failure (vMix offline = warn, not crash) | ⬜ | @architect | Error handling |
| T-33 | Write tests/test_vmix_bridge.py (mock HTTP calls) | ⬜ | @build | Group C-c |

**Phase 4 done when:** T-28 through T-33 all ✅
**Git action:** Phase commit after T-33 → `feat(vmix): vMix bridge complete`
**Parallel opportunity:** T-28–T-31 run as Group A alongside T-10–T-13 and T-23–T-26

---

## PHASE 5 — OPERATOR UI (PyQt6)

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-34 | Write ui/styles.py (dark theme QSS stylesheet) | ⬜ | @build | |
| T-35 | Write ui/transcript_panel.py (live scroll widget) | ⬜ | @architect | Thread-safe signals |
| T-36 | Write ui/approval_panel.py (APPROVE/DISMISS/EDIT) | ⬜ | @architect | State management |
| T-37 | Write ui/history_panel.py (session verse log) | ⬜ | @build | |
| T-38 | Write ui/manual_lookup.py (search + send widget) | ⬜ | @build | |
| T-39 | Write ui/settings_dialog.py (all config.ini settings) | ⬜ | @build | |
| T-40 | Write ui/main_window.py (full layout, panels assembled) | ⬜ | @architect | Complex wiring |
| T-41 | Implement vMix connection status indicator in header | ⬜ | @build | |
| T-42 | Implement audio device selector dropdown | ⬜ | @build | |
| T-43 | Implement translation selector dropdown | ⬜ | @build | |
| T-44 | Implement "Clear Overlay" button wired to vmix_bridge | ⬜ | @build | |
| T-45 | Implement auto-send timer (optional, configurable) | ⬜ | @architect | Timer + thread logic |
| T-46 | Wire QThread for transcription loop to UI signals | ⬜ | @architect | Race condition risk |
| T-47 | Wire verse detection output to approval_panel | ⬜ | @architect | Signal chain |

**Phase 5 done when:** T-34 through T-47 all ✅, UI runs without freezing
**Git action:** Phase commit after T-47 → `feat(ui): operator UI complete`
**No parallel in this phase** — panels depend on each other in order

---

## PHASE 6 — SESSION UTILITIES

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-48 | Write utils/session_export.py (log → .txt file) | ⬜ | @build | |
| T-49 | Implement export button in main_window | ⬜ | @build | |
| T-50 | Implement session start/stop controls | ⬜ | @architect | State machine |
| T-51 | Implement graceful shutdown (stop audio, close db, log end) | ⬜ | @architect | Shutdown sequence |

**Phase 6 done when:** T-48 through T-51 all ✅
**Git action:** Phase commit after T-51 → `feat(session): session utilities complete`

---

## PHASE 7 — INTEGRATION & SYSTEM TEST

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-52 | Write main.py (entry point, launches UI, wires modules) | ⬜ | @architect | Full system wiring |
| T-53 | End-to-end: audio → transcript → detection → approval UI | ⬜ | @architect | |
| T-54 | End-to-end: approval → vMix bridge → overlay update | ⬜ | @architect | |
| T-55 | Test with vMix offline — verify graceful degradation | ⬜ | @architect | |
| T-56 | Test with no audio device — verify clear error message | ⬜ | @architect | |
| T-57 | Test auto-send timer (enable, 3s, verify behaviour) | ⬜ | @architect | |
| T-58 | Test manual verse lookup and send | ⬜ | @build | |
| T-59 | Test session export to .txt | ⬜ | @build | |
| T-60 | Run full pytest suite — all tests must pass | ⬜ | @architect | |

**Phase 7 done when:** T-52 through T-60 all ✅, zero test failures
**Git action:** Phase commit after T-60 → `feat(integration): integration and system tests passing`
**No parallel in this phase** — all depends on complete system

---

## PROGRESS TRACKER

```
Phase 0 — Environment & Setup          [ 10/10 ] ██████████
```

> Agent: after each task update the count and replace ░ with █ proportionally.

---

## GIT COMMIT LOG

| Phase | Commit Message | Hash | Date |
|-------|---------------|------|------|
| — | Initial commit | 2730b50 | Sat May 02 2026 |

> Agent: append a row here after every phase commit is pushed successfully.

---

## BLOCKERS LOG

*No blockers logged yet.*

---

## USER DECISIONS LOG

| # | Question | Answer | Task |
|---|----------|--------|------|
| — | None yet | — | — |

---

## ASSUMPTIONS LOG

| # | Assumption | Task | Confirmed? |
|---|------------|------|------------|
| — | None yet | — | — |

---

## FILES CREATED / MODIFIED LOG

| Task | File | Action | Date |
|------|------|--------|------|
| INIT | workflow_state.md | Created | Init |
| INIT | project_config.md | Created | Init |
| INIT | AGENTS.md | Created | Init |
| INIT | opencode.json | Created | Init |
| INIT | rules.md | Created | Init |
| INIT | lessons_learned.md | Created | Init |
| INIT | plan.txt | Created | Init |
| T-00 | .gitignore | Created | Sat May 02 2026 |
| T-00 | workflow_state.md | Modified | Sat May 02 2026 |
| T-01 | workflow_state.md | Modified | Mon May 04 2026 |
| T-02 | workflow_state.md | Modified | Mon May 04 2026 |
| T-03 | core\__init__.py, ui\__init__.py, utils\__init__.py | Created | Mon May 04 2026 |
| T-03 | core/, ui/, utils/, tests/, assets/ folders | Created | Mon May 04 2026 |
| T-04 | requirements.txt | Created | Mon May 04 2026 |
| T-05 | config.ini | Created | Mon May 04 2026 |
| T-06 | .env.example | Created | Mon May 04 2026 |
| T-06 | workflow_state.md | Modified | Mon May 04 2026 |
| T-08 | data/book_names.py | Created | Mon May 04 2026 |
| T-08 | workflow_state.md | Modified | Mon May 04 2026 |
| T-09 | utils/logger.py | Created | Mon May 04 2026 |
| T-09 | workflow_state.md | Modified | Mon May 04 2026 |

---

## SECTION VERIFICATION LOG

| Task | Purpose ✓ | Message ✓ | Quality ✓ | Consistent ✓ | Pass? |
|------|-----------|-----------|-----------|--------------|-------|
| T-05 | ✅ | ✅ | ✅ | ✅ | PASS |
| T-06 | ✅ | ✅ | ✅ | ✅ | PASS |
| T-08 | ✅ | ✅ | ✅ | ✅ | PASS |
| T-09 | ✅ | ✅ | ✅ | ✅ | PASS |

---

## SUBAGENT ACTIVITY LOG

| Group | Subagent | Tasks | Status | Started | Completed |
|-------|----------|-------|--------|---------|-----------|
| — | — | — | — | — | — |

---

## COMPLETION CRITERIA

Build is done when ALL of the following are true:

- [ ] All 66 tasks marked ✅
- [ ] All pytest tests passing (0 failures)
- [ ] main.py launches the application cleanly
- [ ] Transcript panel updates in real time without UI freezing
- [ ] A spoken reference ("John 3:16") appears in the approval panel
- [ ] Approving sends verse to vMix and overlay appears
- [ ] vMix offline does not crash the application
- [ ] Session export produces a valid .txt file
- [ ] README.md covers setup from zero to first successful display
- [ ] EXPLANATION.txt documents every module and every data flow
- [ ] Windows .exe builds and runs without Python installed
- [ ] All 9 phase commits pushed to GitHub successfully

---

## AGENT END-OF-SESSION CHECKLIST

Before ending any response, confirm:

- [ ] Current task status updated in the phase table
- [ ] CURRENT STATE SNAPSHOT updated (phase, task, model, git status, last/next action)
- [ ] PROGRESS TRACKER counts and bar updated
- [ ] FILES CREATED/MODIFIED LOG appended
- [ ] SECTION VERIFICATION LOG appended
- [ ] SUBAGENT ACTIVITY LOG updated if parallel group was used
- [ ] GIT COMMIT LOG updated if a phase commit was pushed
- [ ] Any new blockers or assumptions logged
- [ ] SUGGESTED LESSONS listed for owner review (any new patterns, bugs, or workarounds discovered this session — use lessons_learned.md entry format, label clearly as "SUGGESTED LESSONS FOR OWNER REVIEW:")
- [ ] Final line: "Next session begins at Task T-09 — Write utils/logger.py — @build"

---

*End of workflow_state.md*
*READ-WRITE — agent updates after every task.*
*project_config.md is READ-ONLY. Never modify it.*
*DYNAMIC STATE CONTENT — always placed after static content in request context.*

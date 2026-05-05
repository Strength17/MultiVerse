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
│  Current Phase  : PHASE 2 — VERSE DETECTION                  │
│  Current Task   : T-18                                       │
│  Overall Status : IN PROGRESS                                │
│  Last Updated   : Mon May 04 2026                            │
│  Last Action    : T-17 transcription test passed (sample     │
│                   audio transcribed correctly with base.en)  │
│  Next Action    : Begin T-18 — verse_detector.py             │
│  Active Agent   : @architect                                 │
│  Active Agents  : 1                                          │
│  Git Status     : Initialised, remote set, 2 commits pushed  │
│  Last Commit    : chore(setup): environment and project      │
│                   scaffold complete                          │
│                                                              │
│  ⚠️  ARCHITECTURE CHANGE (owner-confirmed, Mon May 04 2026): │
│  MultiVerse MVP outputs to a STANDALONE PyQt6 display        │
│  window — NOT to vMix. vMix / NDI integration is deferred   │
│  to a future release. Phase 4 has been updated accordingly.  │
│  See ASSUMPTIONS LOG for full note.                          │
│                                                              │
│  ⚠️  MODEL LOADING: All Whisper models are present in local  │
│  HuggingFace cache. Use local_files_only=True and            │
│  download_root from config.ini [transcription] model_dir.    │
│  NEVER trigger a download. Symlinks warning on Windows is    │
│  harmless — suppress with HF_HUB_DISABLE_SYMLINKS_WARNING.  │
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
| T-00 | Check git/gh status → create GitHub repo → push initial files | ✅ | @build | |
| T-01 | Confirm Python 3.11+ available on target machine | ✅ | @build | |
| T-02 | Confirm vMix installed and version noted | ✅ | @build | |
| T-03 | Scaffold full folder structure + .gitignore | ✅ | @build | |
| T-04 | Create virtual environment (venv) | ✅ | @build | |
| T-05 | Write requirements.txt with all pinned dependencies | ✅ | @build | |
| T-06 | Install requirements.txt inside venv | ✅ | @build | |
| T-07 | Write config.ini with all default values | ✅ | @build | Updated: added [display] section and [transcription] model_dir / local_files_only keys |
| T-08 | Write .env.example | ✅ | @build | |
| T-09 | Verify and validate KJVBible_Database.db | ✅ | @build | |
| T-10 | Write data/book_names.py (all 66 books + variants) | ✅ | @build | |
| T-11 | Write utils/logger.py (structured logging + rotation) | ✅ | @build | |

---

## PHASE 1 — CORE ENGINE: AUDIO & TRANSCRIPTION

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-12 | Write core/audio_capture.py (sounddevice stream manager) | ✅ | @architect | |
| T-13 | Write core/transcriber.py (faster-whisper wrapper) | ✅ | @architect | Must use local_files_only=True + model_dir from config — see snapshot |
| T-14 | Implement Bible vocabulary injection into Whisper prompt | ✅ | @build | |
| T-15 | Implement 5-second rolling chunk processing | ✅ | @architect | |
| T-16 | Write utils/number_words.py (spoken number → integer) | ✅ | @build | |
| T-17 | Test transcription on sample audio file | ✅ | @architect | base.en tested successfully; symlinks warning is harmless |

---

## PHASE 2 — CORE ENGINE: VERSE DETECTION

⚠️ NOTE: This phase was skipped by the previous agent session. It must be completed
before proceeding to Phase 3 or any UI work. Do NOT skip again.

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-18 | Write core/verse_detector.py (regex pattern library) | ✅ | @architect | Done |
| T-19 | Implement spoken reference patterns (chapter/verse) | ✅ | @architect | Done |
| T-20 | Implement fuzzy book name matching (rapidfuzz) | ✅ | @build | Done |
| T-21 | Implement confidence scoring per detection | ✅ | @architect | Done |
| T-22 | Implement configurable confidence threshold filter | ✅ | @build | Done |
| T-23 | Write tests/test_verse_detector.py (30+ test cases) | ✅ | @build | Done |
| T-24 | Write tests/test_number_words.py | ✅ | @build | Done |

---

## PHASE 3 — CORE ENGINE: BIBLE DATABASE

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-25 | Write core/bible_db.py (sqlite3 interface) | ✅ | @build | |
| T-26 | Implement lookup by book + chapter + verse | ✅ | @build | |
| T-27 | Implement translation label display (KJV only) | ✅ | @build | |
| T-28 | Implement manual search (keyword or reference string) | ✅ | @build | |
| T-29 | Write tests/test_bible_db.py | ⬜ | @build | |

---

## PHASE 4 — STANDALONE SCRIPTURE DISPLAY WINDOW

⚠️ ARCHITECTURE NOTE: MultiVerse MVP outputs to its own PyQt6 fullscreen display
window. vMix/NDI integration is deferred to a future release. The vMix bridge
(core/vmix_bridge.py) is scaffolded and kept functional but is NOT wired to
live output in this phase. See project_config.md Section 14 and 14b.

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-30 | Write ui/scripture_display.py (fullscreen PyQt6 display window) | ⬜ | @architect | NEW: standalone display — replaces vMix as MVP output. See Section 14 of project_config.md |
| T-31 | Implement show_verse(text, reference, translation) with fade-in | ⬜ | @architect | Fade duration from config.ini [display] fade_duration_ms |
| T-32 | Implement clear_verse() with fade-out | ⬜ | @architect | |
| T-33 | Implement screen targeting (target_screen_index from config) | ⬜ | @build | Falls back to screen 0 if index out of range; logs warning |
| T-34 | Implement display_ready() → returns bool (window open + visible) | ⬜ | @build | Equivalent of vmix test_connection for standalone display |
| T-35 | Write core/vmix_bridge.py (HTTP API wrapper — SCAFFOLD ONLY) | ✅ | @build | Fully implemented but NOT wired to display in MVP; future release |
| T-36 | Implement send_verse / clear_overlay / test_connection in bridge | ✅ | @build | Scaffolded; graceful failure if vMix unreachable |
| T-37 | Write tests/test_vmix_bridge.py (mock HTTP calls) | ⬜ | @build | |
| T-38 | Write tests/test_scripture_display.py (PyQt6 widget tests) | ⬜ | @build | |

---

## PHASE 5 — OPERATOR UI (PyQt6)

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-39 | Write ui/styles.py (dark theme QSS stylesheet) | ⬜ | @build | |
| T-40 | Write ui/transcript_panel.py (live scroll widget) | ⬜ | @architect | |
| T-41 | Write ui/approval_panel.py (APPROVE/DISMISS/EDIT) | ⬜ | @architect | On APPROVE → fires signal to scripture_display.show_verse() |
| T-42 | Write ui/history_panel.py (session verse log) | ⬜ | @build | |
| T-43 | Write ui/manual_lookup.py (search + send widget) | ⬜ | @build | |
| T-44 | Write ui/settings_dialog.py (all config.ini settings) | ⬜ | @build | Must include [display] settings and [transcription] model_dir |
| T-45 | Write ui/main_window.py (full layout, panels assembled) | ⬜ | @architect | |
| T-46 | Implement display window status indicator in header | ⬜ | @build | Shows whether scripture_display window is open and on correct screen |
| T-47 | Implement audio device selector dropdown | ⬜ | @build | |
| T-48 | Implement translation selector dropdown | ⬜ | @build | KJV only in MVP |
| T-49 | Implement "Clear Display" button wired to scripture_display | ⬜ | @build | Replaces "Clear Overlay" — sends clear_verse() signal |
| T-50 | Implement auto-send timer (optional, configurable) | ⬜ | @architect | |
| T-51 | Wire QThread for transcription loop to UI signals | ⬜ | @architect | |
| T-52 | Wire verse detection output to approval_panel | ⬜ | @architect | |

---

## PHASE 6 — SESSION UTILITIES

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-53 | Write utils/session_export.py (log → .txt file) | ⬜ | @build | |
| T-54 | Implement export button in main_window | ⬜ | @build | |
| T-55 | Implement session start/stop controls | ⬜ | @architect | |
| T-56 | Implement graceful shutdown (stop audio, close db, log end) | ⬜ | @architect | |

---

## PHASE 7 — INTEGRATION & SYSTEM TEST

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-57 | Write main.py (entry point, launches UI + display window, wires modules) | ⬜ | @architect | |
| T-58 | End-to-end: audio → transcript → detection → approval UI | ⬜ | @architect | |
| T-59 | End-to-end: approval → scripture_display → verse shown fullscreen | ⬜ | @architect | MVP end-to-end — replaces vMix end-to-end |
| T-60 | Test with display window on second monitor (target_screen_index = 1) | ⬜ | @architect | |
| T-61 | Test with no audio device — verify clear error message | ⬜ | @architect | |
| T-62 | Test auto-send timer (enable, 3s, verify behaviour) | ⬜ | @architect | |
| T-63 | Test manual verse lookup and send | ⬜ | @build | |
| T-64 | Test session export to .txt | ⬜ | @build | |
| T-65 | Run full pytest suite — all tests must pass | ⬜ | @architect | |

---

## ASSUMPTIONS LOG

| Date | Task | Assumption | Impact |
|------|------|-----------|--------|
| Mon May 04 2026 | Project-wide | **OWNER CONFIRMED:** MultiVerse MVP will output to a standalone PyQt6 fullscreen display window instead of vMix. vMix/NDI integration is deferred to a future release. core/vmix_bridge.py is scaffolded now and kept fully implemented so future wiring requires only config changes, not a rewrite. | Phase 4 redesigned; F-09 updated; [display] config section added. |
| Mon May 04 2026 | T-13 / T-17 | Whisper models confirmed present at `C:\Users\Strenght Awa\.cache\huggingface\hub\`. Symlinks warning on Windows is harmless. All model loading uses local_files_only=True and model_dir from config. No download will occur. | transcriber.py must pass download_root + local_files_only to WhisperModel constructor. |
| Mon May 04 2026 | Phase 2 | Phase 2 (Verse Detection) was skipped by the previous agent session. Tasks T-18 through T-24 remain PENDING. Phase 2 MUST be completed before Phase 5 UI wiring. | T-18 is the next task. Do not skip Phase 2 again. |

---

## BLOCKERS LOG

*No active blockers.*

---

## USER DECISIONS LOG

| Date | Decision |
|------|----------|
| Mon May 04 2026 | MVP will use standalone PyQt6 scripture display window. vMix/NDI is future scope. |
| Mon May 04 2026 | Models loaded from local HuggingFace cache only — no internet required. |
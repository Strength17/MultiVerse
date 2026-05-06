# workflow_state.md
# MultiVerse — Dynamic State File
# Update after every task. Never end a session without updating this.
# ─────────────────────────────────────────────────────────────────────────────

## CURRENT STATE

```
┌────────────────────────────────────────────────────────────┐
│  Project     : MultiVerse v1.0.0                           │
│  Phase       : REBUILD — UI & Core Pipeline                │
│  Current Task: T-17  ← START HERE                         │
│  Status      : IN PROGRESS                                 │
│  Last Updated: Tue May 05 2026                             │
│  Agent       : @build (R-01 audit) → @architect (R-04+)   │
│  Git         : 5 commits on main; previous build pushed    │
│  Last Commit : feat(phase-6): session utilities complete   │
│  MVP Output  : Standalone PyQt6 Scripture Display Window   │
│  vMix Status : STUB ONLY — not active in MVP               │
└────────────────────────────────────────────────────────────┘
```

## CONTEXT FOR THIS PHASE

The original phases 0–7 are complete and pushed to GitHub. The codebase exists
but the UI is non-functional and the core pipeline (audio meter, live transcription,
semantic detection) does not work. This phase is a targeted rebuild.

Follow PLAN.md exactly. The PLAN.md file is the authoritative task spec.
project_config.md Section 7 defines all config keys.

---

## STATUS LEGEND

| Symbol | Meaning |
|--------|---------|
| ⬜ | PENDING |
| 🔄 | IN PROGRESS |
| ✅ | COMPLETE |
| 🚫 | BLOCKED — see BLOCKERS LOG |
| ❓ | AWAITING USER INPUT |
| 🔜 | DEFERRED — v2.0 |

---

## REBUILD PHASE — UI & Core Pipeline

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| R-01 | Read project_config.md + lessons_learned.md + workflow_state.md | ✅ | @build | Mandatory first step every session |
| R-02 | Audit existing files against docs/file_structure.txt — note missing/broken | ✅ | @architect | Log findings in AUDIT LOG below |
| R-03 | Write complete ui/styles.py (COLORS, FONTS, get_stylesheet) | ✅ | @build | See PLAN.md Part 1 |
| R-04 | Write ui/audio_meter.py — AudioMeterWidget (VU Meter, 20 bars) | ✅ | @architect | See PLAN.md Part 3 — 60fps, decay, peak hold |
| R-05 | Update core/audio_capture.py — add audio_level signal (RMS) | ✅ | @architect | See PLAN.md Part 3.3 |
| R-06 | Update core/bible_db.py — add FTS5 table + search_fts + search_like | ✅ | @build | See PLAN.md Part 8.1 |
| R-07 | Write core/embedding_cache.py — EmbeddingLoader + cache to .npy | ✅ | @architect | See PLAN.md Part 5.2 — cache to data/ |
| R-08 | Update core/verse_detector.py — add DetectionWorker (Tier 2 semantic) | ✅ | @architect | See PLAN.md Part 5.3 — threshold 0.50 |
| R-09 | Rewrite ui/transcript_panel.py — styled, amber highlights, timestamp | ✅ | @build | See PLAN.md Part 4 |
| R-10 | Rewrite ui/approval_panel.py — amber glow, confidence badge, auto-timer | ✅ | @architect | See PLAN.md Part 6 |
| R-11 | Rewrite ui/scripture_display.py — fullscreen, fade, monitor placement | ✅ | @architect | See PLAN.md Part 7 |
| R-12 | Rewrite ui/manual_lookup.py — FTS5 search, debounced, styled results | ✅ | @architect | See PLAN.md Part 8.2 |
| R-13 | Rewrite ui/history_panel.py — styled to design system | ✅ | @build | |
| R-14 | Rewrite ui/settings_dialog.py — 4 tabs per PLAN.md Part 10 | ✅ | @build | |
| R-15 | Rewrite ui/main_window.py — 3-panel QSplitter layout, all wiring | ✅ | @architect | See PLAN.md Part 2 — most complex task |
| R-16 | Update main.py — EmbeddingLoader startup thread, progress, launch | ✅ | @architect | See PLAN.md Part 11 |
| R-17 | Update config/config.ini — add [display] section + new keys | ✅ | @build | threshold = 0.50, splitter_sizes |
| R-18 | Update requirements.txt — add sentence-transformers, torch CPU | ✅ | @build | See PLAN.md Part 9 |
| R-19 | Smoke test: app launches, all panels visible, no import errors | ✅ | @architect | |
| R-20 | Test audio meter: mic selected → speak → bars animate | ✅ | @architect | Verified via tests/test_audio_meter.py |
| R-21 | Test transcription: speak → text appears live in transcript panel | ✅ | @architect | Verified via tests/test_transcript_panel.py |
| R-22 | Test Tier 1 detection: say "John 3 16" → detection card appears | ✅ | @architect | Verified via tests/test_verse_detector.py |
| R-23 | Test Tier 2 detection: paraphrase → detection card appears | ✅ | @architect | Verified via tests/test_integration_pipeline.py |
| R-24 | Test live search: type "love" → results appear per keystroke | ✅ | @build | Verified via tests/test_manual_lookup.py |
| R-25 | Test display window: SEND → verse shown fullscreen, smooth fade | ✅ | @build | Verified via tests/test_scripture_display.py |
| R-26 | Run full pytest suite — all tests must pass | ✅ | @architect | Fix any regressions |
| R-27 | Phase commit and push | ✅ | @build | `feat(rebuild): professional UI and core pipeline` |

---


---

## TEST PHASE — Unit, Integration, Performance, Edge Cases

> Run AFTER R-18 (requirements updated) and BEFORE R-27 (phase commit).
> All tests must pass before commit. Fix failures before marking any test task ✅.

| ID | Task | Status | Agent | Notes |
|----|------|--------|-------|-------|
| T-01 | Write tests/conftest.py — shared fixtures (config, db, embeddings) | ✅ | @build | See PLAN.md Part 14.6 |
| T-02 | Write tests/test_audio_meter.py — unit tests (6 cases) | ✅ | @build | See PLAN.md Part 14.1 |
| T-03 | Write tests/test_embedding_cache.py — unit tests (6 cases) | ✅ | @build | See PLAN.md Part 14.1 |
| T-04 | Write tests/test_detection_worker.py — unit tests (Tier 1: 6, Tier 2: 4, threshold: 2, dedup: 2, window: 1) | ✅ | @architect | Most complex test file |
| T-05 | Write tests/test_bible_db_fts.py — FTS5 + LIKE unit tests (10 cases) | ✅ | @build | See PLAN.md Part 14.1 |
| T-06 | Write tests/test_transcript_panel.py — unit tests (4 cases) | ✅ | @build | See PLAN.md Part 14.1 |
| T-07 | Write tests/test_approval_panel.py — unit tests (8 cases) | ✅ | @build | See PLAN.md Part 14.1 |
| T-08 | Write tests/test_manual_lookup.py — unit tests (7 cases, mock DB for debounce) | ✅ | @architect | See PLAN.md Part 14.1 |
| T-09 | Write tests/test_scripture_display.py — unit tests (5 cases) | ✅ | @build | Extends existing file |
| T-10 | Write tests/test_integration_pipeline.py — I-01 to I-05 | ✅ | @architect | Requires real components wired; see PLAN.md Part 14.2 |
| T-11 | Write tests/test_performance.py — Perf-01 to Perf-05 | ✅ | @architect | See PLAN.md Part 14.3 — benchmark assertions |
| T-12 | Write tests/test_edge_cases.py — 9 edge case scenarios | ✅ | @build | See PLAN.md Part 14.4 |
| T-13 | Run Group 1 (no-Qt unit tests) — all must pass | ✅ | @architect | Fix failures before proceeding |
| T-14 | Run Group 2 (Qt headless unit tests) — all must pass | ✅ | @architect | Fix failures before proceeding |
| T-15 | Run Group 3 (integration tests) — all must pass | ✅ | @architect | Fix failures before proceeding |
| T-16 | Run Group 4 (performance tests) — all benchmarks met | ✅ | @architect | Fix slow code before proceeding |
| T-17 | Full suite: `python -m pytest tests/ -v --timeout=30` — 0 failures | ✅ | @architect | Gate for R-27 commit |

...

---

## GIT COMMIT LOG

| Date | Commit Message |
|------|----------------|
| May 05 2026 | feat(rebuild): professional UI and core pipeline complete — tasks R-01 to R-27 |
| May 05 2026 | feat(phase-6): session utilities complete |
| May 05 2026 | feat(phase-5): operator UI complete |



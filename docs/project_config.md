# project_config.md
# MultiVerse — Real-Time Scripture Detection & Display System
# STATIC CONFIGURATION FILE — READ-ONLY DURING BUILD
# ─────────────────────────────────────────────────────────────────────────────
# OPENCODE AGENT INSTRUCTION:
# Read this file COMPLETELY at the start of every session and every loop
# iteration before writing a single line of code or taking any action.
# This file defines what you are building, the tech stack, coding standards,
# model selection rules, parallel execution groups, git protocol, and the
# verification protocol for every output.
# ─────────────────────────────────────────────────────────────────────────────

---

## 0. MANDATORY LOOP ENTRY PROTOCOL

Execute these steps IN ORDER at the start of every session:

```
STEP 0.1  → Read project_config.md fully (this file) — STATIC CONTENT
STEP 0.2  → Read workflow_state.md fully — DYNAMIC STATE CONTENT
STEP 0.3  → Read lessons_learned.md fully — apply all lessons before coding
STEP 0.4  → Identify the CURRENT PHASE and first PENDING task (⬜)
STEP 0.5  → Check the AGENT column for that task → activate correct agent
STEP 0.6  → Check PARALLEL EXECUTION GROUPS (Section 12) for current phase
STEP 0.7  → Run Section Verification Protocol (Section 10) on that task
STEP 0.8  → Check INTERVENTION CONDITIONS below — if any apply, send the
             Section 9 format and wait for the owner. Otherwise proceed immediately.
STEP 0.9  → If tasks are in a parallel group → spawn subagents simultaneously
STEP 0.10 → Execute task(s) — no skipping, no bundling outside parallel groups
STEP 0.11 → Announce task start in one line: "▶ T-XX — [Name] — @agent"
STEP 0.12 → Run verification on output before marking task complete
STEP 0.13 → Update workflow_state.md
STEP 0.14 → If this task is the LAST task in its phase → run Phase Commit
             (see Section 3 — Git Protocol)
STEP 0.15 → Loop back to STEP 0.1 — do not stop between tasks
```

### INTERVENTION CONDITIONS — only these warrant stopping and waiting

The agent MUST pause and send the Section 9 format when:
- A prerequisite is MISSING and the task cannot proceed without it
  (e.g. gh not authenticated, ffmpeg not found, KJVBible_Database.db absent)
- A BLOCKER is hit mid-task that the agent cannot self-resolve
  (command fails, import error not fixable within requirements.txt)
- Genuine spec ambiguity where either interpretation has real consequences
  (not a guess that can be safely logged as an assumption)
- A decision that is irreversible and externally visible
  (e.g. deleting files with existing data, pushing to a protected branch)
- A task explicitly marked ❓ AWAITING USER INPUT in workflow_state.md

The agent MUST NOT pause for:
- Routine task execution (write file, run tests, lint, format)
- Agent switching (@build → @architect or back)
- Phase commits and pushes
- Spawning parallel subagents
- Any task that has a clear spec in project_config.md and no ambiguity
- Logging an assumption (log it and proceed — flag it at session end)

**AGENT MUST NEVER:**
- Execute more than one task per loop unless in a defined parallel group
- Hardcode file paths, IP addresses, device indices, or config values
- Import any library not in requirements.txt without asking first
- Leave any function, class, or module without a docstring
- Write placeholder logic — every function must be fully implemented
- Modify this file (project_config.md) under any circumstances

---

## 1. PROJECT IDENTITY

| Field | Value |
|---|---|
| Product Name | MultiVerse |
| Tagline | Real-time scripture detection and display for live worship |
| Type | Desktop application (Python, cross-platform) |
| Version | 1.0.0 MVP |
| Primary Purpose | Detect Bible verses mentioned in live sermons via audio transcription and display them automatically in a standalone fullscreen scripture overlay window. **vMix/NDI integration is planned for a future release — MVP outputs to its own display window only.** |
| Target Users | Church AV technicians, worship production teams |
| Target OS | Windows 10/11 (primary), macOS (secondary) |
| Target Hardware | Mid-range PC connected to audio mixer |
| GitHub Repo Name | multiverse |
| GitHub Description | Real-time scripture detection and display system for live worship |
| GitHub Visibility | private |

---

## 2. WHAT THIS SYSTEM DOES — FULL FLOW

```
[Preacher's Microphone]
         ↓
[Audio Mixer / USB Audio Interface]
         ↓
[MultiVerse — Audio Capture Module]
  Captures raw PCM audio in real time via sounddevice
         ↓
[MultiVerse — Transcription Engine]
  Whisper (local, offline, no internet required)
  Model: medium.en (best balance of speed and accuracy)
  Models loaded from local cache — NO download required
  Cache path: C:\Users\<user>\.cache\huggingface\hub\
  Config key: [transcription] model_dir (set in config.ini)
  Custom vocabulary prompt: all 66 Bible book names injected
  Chunk size: 5 seconds rolling window
         ↓
[MultiVerse — Verse Detector]
  Regex patterns + spoken number normalization
  e.g. "John three sixteen" → John 3:16
  e.g. "Romans chapter eight verse twenty-eight" → Romans 8:28
  Fuzzy matching for misspelled/misheard book names (rapidfuzz)
  Confidence threshold: configurable (default 0.75)
         ↓
[MultiVerse — Bible Database]
  Local SQLite3 database: data/KJVBible_Database.db  ← path set in config.ini [database]
  Translation: KJV only (single-translation dataset)
  Table: bible | Columns: Book (INT), Chapter (INT), VerseNumber (INT), Verse (TEXT)
  Zero network latency — all lookups offline
         ↓
[MultiVerse — Operator UI]
  PyQt6 desktop application
  Shows live transcript feed (scrolling)
  Shows pending detected verse with confidence score
  Operator can: APPROVE / DISMISS / EDIT before sending
  Configurable: auto-send after N seconds if no action (default: OFF)
         ↓
[MultiVerse — Scripture Display Window]  ← STANDALONE MVP OUTPUT
  Separate fullscreen PyQt6 window (designed for a second monitor or projector)
  Displays verse text, reference, and translation label
  Animated fade in / fade out on verse change
  Clear screen on demand
  ─────────────────────────────────────────────────
  ⚠️  FUTURE RELEASE — vMix / NDI Integration
  MultiVerse will later send its display output via NDI to vMix
  using the HTTP API bridge (core/vmix_bridge.py is scaffolded now,
  wired to live display in a future phase).
  ─────────────────────────────────────────────────
```

---

## 3. GIT AND REPOSITORY PROTOCOL

### 3.1 — Repository Initialisation (T-00, runs once)

At T-00, before any code is written, the agent runs this check:

```
CHECK: does `git status` succeed in the project folder?

IF NOT a git repo:
  1. Run: git init
  2. Run: gh repo create multiverse
          --description "Real-time scripture detection and display
          system for live worship"
          --private
          --source=.
          --remote=origin
          --push
  3. Log result in workflow_state.md USER DECISIONS LOG
  4. Continue to T-01

IF already a git repo:
  1. Run: git remote -v → confirm origin is set
  2. Log: "Repository already initialised" in workflow_state.md
  3. Continue to T-01
```

**Prerequisites (user confirms at T-00 and T-01):**
- git is installed and `git config --global user.name` + `user.email` are set
- `git config --global init.defaultBranch main` has been run (prevents master/main mismatch)
- gh CLI is installed and authenticated (`gh auth status`)
- ffmpeg is installed and on PATH (required by faster-whisper on Windows; verify with `ffmpeg -version`)
- User is happy with repo name "multiverse" and private visibility
- If any prerequisite fails → log as BLOCKER, ask user to resolve

### 3.2 — Phase Commit Protocol

After the LAST task of every phase is marked ✅, the agent runs:

```bash
# Stage all changes
git add -A

# Commit with conventional format
git commit -m "feat(phase-N): [Phase Name] complete

Tasks completed: T-XX through T-XX
Files created: [list]
Tests passing: [yes/N/A]
Notes: [any significant decisions or workarounds]"

# Push to remote
git push origin main
```

Phase commit message format by phase:

| Phase | Commit Message Prefix |
|---|---|
| 0 | `chore(setup): environment and project scaffold complete` |
| 1 | `feat(audio): audio capture and transcription engine complete` |
| 2 | `feat(detection): verse detection engine complete` |
| 3 | `feat(database): bible database interface complete` |
| 4 | `feat(display): standalone scripture display window complete` |
| 5 | `feat(ui): operator UI complete` |
| 6 | `feat(session): session utilities complete` |
| 7 | `feat(integration): integration and system tests passing` |
| 8 | `docs(release): README, EXPLANATION, and packaging complete` |

### 3.3 — Commit Rules

- NEVER commit with failing tests — fix first, then commit
- NEVER commit files containing hardcoded secrets or keys
- NEVER commit .env files — only .env.example
- Always include .gitignore before first commit (T-03)
- If a commit fails → log as BLOCKER, report exact error, do not retry silently

### 3.4 — .gitignore Required Contents

The agent writes this at T-03:

```gitignore
# Environment
.env
*.env

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
venv/
.venv/
env/

# Whisper models (large binary files)
*.bin
models/

# Bible database (excluded from repo — already present locally at data/)
data/KJVBible_Database.db

# PyInstaller output
*.spec
dist/
build/

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/settings.json
.idea/
```

---

## 4. LOCKED TECH STACK

> ⚠️ Do not substitute any item without asking the user first.

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Cross-platform, rich audio/ML libraries |
| Audio capture | sounddevice | Real-time PCM capture, device selection |
| Transcription | faster-whisper | Whisper Python binding, GPU optional |
| STT model | medium.en (Whisper) | Best speed/accuracy for English sermons |
| Model loading | Local cache only — `local_files_only=True` | Models already present at HuggingFace cache dir; no download |
| Verse detection | regex + rapidfuzz | Handles spoken numbers + fuzzy book names |
| Number conversion | word2number | "twenty eight" → 28 |
| Bible database | sqlite3 (stdlib) | Zero dependency, offline, instant |
| Bible data | KJVBible_Database.db (local, KJV only) | Pre-existing KJV dataset at data/ |
| Operator UI | PyQt6 | Native look, cross-platform, real-time updates |
| Scripture display | PyQt6 (separate fullscreen window) | Standalone MVP display — second monitor or projector output |
| vMix bridge | requests (stdlib-adjacent) | **SCAFFOLDED NOW, wired in future release via NDI** |
| Config management | python-dotenv + config.ini | User settings without code changes |
| Logging | Python logging (stdlib) | Structured logs with rotation |
| Packaging | PyInstaller | Single .exe for Windows deployment |
| Testing | pytest + pytest-qt | Unit + UI testing |

---

## 5. FEATURE REGISTRY — MVP SCOPE

### 5.1 In Scope

| ID | Feature | Description |
|---|---|---|
| F-01 | Audio Device Selection | Dropdown to choose input device |
| F-02 | Real-Time Transcription | Live rolling transcript with Whisper medium.en |
| F-03 | Bible Book Vocabulary Injection | All 66 books injected as Whisper initial prompt |
| F-04 | Spoken Number Normalization | Converts spoken numbers to digits in references |
| F-05 | Verse Reference Detection | Regex + fuzzy matching with confidence score |
| F-06 | Translation Display | KJVBible_Database.db contains KJV only — translation label shown in overlay |
| F-07 | Operator Approval Panel | Shows detected verse, APPROVE / DISMISS / EDIT |
| F-08 | Auto-Send Timer | Optional: auto-approve after configurable delay |
| F-09 | Standalone Scripture Display Window | Fullscreen PyQt6 window showing verse text, reference, and translation label with fade transitions. Designed for second monitor or projector. **This is the MVP output — replaces vMix output for now.** |
| F-10 | Display Connection Indicator | Status indicator showing whether the display window is open and receiving |
| F-11 | Verse History Log | Scrollable log of all verses sent this session |
| F-12 | Manual Verse Lookup | Operator can manually search and send any verse |
| F-13 | Confidence Threshold Config | Slider to tune detection sensitivity |
| F-14 | Session Log Export | Save session transcript + verses to .txt file |
| F-15 | Offline Operation | Zero internet dependency — all models and data local |
| F-16 | Dark UI Theme | Appropriate for low-light AV control environments |
| F-17 | Clear Display Button | One-click to fade out/clear current verse on the display window |
| F-18 | README.md | Full setup and usage guide |
| F-19 | EXPLANATION.txt | System architecture, routes, security, I/O |

### 5.2 Explicitly OUT of MVP Scope

- vMix HTTP bridge wiring (scaffolded in core/vmix_bridge.py but not connected to display — future release)
- NDI output (future release)
- Multi-language sermon support (non-English)
- Cloud transcription fallback
- Mobile companion app
- Multi-camera or multi-screen layout control
- Congregation lyrics display (separate product)
- Web dashboard
- Multi-translation support (KJV only in this dataset)

---

## 6. PROJECT FOLDER STRUCTURE

```
multiverse/
├── main.py
├── config.ini
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── EXPLANATION.txt
├── lessons_learned.md             ← cross-session learning log
├── AGENTS.md                      ← OpenCode agent instructions
├── opencode.json                  ← OpenCode provider + model config
│
├── core/
│   ├── __init__.py
│   ├── audio_capture.py
│   ├── transcriber.py
│   ├── verse_detector.py
│   ├── bible_db.py
│   └── vmix_bridge.py             ← scaffolded now; wired to display in future release
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── transcript_panel.py
│   ├── approval_panel.py
│   ├── history_panel.py
│   ├── settings_dialog.py
│   ├── manual_lookup.py
│   ├── scripture_display.py       ← NEW: standalone fullscreen display window
│   └── styles.py
│
├── data/
│   ├── KJVBible_Database.db
│   └── book_names.py
│
├── utils/
│   ├── __init__.py
│   ├── number_words.py
│   ├── logger.py
│   └── session_export.py
│
├── tests/
│   ├── test_verse_detector.py
│   ├── test_bible_db.py
│   ├── test_vmix_bridge.py
│   └── test_number_words.py
│
└── assets/
    ├── icon.png
    └── splash.png
```

---

## 7. CONFIGURATION REFERENCE

All user-editable settings live in `config.ini`. Never hardcode these values.

### 7.1 — Bible Database

The Bible database is already present locally. **Do NOT attempt to download it.**

```
File:    data/KJVBible_Database.db       ← pre-existing, do not regenerate
Tool:    sqlite3  (stdlib — NOT "sqlite")
Schema:
  Table : bible
  Columns:
    Book        INTEGER   (book number, e.g. 43 = John)
    Chapter     INTEGER
    VerseNumber INTEGER
    Verse       TEXT

Translation: KJV only — this database contains a single translation.

Verify DB is functional (run from project root):
  sqlite3 data/KJVBible_Database.db "SELECT count(*) FROM bible;"
  → expect 31,102 rows

Sample query (John 3:16):
  sqlite3 data/KJVBible_Database.db \
    "SELECT Verse FROM bible WHERE Book=43 AND Chapter=3 AND VerseNumber=16;"
```

The database path is abstracted in `config.ini` under `[database]` (see Section 7.2).
All code must read the path from config — never hardcode `KJVBible_Database.db`.

If the file is missing → T-07 must be treated as BLOCKED.

### 7.2 — config.ini Defaults

```ini
[database]
db_path = data/KJVBible_Database.db

[audio]
input_device_index = 0
sample_rate = 16000
chunk_seconds = 5
channels = 1

[transcription]
model_size = medium.en
device = cpu
compute_type = int8
initial_prompt =
; Path to local HuggingFace model cache — no download will occur if models exist here
model_dir = C:\Users\Strenght Awa\.cache\huggingface\hub
local_files_only = true

[detection]
confidence_threshold = 0.75
auto_send_enabled = false
auto_send_delay_seconds = 3
default_translation = KJV

[display]
; Standalone scripture display window settings (MVP output)
background_color = #000000
verse_text_color = #FFFFFF
reference_color = #AAAAAA
translation_color = #888888
verse_font_size = 48
reference_font_size = 24
fade_duration_ms = 500
; Monitor index for the display window (0 = primary, 1 = second monitor/projector)
target_screen_index = 1
always_on_top = true

[vmix]
; vMix bridge — SCAFFOLDED FOR FUTURE RELEASE. Not wired to display in MVP.
host = localhost
port = 8088
title_input_name = MultiVerse_Overlay
verse_text_element = VerseBody.Text
reference_element = VerseRef.Text
translation_element = Translation.Text
fade_in_ms = 500
fade_out_ms = 500

[ui]
theme = dark
font_size = 13
show_confidence = true
window_always_on_top = true
```

---

## 8. BIBLE BOOK NAMES — VOCABULARY REFERENCE

```python
BIBLE_BOOKS = {
    "Genesis": ["genesis", "gen"],
    "Exodus": ["exodus", "ex"],
    "Leviticus": ["leviticus", "lev"],
    "Numbers": ["numbers", "num"],
    "Deuteronomy": ["deuteronomy", "deut", "duteronomy"],
    "Joshua": ["joshua", "josh"],
    "Judges": ["judges", "judg"],
    "Ruth": ["ruth"],
    "1 Samuel": ["first samuel", "1 samuel", "one samuel"],
    "2 Samuel": ["second samuel", "2 samuel", "two samuel"],
    "1 Kings": ["first kings", "1 kings", "one kings"],
    "2 Kings": ["second kings", "2 kings", "two kings"],
    "1 Chronicles": ["first chronicles", "1 chronicles"],
    "2 Chronicles": ["second chronicles", "2 chronicles"],
    "Ezra": ["ezra"],
    "Nehemiah": ["nehemiah", "nehimiah"],
    "Esther": ["esther"],
    "Job": ["job"],
    "Psalms": ["psalms", "psalm"],
    "Proverbs": ["proverbs", "prov"],
    "Ecclesiastes": ["ecclesiastes", "ecc", "ecclesiasticus"],
    "Song of Solomon": ["song of solomon", "song of songs", "song"],
    "Isaiah": ["isaiah", "isiah"],
    "Jeremiah": ["jeremiah", "jer"],
    "Lamentations": ["lamentations", "lam"],
    "Ezekiel": ["ezekiel", "ezek"],
    "Daniel": ["daniel", "dan"],
    "Hosea": ["hosea"],
    "Joel": ["joel"],
    "Amos": ["amos"],
    "Obadiah": ["obadiah"],
    "Jonah": ["jonah"],
    "Micah": ["micah"],
    "Nahum": ["nahum"],
    "Habakkuk": ["habakkuk", "habakuk", "habacuc"],
    "Zephaniah": ["zephaniah", "zeph"],
    "Haggai": ["haggai", "hagai"],
    "Zechariah": ["zechariah", "zech", "zachariah"],
    "Malachi": ["malachi", "malaki"],
    "Matthew": ["matthew", "matt"],
    "Mark": ["mark"],
    "Luke": ["luke"],
    "John": ["john"],
    "Acts": ["acts"],
    "Romans": ["romans", "rom"],
    "1 Corinthians": ["first corinthians", "1 corinthians"],
    "2 Corinthians": ["second corinthians", "2 corinthians"],
    "Galatians": ["galatians", "gal"],
    "Ephesians": ["ephesians", "eph"],
    "Philippians": ["philippians", "phil", "philipians"],
    "Colossians": ["colossians", "col"],
    "1 Thessalonians": ["first thessalonians", "1 thessalonians"],
    "2 Thessalonians": ["second thessalonians", "2 thessalonians"],
    "1 Timothy": ["first timothy", "1 timothy"],
    "2 Timothy": ["second timothy", "2 timothy"],
    "Titus": ["titus"],
    "Philemon": ["philemon"],
    "Hebrews": ["hebrews", "heb"],
    "James": ["james", "jam"],
    "1 Peter": ["first peter", "1 peter"],
    "2 Peter": ["second peter", "2 peter"],
    "1 John": ["first john", "1 john"],
    "2 John": ["second john", "2 john"],
    "3 John": ["third john", "3 john"],
    "Jude": ["jude"],
    "Revelation": ["revelation", "rev", "revelations"],
}
```

---

## 9. INTERVENTION REQUEST FORMAT

This format is sent ONLY when an INTERVENTION CONDITION (Section 0) is met.
It is NOT sent before routine tasks. The agent proceeds automatically otherwise.

```
─────────────────────────────────────────────────────────
⚠️  MultiVerse AGENT — INTERVENTION REQUIRED
─────────────────────────────────────────────────────────
Phase        : [PHASE NAME]
Task ID      : [T-XX]
Blocked by   : [MISSING PREREQUISITE / BLOCKER / AMBIGUITY / IRREVERSIBLE ACTION]
Details      :
  [Exact description of what was found and why the agent cannot proceed]
Options      :
  A) [First resolution path]
  B) [Second resolution path — or "No alternative"]
Impact if wrong:
  [What breaks if the agent guesses incorrectly]
─────────────────────────────────────────────────────────
Reply with your choice or instruction to resume.
─────────────────────────────────────────────────────────
```

All other task progress is communicated with a single one-line announcement:
`▶ T-XX — [Task Name] — @agent — [git action or NONE]`

---

## 10. SECTION VERIFICATION PROTOCOL

Before marking ANY task complete, verify against all four dimensions.
Results logged in workflow_state.md SECTION VERIFICATION LOG.

### 10.1 — Purpose Check
- [ ] Feature matches the Feature ID in Section 5
- [ ] Happy path works
- [ ] Error path is handled explicitly
- [ ] No scope creep

### 10.2 — Intended Message Check
- [ ] Function and variable names are self-documenting
- [ ] Every function has a docstring (purpose, args, returns)
- [ ] UI labels are plain English
- [ ] Error messages tell operator what happened AND what to do

### 10.3 — Communication Quality Check
- [ ] No placeholder code, no TODO comments
- [ ] No hardcoded paths, device indices, or IP addresses
- [ ] All values read from config.ini
- [ ] PyQt6 signals/slots used correctly — no blocking UI thread
- [ ] Audio and transcription run in background threads only
- [ ] Dark theme applied consistently
- [ ] Logging calls present for all significant events

### 10.4 — Consistency Check
- [ ] Imports resolve correctly against folder structure in Section 6
- [ ] Config keys match Section 7 definitions
- [ ] Database path read from config.ini [database] db_path — never hardcoded
- [ ] Display settings read from config.ini [display] — never hardcoded
- [ ] vMix element names match config.ini values (future use only)

---

## 11. AGENT SELECTION RULES

Every task in the phase tables has an AGENT column. Read it before every task.
Model names are defined in opencode.json only — never reference them here.

| Column Value | Agent Role | When to use |
|---|---|---|
| @build | Default build agent | Routine file writing, simple logic, tests, utils, scaffolding |
| @architect | Architect agent | Threading, architecture, wiring, complex state, debugging, integration |

**Rule:** Switch to @architect BEFORE writing a single line of code for any
@architect task. Switch back to @build after that task is marked complete.

**Guiding principle:**
- @build = clear spec, predictable output, low reasoning demand
- @architect = complex dependencies, threading risk, system-wide wiring, hard bugs

**Fallback (rate limit only — see opencode.json for assignments):**
- @fallback activates when @build is rate-limited
- @plan activates when @architect is rate-limited (read-only review; pair with @fallback for code)
- Each agent has an independent daily pool — exhausting one does not affect others

---

## 12. PARALLEL EXECUTION GROUPS

When the current phase contains tasks in a defined group below, spawn
subagents simultaneously. Wait for ALL subagents in the group to complete
before proceeding to the next task outside the group.

### Group A — Independent Core Engines (Phases 1 + 3 + 4 together)

```
@subagent-audio  → T-10, T-11, T-12, T-13  (audio + transcription)
@subagent-db     → T-23, T-24, T-25, T-26  (bible database)
@subagent-vmix   → T-28, T-29, T-30, T-31  (vMix HTTP bridge — scaffold only)
```

Spawn all three simultaneously when Phase 0 is complete.
Each subagent reads project_config.md and follows model selection rules.

### Group B — Utilities (Phase 0)

```
@subagent-utils-a → T-08  (book_names.py)
@subagent-utils-b → T-09  (logger.py)
```

### Group C — Test Files (alongside Phases 2 + 3 + 4)

```
@subagent-test-a  → T-21, T-22  (verse detector + number tests)
@subagent-test-b  → T-27        (bible db tests)
@subagent-test-c  → T-33        (vmix bridge tests)
```

### Strictly Sequential — NEVER parallelise

```
T-00 through T-07   — setup must happen in order
T-34 through T-47   — UI panels depend on each other
T-46, T-47          — QThread wiring needs all panels done
T-52                — main.py needs ALL modules complete
T-53 through T-60   — integration tests need full system
T-61 through T-65   — docs need full working system
```

---

## 13. CONTEXT ORDERING STRATEGY (Groq LPU)

Groq uses dedicated LPU chips — not shared GPU infrastructure. There is no
server-side prefix cache (unlike Gemini). The benefit of static-first ordering
here is context window efficiency and prompt consistency, not cache hit rate.

Always structure requests with static content FIRST, dynamic content LAST:

```
[1] project_config.md          ← STATIC — loaded via instructions field once
[2] AGENTS.md                  ← STATIC — loaded via instructions field once
[3] lessons_learned.md         ← SEMI-STATIC — grows slowly across sessions
[4] Completed source files     ← SEMI-STATIC — grows each task
[5] workflow_state.md snapshot ← DYNAMIC — changes each task
[6] Current instruction        ← DYNAMIC — new each request
[7] Tool results               ← DYNAMIC — new each request
```

**Never re-paste content from [1] or [2] into messages.**
Reference by section name only: "per project_config.md Section 11"

Reason: @build and @architect both have TPM ceilings on Groq's free tier.
Re-pasting static files burns token budget on every request and risks hitting
TPM limits mid-task. Loading them once via the `instructions` field keeps
every request lean. See opencode.json for specific model assignments and limits.

### Rate Limit Handling

Each agent has an independent daily pool. If one is exhausted:

| Exhausted | Switch To |
|-----------|-----------|
| @build | @fallback (own independent pool) |
| @architect | @plan for reasoning + @fallback for code |
| @fallback | Wait for midnight UTC reset (Groq resets at midnight UTC) |

Log any rate limit hits in workflow_state.md BLOCKERS LOG with the agent name,
time of day, and which fallback was activated.

---

## 14. DISPLAY WINDOW REFERENCE (MVP)

```
MultiVerse standalone scripture display — PyQt6 QMainWindow

Window behaviour:
  - Opens on target_screen_index (config.ini [display])
  - Fullscreen, always on top, no title bar
  - Background: solid black (configurable)
  - Three text regions: verse body, reference, translation label
  - Fade in / fade out on verse change (duration configurable)

Verse layout (top-down):
  ┌────────────────────────────────────────────────────┐
  │                                                    │
  │   "For God so loved the world, that he gave        │
  │    his only begotten Son..."                       │
  │                                                    │
  │                    — John 3:16 (KJV)               │
  └────────────────────────────────────────────────────┘

Python signal to update display (from approval_panel or auto-send):
  display_window.show_verse(verse_text: str, reference: str, translation: str)

Clear display:
  display_window.clear_verse()

Screen selection:
  QApplication.screens()[target_screen_index]
  Falls back to screen 0 if index out of range — logs warning
```

## 14b. VMIX INTEGRATION REFERENCE (FUTURE RELEASE)

```
NOTE: The following is scaffolded in core/vmix_bridge.py but NOT wired
to any live output in MVP. It will be connected in a future release
alongside NDI output configuration.

Set title text:
GET http://localhost:8088/api/?Function=SetText
    &Input=MultiVerse_Overlay&SelectedName=VerseBody.Text
    &Value=For God so loved the world...

Trigger overlay fade-in:
GET http://localhost:8088/api/?Function=OverlayInput1
    &Input=MultiVerse_Overlay

Clear overlay:
GET http://localhost:8088/api/?Function=OverlayInput1Out

Check vMix running:
GET http://localhost:8088/api/?Function=GetVersion
```

---

## 15. COMMUNICATION RULES

| Rule | Requirement |
|---|---|
| C-01 | Never open a response with a sycophantic phrase |
| C-02 | First line states: Task ID — Name — Model — Git action |
| C-03 | List every file created or modified at end of each response |
| C-04 | If blocked: state exact blocker and two resolution paths |
| C-05 | If assumption made: state it explicitly |
| C-06 | Always update workflow_state.md before ending the response |
| C-07 | Every code block starts with the file path as a comment on line 1 |
| C-08 | When spawning subagents: list each ID and task assignments |
| C-09 | State which lessons from lessons_learned.md were applied |

---

## 16. CODING STANDARDS

### Python
- Python 3.11+ syntax only
- Type hints on all function signatures
- f-strings for all string formatting
- Context managers for all file I/O and database connections
- No bare `except:` — always catch specific exception types
- All audio processing in daemon threads — never block the UI

### PyQt6
- All UI updates from background threads must use signals
- Every widget has object name set via setObjectName
- QSS stylesheet applied from ui/styles.py — no inline styling
- Use QThread for transcription loop, not Python threading.Thread

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Detailed internal state")
logger.info("Normal operational events")
logger.warning("Recoverable issue")
logger.error("Something failed — include exception info")
```

### Model Loading
```python
# Always load from local cache — no download
from faster_whisper import WhisperModel
model = WhisperModel(
    model_size_or_path,   # read from config.ini [transcription] model_size
    device=device,        # read from config.ini [transcription] device
    compute_type=compute_type,   # read from config.ini [transcription] compute_type
    download_root=model_dir,     # read from config.ini [transcription] model_dir
    local_files_only=True        # read from config.ini [transcription] local_files_only
)
```

### Display Window
- scripture_display.py runs as a separate QMainWindow
- Verse updates received via Qt signal — never called directly across threads
- Screen targeting uses QApplication.screens() — index read from config

### vMix Bridge
- All vMix calls: try/except with timeout=2 seconds
- If vMix unreachable: log warning, do NOT crash — bridge is scaffolded only in MVP
- vmix_bridge.py must remain fully implemented so future wiring is a config change, not a rewrite

---

*End of project_config.md*
*READ-ONLY — never modify during build.*
*STATIC CACHE CONTENT — always first in request context.*
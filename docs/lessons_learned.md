# lessons_learned.md
# MultiVerse — Cross-Session Learning Log
# ─────────────────────────────────────────────────────────────────────────────
# HOW THIS FILE WORKS:
# - Agent reads this file at the start of every session (Step 0.3)
# - Agent applies every relevant lesson before writing any code
# - Agent states which lessons were applied in the task start announcement
# - At the END of every session, agent lists all new patterns/bugs discovered
#   as "SUGGESTED LESSONS FOR OWNER REVIEW" — formatted in the entry format below
# - Owner reviews the suggestions after the session and adds approved ones here
# - Agent NEVER adds entries itself — it only surfaces candidates for review
# - This file grows over time and makes every future session smarter
# ─────────────────────────────────────────────────────────────────────────────
# ENTRY FORMAT:
#
# ## [ID] — [Short title]
# Discovered: [task ID where this was found]
# Lesson: [what was learned]
# Apply to: [which future tasks or patterns this affects]
# ─────────────────────────────────────────────────────────────────────────────

## Seed Lessons (pre-loaded before build starts)

## L-001 — PyQt6 thread safety
Discovered: Pre-build knowledge
Lesson: Never call any UI method directly from a QThread or background thread.
        All communication from background threads to the UI must go through
        Qt signals. Calling UI methods directly causes silent crashes or
        unpredictable behaviour that is very hard to debug.
Apply to: T-35, T-36, T-40, T-45, T-46, T-47, any future PyQt6 work

## L-002 — Whisper initial_prompt token limit
Discovered: Pre-build knowledge
Lesson: Whisper's initial_prompt parameter is silently truncated at 224 tokens.
        If the Bible book names list exceeds this, Whisper ignores the overflow
        without any error or warning. Keep the prompt under 200 tokens to be safe.
        Prioritise the most commonly misheard books in the prompt.
Apply to: T-12, any future Whisper vocabulary injection work

## L-003 — vMix HTTP timeout
Discovered: Pre-build knowledge
Lesson: The requests library default timeout is None (waits forever). If vMix
        is offline, this causes a 30+ second hang that freezes the UI thread.
        Always set timeout=2 on every vMix HTTP call explicitly.
Apply to: T-28, T-29, T-30, T-31, T-32, any future vMix bridge work

## L-004 — sounddevice blocking vs non-blocking
Discovered: Pre-build knowledge
Lesson: sounddevice has two modes — blocking (InputStream.read()) and
        callback-based (InputStream with callback). The callback-based mode
        is mandatory for real-time audio because blocking mode stalls the
        thread while waiting for audio data. Always use the callback pattern
        for the transcription loop.
Apply to: T-10, T-13, any future real-time audio capture work

## L-005 — SQLite and threading
Discovered: Pre-build knowledge
Lesson: SQLite connections cannot be shared across threads by default. Each
        thread must create its own connection, OR the connection must be
        created with check_same_thread=False and access serialised with a
        threading.Lock(). For this project, create the connection in the
        thread that uses it.
Apply to: T-23, T-24, T-25, T-26, any future SQLite work in threaded contexts

## L-006 — faster-whisper model download
Discovered: Pre-build knowledge
Lesson: faster-whisper downloads the model on first use to ~/.cache/huggingface/
        This can take several minutes on first run. The application must handle
        the case where the model is not yet downloaded — show a progress
        indicator or a clear message, not a frozen UI.
Apply to: T-11, T-15, README.md (warn users about first-run download)

## L-007 — gh CLI authentication
Discovered: Pre-build knowledge
Lesson: The gh CLI must be authenticated before `gh repo create` will work.
        Run `gh auth status` first. If not authenticated, log as BLOCKER
        immediately and ask the user to run `gh auth login` before proceeding.
        Do not attempt repo creation if gh auth status fails.
Apply to: T-00

## L-008 — Windows binary wheel availability
Discovered: T-06
Lesson: Pinning older versions of core libraries (like `numpy==1.26.4`) on
        Windows with newer Python versions (3.13+) often fails because pre-built
        binary wheels are unavailable. This triggers a source build requiring
        a C++ compiler. To avoid this, either relax the version constraint
        to allow versions with wheels or use `--only-binary :all:` to force
        binary installation where possible.
Apply to: Phase 0 setup, requirements.txt

## L-009 — PYTHONPATH for local module resolution
Discovered: T-17
Lesson: Running standalone scripts or tests from subdirectories (e.g., `tests/`)
        requires the project root to be in the `PYTHONPATH`. Without it, imports
        of local packages like `core` or `utils` will fail with
        `ModuleNotFoundError`. Use `$env:PYTHONPATH="."` (PowerShell) or 
        `set PYTHONPATH=.` (CMD) before execution.
Apply to: T-17, T-23, T-24, T-29, T-35, all testing tasks

## Session Lessons (added by owner after each build session)

## L-011 — PyQt6 Window Opacity for Fade Effects
Discovered: T-30, T-38
Lesson: To achieve a smooth fade-in/fade-out for a window, `setWindowOpacity()` must be called on the `QMainWindow` itself. Attempting to set opacity on child widgets or using graphics effects for window-level fades is often less reliable and can lead to flickering or failure to render.
Apply to: Any future fullscreen display or overlay window work.

## L-012 — Screen Index Validation
Discovered: T-33, T-38
Lesson: Always validate the `target_screen_index` against `QApplication.screens()` before attempting to move a window. If the index is out of range (e.g., trying to target a second monitor when only one is connected), the application should log a warning and fallback to the primary screen (index 0) to prevent the window from being rendered off-screen or crashing.
Apply to: T-44, T-60, any multi-monitor UI features.

## L-009 — Run tests as a module
...
Discovered: T-24
Lesson: When encountering `ImportError` in complex project structures, running `python -m pytest` is often more robust than running `pytest` directly, as it automatically includes the project root in `sys.path`.
Apply to: Any future test execution in this repository.

## L-010 — Test-implementation alignment
Discovered: T-24
Lesson: Ensure that tests import from the exact module path and function names implemented in the source files, especially after refactoring utility functions.
Apply to: Any future test file creation or refactoring tasks.

## L-008 — Regex flexibility for spoken numbers
Discovered: T-18, T-19
Lesson: Spoken Bible references are highly variable. Using non-capturing groups and flexible whitespace/separator patterns in regex is critical to catch variants like "chapter X verse Y" vs "X Y".
Apply to: Any future text-to-reference parsing tasks.

## L-009 — Test-driven development for regex
Discovered: T-23
Lesson: Regex patterns should be developed in tandem with comprehensive test suites to catch edge-case failures quickly. Test cases should cover both digit-based and word-based numbers to ensure robust parsing.
Apply to: UI development using PyQt6.

- **Lesson - PyQt6 Import Locations**: Always verify the correct module for PyQt6 classes. For example, `QAction` has moved from `PyQt6.QtWidgets` to `PyQt6.QtGui` since older PyQt5 versions. Relying on incorrect imports will cause immediate runtime errors.
Apply to: Future UI development and migration tasks.

## L-013 — Application Bundling
Discovered: Project Finalization
Lesson: For PyQt6 applications, creating a custom `spec` file is essential for ensuring all external assets (database files, configs, and models) are correctly included in the standalone executable. Using `PyInstaller` with `--add-data` ensures portability.
Apply to: Future deployments of MultiVerse.

---
*End of lessons_learned.md*

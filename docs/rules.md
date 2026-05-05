# rules.md
# MultiVerse — Global Agent Rules
# Applied across all OpenCode sessions for this project
# ─────────────────────────────────────────────────────────────────────────────

## Git Protocol
- At T-00: check git status → create GitHub repo via gh CLI if not initialised
- Repo name: multiverse | visibility: private | push immediately after creation
- Commit after LAST task of every phase using conventional commit format
- Commit format: feat:, fix:, chore:, docs: as defined in project_config.md Section 3
- Never commit with failing tests — fix first
- Never commit .env files — only .env.example is committed
- Always include .gitignore (written at T-03) before first code commit
- Push every phase commit to origin main immediately after committing
- Log every commit in workflow_state.md GIT COMMIT LOG

## Code Structure
- Prefer modular code — one responsibility per file
- Strict separation of concerns:
    core/     → business logic only, zero UI imports
    ui/       → presentation only, zero business logic
    utils/    → shared helpers only, zero domain logic
    tests/    → test code only, zero production logic
- Write clear docstrings for every module, class, and function
- Run black + isort before every phase commit

## Agent Usage
- @build   → routine tasks, clear specs, file writing, tests, scaffolding
- @architect → threading, architecture, wiring, complex debugging
- Check the AGENT column in workflow_state.md before starting every task
- Switch to @architect BEFORE writing code for @architect tasks
- Switch back to @build after every @architect task is complete
- Model names are defined in opencode.json only — do not reference them in code or logs

## Parallel Execution
- Check Section 12 of project_config.md at the start of every phase
- Spawn subagents simultaneously for tasks in defined parallel groups
- Never parallelise tasks with shared file dependencies
- Log all subagent spawns in workflow_state.md SUBAGENT ACTIVITY LOG

## Lessons
- Read lessons_learned.md at the start of every session
- Apply every relevant lesson before writing code
- Report any new patterns discovered during the build so the owner
  can add them to lessons_learned.md after the session

## Context Efficiency
- Never re-paste content from project_config.md or AGENTS.md into messages
- Reference static files by section name only
- Always place static references before dynamic content in every request
- Let OpenCode compaction handle conversation history automatically

## Safety
- Never hardcode secrets, API keys, or credentials anywhere
- Never hardcode file paths — use pathlib.Path and config.ini values
- Never import a library not in requirements.txt without asking first
- All vMix HTTP calls must have timeout=2 and graceful offline handling
- All audio and transcription processing in background threads only

## Communication
- First line of every task: ▶ T-XX — [Task Name] — @agent — [git action or NONE]
- List all files created or modified at end of every response
- State all assumptions explicitly — log them in workflow_state.md and proceed
- State which lessons from lessons_learned.md were applied
- Update workflow_state.md before ending every response
- Only stop and send the Section 9 Intervention format when an INTERVENTION
  CONDITION (project_config.md Section 0) is met — never for routine tasks

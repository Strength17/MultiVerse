# GEMINI.md
# MultiVerse — Gemini CLI Agent Instructions
# Static cache content — always load first
# ─────────────────────────────────────────────────────────────────────────────

## Session Start (Every Time)
1. Read `docs/project_config.md` fully
2. Read `docs/lessons_learned.md` fully — apply every lesson
3. Read `docs/workflow_state.md` fully — find first ⬜ task
4. Announce: `▶ R-XX — [Task Name] — @agent — [git action]`
5. Do not write code before completing steps 1–3

## Request Efficiency
- Batch ALL file reads into one tool call
- Never re-read a file already in context this session
- Think completely before making any tool call
- Minimum tool calls needed, not maximum possible

## Agent Rules
- Check AGENT column in workflow_state.md before every task
- Check and confirm that dependecies are absent before installing
- `@build` → proceed; `@architect` → switch model before writing code
- Switch back to `@build` immediately after each `@architect` task
- Rate-limited? `@build` → `@fallback`; `@architect` → `@plan` + `@fallback`
- ⚠️ Use pro/advanced model for R-08, R-15, R-16 (hardest tasks)

## Git Rules
- Phase commit after last ✅ in every phase: `git add -A && git commit && git push`
- Never commit failing tests. Fix first.
- Never commit .env — only .env.example
- Log every commit in workflow_state.md GIT COMMIT LOG

## Parallel Execution
- Check project_config.md Section 12 before each phase
- Group A (spawn simultaneously): R-03 + R-04 + R-06
- Group B (after Group A): R-07 + R-09
- Never parallelize tasks with shared file dependencies

## Lessons
- State which lessons from lessons_learned.md were applied in task announcement
- End of session: list new patterns as "SUGGESTED LESSONS FOR OWNER REVIEW"
- Never add entries to lessons_learned.md yourself unless explicitly told to

## Resume Trigger
If user says "resume", "continue build", or "continue from":
→ Read all 3 docs → find first ⬜ → begin immediately. No questions.

## Hard Rules
- Never modify `docs/project_config.md`
- Never hardcode config values — always from `config/config.ini`
- Never block PyQt6 main thread — audio/transcription/embedding in QThread
- Every function needs a docstring
- Every code block: first line is file path as comment
- Update workflow_state.md before ending every response
- All styling through `ui/styles.py` COLORS/get_stylesheet() — no inline hex values


## Loop Protocol
If the agent encounters a task that is not marked as critical/blocking (see Section 9 of project_config.md) or requiring user feedback (❓), it **must** proceed automatically through the workflow until a task is completed that requires an external Git commit (marked with ✅) or until all tasks in the phase are complete.

The agent only stops if:
1. It reaches a task that is blocked (🚫), missing prerequisites, requires irreversible action, or is marked ❓.
2. It hits a critical failure or unresolvable blocker.


## Phase Complete Checklist
After last ✅ in a phase:
1. Run git add -A && commit && push
2. Update workflow_state.md GIT COMMIT LOG
3. Print "Phase Complete Summary" block
4. Suggest `/compress` to user to preserve context

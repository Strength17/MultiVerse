# GEMINI.md
# MultiVerse — OpenCode Agent Instructions
# STATIC CACHE CONTENT — always loaded first via opencode.json instructions field
# ─────────────────────────────────────────────────────────────────────────────

## Mandatory Read Order Every Session
1. Read `project_config.md` fully — rules, tech stack, git protocol, standards
2. Read `lessons_learned.md` fully — apply every lesson before writing any code
3. Read `workflow_state.md` fully — current phase, current task, current state
4. Do not write a single line of code before completing all 

## Request Efficiency Rules
- Batch ALL file reads into one tool call — never read files one by one
- Never re-read a file already read this session
- Never re-run a command whose output is already in context
- Complete all thinking before making any tool call
- Make the minimum number of tool calls needed — not the maximum possible
- If you already know the answer from context, do not make a tool call to confirm it

## Git — First Thing At T-00
Before any code is written at T-00:
- Run `git status` to check if this folder is already a repository
- If NOT a repo: run `git init` then `gh repo create multiverse --description "Real-time scripture detection and display system for live worship via vMix NDI" --private --source=. --remote=origin --push`
- If already a repo: confirm origin is set with `git remote -v`
- Log result in workflow_state.md USER DECISIONS LOG
- If gh CLI is not installed or not authenticated: log as BLOCKER immediately

## Phase Commits
After the last task of every phase is marked ✅:
- Run `git add -A`
- Run `git commit -m "[message from phase commit table in workflow_state.md]"`
- Run `git push origin main`
- Log the commit in workflow_state.md GIT COMMIT LOG
- Never commit with failing tests

## Phase Completion Recap
After every phase completion message, always include these Top 3 Commands:
1. `/compress`: Condenses the conversation history into a summary to preserve context window and reduce token costs.
2. `/rewind`: Allows you to travel back to any point in the session to fix errors or restart from a known good state.
3. `/resume`: Opens the session browser to quickly switch between tasks or restore previous work sessions.
- **Provide a structured "Phase Complete Summary" block in the session (Phase Name, Tasks, Commit Message, Hash, Next Phase).**
- **Prompt the user to run `/clear` to reset the session context for the next phase.**

## Model Selection
- Check the AGENT column in workflow_state.md for every task
- @build tasks → use @build (default agent) — proceed automatically
- @architect tasks → switch to @architect before writing any code
- Switch back to @build after every @architect task is marked complete
- If @build is rate-limited (429) → switch to @fallback for that task
- If @architect is rate-limited (429) → use @plan for reasoning, @fallback for code
- Each agent has its own independent daily pool — exhausting one does not affect others
- Model names and pool sizes are defined in opencode.json — not referenced here

## Parallel Execution
- Check Section 12 of project_config.md before starting any phase
- If tasks are in a defined parallel group → spawn subagents simultaneously
- Log all subagent activity in the SUBAGENT ACTIVITY LOG in workflow_state.md
- Never parallelise tasks not in a defined group

## Lessons
- Read lessons_learned.md at the start of every session
- State which lessons were applied in the task start announcement
- If a new pattern or bug is discovered during the build, note it at the
  end of the session response so the owner can add it to lessons_learned.md

## Context Ordering Strategy
Always structure every request with static content first:
1. project_config.md (static — loaded via instructions, never re-paste)
2. AGENTS.md (static — loaded via instructions, never re-paste)
3. lessons_learned.md (semi-static)
4. Completed source files (semi-static)
5. workflow_state.md snapshot (dynamic)
6. Current instruction or tool result (dynamic)

Reference static files by section name only — never copy their content
into messages. Example: "per project_config.md Section 11"
Groq LPU inference is fast but context window is finite — keeping static
content loaded once via the instructions field and never re-pasting it
preserves context budget for code, tool results, and dynamic state.

## Resume Trigger
If the user's opening message contains "resume", "continue build", or "continue from":
  → Read all three files in order (project_config.md → lessons_learned.md → workflow_state.md)
  → Find the first ⬜ PENDING task in the current phase
  → Begin immediately with the one-line task announcement — do not ask "where did we stop?"
  → workflow_state.md always contains the exact resume point

## Suggested Lessons (End-of-Session Duty)
At the end of every session, after updating workflow_state.md:
  → Review every bug, workaround, unexpected behaviour, and pattern from this session
  → List each one as a SUGGESTED LESSON using the lessons_learned.md entry format
  → Label them clearly: "SUGGESTED LESSONS FOR OWNER REVIEW:"
  → The owner reviews and adds approved entries to lessons_learned.md
  → Never add entries to lessons_learned.md yourself — surface candidates only

## Hard Rules
- Never modify project_config.md
- Never hardcode config values — always read from config.ini
- Never block the PyQt6 main thread
- Every function must have a docstring
- Every code block starts with the file path as a comment on line 1
- Update workflow_state.md before ending every response
- Never commit .env files — only .env.example


### Note
- Demand that pro version model be used for T-46, T-52, and T-60.

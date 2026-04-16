---
name: save-state
description: >
  Freezes the current session — reads project state, writes all session-end files,
  resets the turn counter, outputs a single confirmation. Fully autonomous, no user
  interaction. Invoke as /save-state [project-slug]. When to trigger: at the end of
  every working session before closing; before switching to a different project; when
  mid-flight work needs to be preserved for the next session; after any significant
  milestone or decision; and whenever the user says "save state" or "wrap up." Key
  capabilities: spawns a fully autonomous subagent so zero work happens in the calling
  session, reads mid-flight files (src/, lib/, app/, backend/, etc.) to capture what
  was half-done, writes session logs, heartbeat updates, decisions records, next-session
  briefs, and STATE.md summaries. Also syncs root lessons from ~/.claude/memory/
  lessons/ into the project's memory/ dir, and fires a best-effort Pinecone upsert for
  long-term retrieval. Ideal for project directors maintaining multiple active projects
  who need reliable session continuity across context switches. Also useful for post-
  incident reviews, onboarding a colleague into a project, and feeding session data into
  a project memory or RAG system.
---

# Save State

Spawns a subagent that reads project state, scans mid-flight files, writes all session-end
files, and outputs a single confirmation. Caller spawns and waits — zero work done in the
calling session.

## SSOT: medium-term.md

The **primary source of truth** for project locations is `~/.claude/memory/medium-term.md`
— the Active Projects table. Read it FIRST.

## If Slug Not Found

1. Check `~/.claude/memory/medium-term.md` Active Projects table — the SSOT.
2. If not in medium-term.md → output:

   ```
   PROJECT NOT FOUND: {slug}
   Hint: Check ~/.claude/memory/medium-term.md for the current project list.
   ```

   **Stop. Do not fall back to other projects or search broadly.**

## Step 1 — Spawn Subagent

Use the Agent tool to spawn a general-purpose sonnet subagent. The subagent owns the
entire ritual — do not do any reading or writing yourself.

Subagent prompt:

"You own the save-state ritual for {project}. Run it completely.

PERMISSIONS: read-write-create on ALL paths below. No restrictions.

## Scope
- Project root: `{project}/`
- Memory dir: `{project}/memory/` — includes heartbeat.md, decisions.md, next-session.md, sessions/, lessons/
- State tracking: `{project}/.claude/save-state-state.json`
- Lessons root: `~/.claude/memory/lessons/`
- Lessons dir: `{project}/memory/lessons/`
- Mid-flight scan dirs: `src/`, `lib/`, `app/`, `backend/`, `frontend/src/`, `components/`, `src-tauri/src/`, `web/src/`, `api/`, `tests/`, `spec/`
- Optional project root files: `{project}/STATE.md`, `{project}/CLAUDE.md`

## Step 1 — Read Baseline
Read simultaneously:
- {project}/memory/heartbeat.md
- {project}/STATE.md (if exists)
- {project}/memory/decisions.md (if exists)
- {project}/memory/next-session.md (if exists)
- {project}/CLAUDE.md (if exists)
- {project}/.claude/save-state-state.json (if exists)
- ~/.claude/memory/lessons/*.md

Note what was being worked on, what's mid-flight, and any blockers.

## Step 2 — Find Mid-Flight Files
Scan: src/, lib/, app/, backend/, frontend/src/, components/, src-tauri/src/, web/src/, api/.
Look for TODO/FIXME comments, recently modified files, or anything half-done.
Report file paths with one-line descriptions.

## Step 3 — Write Session Log
Create or append to {project}/memory/sessions/YYYY-MM-DD.md:

## Session — YYYY-MM-DD HH:MM UTC

**was_doing**: [what was being worked on]
**just_finished**: [what completed before stopping]
**doing_next**: [specific next action]

### Mid-Flight
{format mid_flight list}

### Decisions Made
{format decisions list}

### Blockers Hit
{format blockers list}

### Notes
- [any context from this session]

## Step 4 — Update Heartbeat (overwrite Session End only)
Read {project}/memory/heartbeat.md.
OVERWRITE the Session End section. Keep Phase Status + Blockers intact.
Append only the new Session End block below the existing Phase Status + Blockers.
Old Session End blocks are NOT carried forward — they live in sessions/YYYY-MM-DD.md.

## Session End — YYYY-MM-DD HH:MM UTC

### Completed This Session
- [item from just_finished]

### In Progress
- [item from was_doing]

### Top 3 Priorities
1. [priority 1]
2. [priority 2]
3. [priority 3]

### Blockers
{format blockers list}

## Step 5 — Decisions Record
Read {project}/memory/decisions.md. Append any new decisions not already recorded.

## Step 5b — Decisions Archive (auto-prune)
After appending new decisions, count lines in {project}/memory/decisions.md.
If it exceeds 50 lines and {project}/memory/decisions-archive.md does not exist:
1. Create {project}/memory/decisions-archive.md from the existing decisions.md content
2. Keep the top 30 sections (approx 50 lines) in decisions.md — the most recent and relevant
3. Move older sections to decisions-archive.md, prefixed with "Archived YYYY-MM-DD:"
If decisions.md is already ≤50 lines, skip silently.
If decisions-archive.md already exists, skip silently (archive created once, grows only if explicitly pruned).

## Step 6 — Lessons Sync

## Step 7 — Update STATE.md (overwrite Last Session only)
Read {project}/STATE.md (create if missing).
OVERWRITE the Last Session section. Keep all prior Last Session blocks removed —
only the most recent one exists. Old sessions live in sessions/YYYY-MM-DD.md.

## Last Session: YYYY-MM-DD

### PD Status
[current status from heartbeat]

### Remaining Work
1. [doing_next]
2. [other priorities]

### Blockers
{format blockers list}

### Mid-Flight Files
{format mid_flight list}

## Step 8 — Write next-session.md
Overwrite {project}/memory/next-session.md (keep under 10 lines):

# Next Session — {project}

## Status
[current phase or status]

## Next action
[specific next step — one sentence]

## Blockers
{format blockers list}

## Mid-flight
{format mid_flight list}

## Step 9 — Reset Turn Counter
Update {project}/.claude/save-state-state.json:

{ "turn_count": 0, "last_turn_at": "[current timestamp]", "last_saved_at": "[current timestamp]", "last_session_date": "YYYY-MM-DD" }

Skip if the file doesn't exist.

## Step 10 — Confirm
Output only: save-state done!
Then stop. No further narration.

## Step 11 — Fire Pinecone Upsert (background, fire-and-forget)

After saying "save-state done!", read the session files written by the subagent:
- {project}/memory/sessions/YYYY-MM-DD.md
- {project}/memory/decisions.md
- {project}/memory/next-session.md
- {project}/memory/heartbeat.md

Build a JSON blob with: project_slug, session_date, session_log, decisions,
next_action, blockers, mid_flight, status. Then fire the upsert in the background
using Bash with `run_in_background: true`. Do NOT wait for it. Do NOT mention it
in the save-state output. It is best-effort and fails silently:

```bash
/tmp/pinecone-env/bin/python3 ~/.claude/skills/save-state/pinecone_upsert.py \
  "$(python3 -c "import json; print(json.dumps({
    'project_slug': '<project slug>',
    'session_date': '<YYYY-MM-DD HH:MM UTC>',
    'session_log': '<full session log content>',
    'decisions': '<decisions text>',
    'next_action': '<next action text>',
    'blockers': '<blockers text>',
    'mid_flight': '<mid-flight files list>',
    'status': '<current phase/status>'
  }))")"
```

If the venv is missing or the script errors, the background process dies silently — no retry, no log, no notification.

Wait for the subagent to complete. You (the caller) do nothing else.

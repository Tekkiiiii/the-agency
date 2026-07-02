# save-state full-scan ritual (SUBAGENT mode)

You are a save-state-runner. You reconstruct one project's session state from
files (the session that produced it is gone), synthesize a payload, and call
the mechanical writer script. You do NOT write session files yourself — the
script does.

Project root: `{project}/`. Memory: `{project}/memory/`.

## Step 1 — Delta check

Read `{project}/memory/agents/pd-scratch.md`; look for a `## Session Delta`
section at the bottom.

**Delta valid** = timestamp within last 2 hours AND not marked INCOMPLETE AND
passes the reality cross-check:
- Git repo: `git -C {project} status --short` → collect changed paths. Not a
  git repo: `find` the source dirs (src/, lib/, app/, backend/, frontend/src/,
  components/, src-tauri/src/, web/src/, api/) for files newer than
  pd-scratch.md.
- If changed files exist that the delta does not list → delta is NOT trusted,
  go to Step 2 (full scan).

**Delta valid:** use it as source of truth for was_doing, just_finished,
decisions, mid_flight. Read only `memory/next-session.md` (for prior Phase) and
skip Steps 2-3 reads that the delta already covers. Go to Step 4.

## Step 2 — Baseline reads (full scan)

Memory size guard: `du -sk {project}/memory` — if >2048KB, read decisions.md
with `head -n 100` only and skip decisions-archive.md entirely.

Read simultaneously:
- `memory/heartbeat.md`
- `STATE.md` (if exists)
- `memory/decisions.md` (if exists; capped per guard)
- `memory/next-session.md` (if exists)
- `CLAUDE.md` (if exists)
- `.claude/save-state-state.json` (if exists)

Mid-flight scan: check the source dirs listed in Step 1 for TODO/FIXME and
recently modified files; note path + one-line description each.

## Step 3 — Active tasks

- Read `memory/tasks/ongoing/*.md` → one line per task (title, status, next).
- Read `memory/inter-spawn-tasks/index.md` if it exists → note active
  inter-spawn tasks for the `interspawn_active` payload field.

## Step 4 — Synthesize payload + run script

Build the payload JSON (schema in SKILL.md §INLINE step 1). Rules:
- `next` MUST name a concrete target (file, task ID, action, URL, or agent).
  "continue work" is INVALID — derive a specific next action from the prior
  next-session.md, ongoing tasks, and mid-flight files.
- `phase`: from prior next-session.md unless the delta/baseline shows it moved.
- `decisions`: only decisions visibly NEW relative to decisions.md content.
- Fields with nothing to report: empty array / omit — the script writes "none".

Run:

```bash
echo '{payload}' | python3 ~/.claude/scripts/save-state.py --project {project} --payload -
```

## Step 5 — Confirm

Output only the script's `save-state done!` line (plus slug). Stop. No
narration, no file listing.

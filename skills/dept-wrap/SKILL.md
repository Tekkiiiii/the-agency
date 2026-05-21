---
name: dept-wrap
description: >
  Freezes department state at session end — writes dept-state.md, updates
  member-roster.md, flushes active-coords.md, and archives dept scratch files.
  Invoke as /dept-wrap [dept-slug] or /dept-wrap all.
  Fully autonomous, no user interaction. Parallel-safe when saving all departments.
---

# /dept-wrap

Writes all department session-end state files. Caller spawns and waits — zero work
done in the calling session.

Pairs with `/dept-resume` (session start) and `/dept-status` (read-only check).

## Department Registry

The 14 departments and their paths:

| Slug | Path | Abbr |
|------|------|------|
| career | ~/.agency/agents/career | car |
| content-creation | ~/.agency/agents/content-creation | cc |
| design | ~/.agency/agents/design | des |
| engineering | ~/.agency/agents/engineering | eng |
| game-development | ~/.agency/agents/game-development | gd |
| marketing | ~/.agency/agents/marketing | mkt |
| operations | ~/.agency/agents/operations | ops |
| paid-media | ~/.agency/agents/paid-media | pm |
| product | ~/.agency/agents/product | prd |
| project-management | ~/.agency/agents/project-management | prj |
| sales | ~/.agency/agents/sales | sal |
| spatial-computing | ~/.agency/agents/spatial-computing | spa |
| specialized | ~/.agency/agents/specialized | spc |
| testing | ~/.agency/agents/testing | tst |

## Argument Resolution

| Argument | Action |
|---|---|
| `all` | Save all 14 departments, in parallel via subagents |
| `[dept-slug]` | Save exactly one department |
| no arg | Fail with message: "Pass a dept slug or 'all'" |

## Step 1 — Read Current State

For the target department, read:
1. `{dept-path}/state/dept-state.md` — current snapshot
2. `{dept-path}/scratch/dept-scratch.md` — active session scratch (if exists)
3. `{dept-path}/scratch/coords/` — any active DC scratch files
4. `{dept-path}/state/active-coords.md` — running coord log

## Step 2 — Write dept-state.md

Overwrite `{dept-path}/state/dept-state.md` with current state. Max 20 lines:

```
dept: {dept-slug}
lead: {lead agent name}
abbr: {abbreviation}
updated: {YYYY-MM-DD HH:MM GMT+7}
active-pipelines: {comma-separated or "none"}
active-protocols: {comma-separated or "none"}
active-coords: {comma-separated DC names with state, or "none"}
open-issues: {any unresolved issues, or "none"}
member-alerts: {capacity/skill alerts, or "none"}
last-improvement: {most recent pipeline/protocol change, or "none"}
next-focus: {what the dept head should work on next session}
blockers: {any blockers, or "none"}
```

## Step 3 — Update member-roster.md

Read `{dept-path}/state/member-roster.md`. Update utilization and active task
columns based on what was observed during the session. If no changes were made
to member assignments, leave the file unchanged.

## Step 4 — Archive Scratch Files

1. If `{dept-path}/scratch/dept-scratch.md` exists → delete it (session is over)
2. If any `{dept-path}/scratch/coords/dc-*.md` files exist for completed coords → delete them
3. Leave scratch files for IN_PROGRESS coords (they'll resume next session)

## Step 5 — Promote Lessons

If any department-level lessons were learned during the session:
1. Append to `{dept-path}/memory/lessons.md` in the standard format
2. If the lesson is cross-department, also note it in `~/.agency/memory/lessons/` with a reference

## Step 6 — Output Confirmation

```
DEPT-WRAP: {dept-slug}
Updated: dept-state.md, member-roster.md
Archived: {n} scratch files
Lessons: {n} promoted
Next focus: {value from dept-state.md next-focus field}
```

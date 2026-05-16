---
name: dept-status
description: >
  Quick department status check. Reads dept-state.md and active-coords.md,
  returns a compact digest. No subagents, no side effects. Invoke as
  /dept-status [dept-slug] or /dept-status all.
---

# /dept-status

Read-only status check. Reads state files directly, outputs a compact digest.
No subagents, no writes, no spawns.

## Department Registry

| Slug | Path | Abbr |
|------|------|------|
| career | {agency-root}/agents/career | car |
| content-creation | {agency-root}/agents/content-creation | cc |
| design | {agency-root}/agents/design | des |
| engineering | {agency-root}/agents/engineering | eng |
| game-development | {agency-root}/agents/game-development | gd |
| marketing | {agency-root}/agents/marketing | mkt |
| operations | {agency-root}/agents/operations | ops |
| paid-media | {agency-root}/agents/paid-media | pm |
| product | {agency-root}/agents/product | prd |
| project-management | {agency-root}/agents/project-management | prj |
| sales | {agency-root}/agents/sales | sal |
| spatial-computing | {agency-root}/agents/spatial-computing | spa |
| specialized | {agency-root}/agents/specialized | spc |
| testing | {agency-root}/agents/testing | tst |

Replace `{agency-root}` with `~/.claude` after installation.

## Argument Resolution

| Argument | Action |
|---|---|
| `all` | Status for all departments |
| `[dept-slug]` | Status for one department |
| no arg | Fail: "Pass a dept slug or 'all'" |

## Step 1 — Read State

For each target department, read in parallel:
1. `{dept-path}/state/dept-state.md`
2. `{dept-path}/state/active-coords.md` (last 10 lines only)
3. `{dept-path}/scratch/dept-scratch.md` (if exists — means a session is active)

## Step 2 — Output Digest

**Single department format:**

```
═══ {DEPARTMENT NAME} ({abbr}) ═══
Lead: {lead name}
Updated: {timestamp from dept-state}
Active Pipelines: {list or "none"}
Active Coords: {list with state or "none"}
Open Issues: {list or "none"}
Member Alerts: {list or "none"}
Next Focus: {value}
Blockers: {value}
Session Active: {yes if dept-scratch.md exists, no otherwise}
═══════════════════════════════════
```

**All departments format (compact table):**

```
DEPARTMENT STATUS — {date}

| Dept | Lead | Pipelines | Coords | Issues | Blockers | Session |
|------|------|-----------|--------|--------|----------|---------|
| cc | CCO | 1 active | none | none | none | no |
| eng | Backend Architect | none | DC-eng-review | none | none | yes |
...

Legend: Session = dept head scratch file exists (active session)
```

## Step 3 — Flag Attention Items

After the digest, if any department has:
- `blockers` not "none" → flag with warning
- `open-issues` not "none" → flag with note
- Active coords in BLOCKED state → flag with warning
- Updated more than 7 days ago → flag as stale

```
ATTENTION:
- {dept}: BLOCKED — {blocker description}
- {dept}: STALE — last updated {date}
```

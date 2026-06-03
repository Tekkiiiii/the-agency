---
name: pd-resume
description: >
  Resume PD sessions with minimal context overhead. Reads next-session.md directly
  (no subagents), spawns PD coordinators with lean briefings. Invoke as
  /pd-resume all or /pd-resume [slug]. Optimized for context window efficiency:
  no recall subagents, no temp files, no embedded protocol duplication.
---

# /pd-resume

Fully autonomous. Reads state directly, spawns PDs with pre-digested briefings.

**Context budget principle:** save-state does the synthesis at write-time so
pd-resume pays near-zero at read-time. Every token in the PD spawn prompt
must earn its place.

## SSOT

Project registry: `~/.claude/memory/medium-term.md` — Active Projects table.
Read it FIRST. This is the ONLY project-to-path map. No hardcoded tables.

## If Slug Not Found

1. Check `~/.claude/memory/medium-term.md` Active Projects table.
2. If not found → output: `PROJECT NOT FOUND: {slug}` and stop.

## Step 1 — Resolve Targets

Accept argument: `all` | single slug | comma-separated slugs.

1. Read `~/.claude/memory/medium-term.md`
2. Parse the Active Projects table for slug → path + PD name mappings
3. Skip archived projects (listed in the Archived line)
4. If slug not found → stop with error

## Step 2 — Read Briefings Directly

For each target project, read these files in parallel using the Read tool.
**Do NOT spawn subagents.**

**Per project, read simultaneously:**
1. `{project-path}/memory/next-session.md` — the PD startup briefing
2. `{project-path}/memory/inter-spawn-tasks/index.md` — inter-spawn tasks Active Summary
3. All files matching `{project-path}/memory/inter-spawn-tasks/incoming/*.md` — unread inbound tasks
4. `{project-path}/memory/pd-structure.md` — structural contract (if exists; skip silently if not)

If next-session.md doesn't exist or is empty, use fallback:
```
Phase: unknown
Next: read project memory and assess current state
Blockers: none
```

If `inter-spawn-tasks/incoming/` has no files or doesn't exist, skip silently.

**INCOMING INTER-SPAWN TASKS (mandatory injection):**
After reading, if any files exist in `incoming/`, inject an "INCOMING INTER-SPAWN TASKS"
section into the PD spawn briefing (Step 3). Format:

```
INCOMING INTER-SPAWN TASKS ({N} unread):
- {filename}: {first line of each file — the task title or # header}
  [verbatim: first 3 lines of each file]
Active Summary (from index.md): {Active Summary section verbatim}
```

The PD MUST read and act on these at startup — the identity file contract says
"inter-spawn-tasks/incoming/ checked FIRST" and the spawn briefing must enforce it.

## Step 2.5 — Check Showcase Mode

Before spawning, test whether `~/.claude/state/pd-showcase.flag` exists.

- **If absent (default):** background spawn, no narration injection.
- **If present (showcase ON):** foreground spawn + Showcase Narration Directive
  appended to every PD briefing. Toggled via `/pd-showcase`.

Record this as `showcase_on = true | false` for use in Step 3. NOTE: if
multiple targets were resolved in Step 1 and showcase is ON, spawn them
**sequentially** (foreground spawns block) — not in parallel.

## Step 3 — Spawn PD Coordinators

Spawn one pd-coordinator per target. **All in a single message** (parallel)
WHEN showcase is OFF. When showcase is ON, spawn one at a time.

**Spawn config:**
- `subagent_type`: pd-coordinator
- `model`: opus
- `run_in_background`: `false` if `showcase_on`, else `true`

**Spawn prompt — LEAN FORMAT (do not add to this):**

```
You are PD-{slug}, resuming {project-name}.
Project: {project-path}
Tasks: {project-path}/memory/tasks/ongoing/
Inter-spawn tasks: {project-path}/memory/inter-spawn-tasks/

--- BRIEFING ---
{verbatim content of next-session.md}
---

{IF incoming inter-spawn tasks exist, append:}
--- INCOMING INTER-SPAWN TASKS ({N}) ---
{verbatim task list from Step 2 injection block}
Read and action these FIRST before any other work. Each file is at:
{project-path}/memory/inter-spawn-tasks/incoming/
---

Start the Next action immediately. On startup, read only memory/tasks/ongoing/
and memory/inter-spawn-tasks/incoming/. Your agent definition has your full
protocol and lifecycle — do not wait for additional instructions.
When done or blocked, /save-state {slug} and stop.

{IF showcase_on, append:}

--- SHOWCASE MODE ---
A live audience is watching this session. Optimize for comprehension over speed:

1. Before each tool call, write ONE short sentence explaining what you're
   about to do and why.
2. After each tool result, write ONE short sentence summarizing what you
   learned before choosing the next step.
3. When deciding between approaches, narrate the trade-off out loud
   ("I could either X or Y — going with X because...").
4. When you finish a phase (research, planning, implementation, verification),
   call it out explicitly so the audience knows where you are.

Keep narration tight — one sentence each, no lectures. The audience reads
your tool calls; you just connect the dots.
--- END SHOWCASE MODE ---
```

**IF pd-structure.md exists and was read, inject into spawn prompt:**
```
--- STRUCTURAL CONTRACT ---
{verbatim content of pd-structure.md}
---
```

**What is NOT in the spawn prompt (already in pd-coordinator agent definition):**
- PD Standard Protocol (decompose → parallelize → report)
- Agent Selection Hierarchy
- Decomposition guide (L1→L3)
- Coord spawn template
- QA gate protocol
- ACK/NACK reference
- Status log format
- Escalation protocol

**What is NOT in the spawn prompt (available on-demand via file read):**
- PD Directory / cross-project paths (medium-term.md — read only for inter-spawn)
- Project CLAUDE.md (read only if PD needs project-specific config)
- Historical sessions (sessions/*.md — never read at startup)

## Step 4 — Output Summary

After all PDs are spawned:

```
PD RESUME — {n} projects

{slug} — {phase} — spawned
  next: {next action}
  blockers: {blockers or "none"}

[...one per project...]

{IF showcase_on:} Showcase MODE — PDs are running in the foreground. Tool calls and narration stream into this session live.
{ELSE:} All PDs running in background. Progress arrives via SendMessage.
```

Then stop. Do not poll or wait.

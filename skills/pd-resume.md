---
name: pd-resume
description: >
  Resume all Product Directors (PDs) with context pre-loaded — launches each PD
  for every active project simultaneously with their session briefing already
  inserted. Each PD reads its own save-state files (heartbeat, decisions,
  next-session.md), formulates a 6-line briefing, and immediately begins working.
  Trigger: start of session after /recall. Or invoke /pd-resume to restart all
  paused PDs across all projects. Key capabilities: parallel PD spawning across
  N projects in seconds, per-project briefing so each PD knows exactly where
  things left off, automatic heartbeat refresh so other agents can see PD status,
  and clean handoff with no re-derivation of state needed. Also for: catching
  a stalled project up to current state, onboarding a new project to the PD
  protocol, and restarting all work after a break. Not for: resuming a single
  project (use /recall instead), or running commands directly (use Claude Code
  directly).
---

# /pd-resume — Resume All Product Directors

Resume all active PDs across every project simultaneously, with each PD's
session briefing already pre-loaded so they begin work immediately.

## When to Activate

Trigger `/pd-resume` when:
- Starting a fresh session — first action after connecting
- Restarting all paused PDs after a break
- Catching a stalled project up to current state

For resuming a **single** project, use `/recall` instead.

## Prerequisites

Each project must have these files for the PD to function:
- `PROJECT.md` — project metadata
- `memory/heartbeat.md` — last pulse
- `memory/decisions.md` — key decisions
- `memory/next-session.md` — what to tackle next

## Instructions

### Step 1: Discover Active Projects

Read the active projects table from `~/.claude/memory/medium-term.md`:

```bash
grep -A 50 "Active Projects" ~/.claude/memory/medium-term.md
```

This gives you each project's:
- Name
- Location
- Tech stacks
- Last active date

### Step 2: Gather PD Briefing for Each Project

For each active project, read its save-state files in parallel:

```bash
# Per project, read these three files concurrently:
cat {project}/memory/heartbeat.md
cat {project}/memory/decisions.md
cat {project}/memory/next-session.md
```

Synthesize a 6-line briefing for each PD:
```
[Project name] — [Last active: X days ago]
NOW: [What's currently in progress]
NEXT: [What to tackle first]
BLOCKERS: [What stopped progress last time]
STACKS: [Tech stacks involved]
SIGNALS: [Any new context from recent work]
```

### Step 3: Spawn All PDs in Parallel

For each active project, spawn a PD sub-agent with:
- `project`: the project directory path
- `project_name`: the project's human-readable name
- `briefing`: the 6-line synthesized briefing from Step 2
- `memory_path`: path to the project's memory directory

**Spawn command:**
```
For each project:
  /spawn pd-agent
    project={project_path}
    briefing={6-line briefing}
```

Use the subagent type: `general-purpose`
Use model: `sonnet`
Set timeout: no limit

### Step 4: Monitor Initial Spawn

After spawning all PDs, wait for each to send an initial status message.
A PD that doesn't respond within 60 seconds of spawning is likely waiting on
a missing file or blocked on a decision. Check its project directory and
resend with updated context.

### Step 5: Run /recall for Each Project

Run `/recall` for each project to ensure lessons are synced and state is
fresh. This runs the full recall protocol per project.

## PD Briefing Format

Each PD briefing should follow this format exactly:

```
PROJECT: {name}
LAST ACTIVE: {relative time}
NOW: {current work in progress}
NEXT: {immediate next action}
BLOCKERS: {what stopped progress, or "none"}
STACKS: {comma-separated tech stacks}
SIGNALS: {new context, decisions made, handoff notes}
```

## Spawning Rules

- Spawn ALL active project PDs simultaneously — do not spawn sequentially
- Each PD is independent — they do not need to wait for each other
- If a project has no memory files yet, spawn the PD anyway — they'll do
  a first-run setup
- If a project directory doesn't exist, skip it and note which projects
  couldn't be resumed

## Important Rules

- **Parallel spawning only.** Do not spawn one PD, wait for it, then spawn
  the next. Spawn all at once.
- **Pre-loaded briefing means no re-derivation.** The PD should begin work
  immediately without reading files first — you've already done that work.
- **/recall runs per project after spawning.** This ensures lessons are synced
  and state is fresh.
- **If a PD goes silent**, check the project directory for missing files
  and resend with corrected context.
- **No hard limit on concurrent agents.** The platform handles parallel
  spawning efficiently — spawn all at once.

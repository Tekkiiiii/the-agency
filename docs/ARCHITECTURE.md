# Architecture

## Overview

The Agency is a multi-agent command center built on Claude Code. It runs autonomously between sessions, coordinating work through a file-based memory and task system.

```
┌─────────────────────────────────────────────────────────────┐
│                      User (you)                            │
│                  Claude Code + agency CLI                  │
└──────────────────────────┬────────────────────────────────┘
                           │
        ┌─────────────────┼─────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼────┐     ┌─────▼─────┐
   │  Task   │      │ Memory   │     │   NEXUS   │
   │ Store   │      │ System   │     │ Handoffs  │
   │ SQLite  │      │ Sessions │     │           │
   └─────────┘      └──────────┘     └───────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
        ┌─────▼────┐  ┌───▼───┐    ┌────▼────────┐
        │  PD per  │  │Skills │    │ Inter-Agent │
        │ Project  │  │Library│    │ Coordination│
        └──────────┘  └───────┘    └─────────────┘
```

## Core Components

### Task Store (SQLite)
Source of truth for pipeline state. All agents read/write here.
- `~/.claude/task-store.db`
- Schema: tasks with status, blocked_by, gate_status, retry_count

### Memory System
Persistent context across sessions:
- `~/.claude/sessions/{project}/` — session logs
- `~/.claude/projects/{project}/STATE.md` — project state
- `~/.claude/lessons/` — lessons learned
- `~/.claude/decisions/` — architectural decisions

### NEXUS Protocol
File-based handoff system for inter-agent coordination:
- Handoff documents with full context
- Phase 0–5 coordination doctrine
- Quality gates before every handoff

### Skills
Reusable workflow procedures invoked via `/skill-name`:
- Loaded from `~/.claude/skills/`
- Registered in `~/.claude/skills/INDEX.md`
- Can be installed from the agency catalog

### Project Directors (PDs)
Each project has a dedicated PD agent that:
- Owns the project from spec to ship
- Maintains the task pipeline
- Reports to team-lead
- Persists state via memory system

## Data Flow

1. **User** spawns a project or assigns work
2. **PD** creates tasks in task store, assigns to specialists
3. **Specialists** execute, write session logs, gate tasks
4. **PD** monitors pipeline, escalates blockers
5. **On session end**: `/save-state` writes session log
6. **Next session**: agent reads memory, resumes

## Extensibility

The system is designed to be extended:

- **New skills**: drop in `skills/` directory, register in INDEX.md
- **New agents**: add agent spec in `core/agents/` and copy to `~/.claude/agents/{department}/` — see `docs/DEVELOPER.md`
- **New projects**: run `agency init --project name`
- **Custom coordination**: add rooms in `{agency-root}/agency-rooms/` — see `docs/ROOMS.md`

---

## Tiered Agent Architecture

The system uses a 4-tier chain. Each agent stops at its termination level.

```
PD  (L1→L3 decomposition, spawns Coords)
 └── Coord × N  (L3→L4→L5→L6, spawns Exec or Mini-Coord, autonomous)
      └── Mini-Coord × M  (L6→L7→L8→L9, spawned for complex L6 tasks, reports to parent Coord)
           └── Task-Executor × K  (executes exactly one atomic unit, reports to spawner)
```

| Layer | Agent | Decomposes | Spawns | Model |
|-------|-------|-----------|--------|-------|
| L1–L3 | PD | L1 → L2 → L3 | Coord | Opus |
| L3–L6 | Coord | L3 → L4 → L5 → L6 | Exec or Mini-Coord | Opus |
| L6+ | Mini-Coord | L6 → L7 → L8 → L9... | Exec | Opus |
| Atomic | Task-Executor | No | — | Sonnet |

### Naming Convention

- PD = `PD-{slug}` — project-level orchestrator (e.g. `PD-my-saas-app`)
- Coord = `Coord-{l3-name}-{pun}` — L3 owner (e.g. `Coord-auth-Gatekeeper`)
- Mini-Coord = `Mini-{l3-name}-{pun}-{branch}` — L6 owner (e.g. `Mini-auth-Gatekeeper-loginFlow`)
- Exec = `Exec-{task}-{pun}` — implementation unit (e.g. `Exec-login-Keymaster`)

### Decomposition Rules

| Level | Who | Stops At |
|-------|-----|---------|
| L1 | PD | L3 |
| L3 | Coord | L6 |
| L6 | Mini-Coord | Smallest implementable unit |
| Atomic | Task-Executor | — |

### PD Standard Protocol

Every Project Director follows a mandatory 3-rule protocol:

1. **Decompose** — break every task into the smallest independent sub-tasks before acting
2. **Parallelize** — spawn one subagent per sub-task simultaneously
3. **Report** — send each completion to team-lead immediately (not at the end)

This protocol applies to every PD spawn, every time, without exception.

---

## Quality Gates (ACK/NACK Protocol)

Every agent-to-agent handoff has a mandatory QA gate before approval:

| Handoff | Reporter | Reviewer | ACK condition | NACK condition |
|---------|----------|----------|---------------|----------------|
| Exec → Coord | Exec sends DONE + QA | Coord reviews QA report | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| Coord → PD | Coord sends L3 complete + QA | PD reviews Coord QA report | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| PD → root | PD sends final digest + QA | root (operator) | Explicit ACK | Explicit NACK with fix list |

**ACK** = "looks good, die quietly" → reporting agent deletes scratch and stops
**NACK** = "fix: [list]" → reporter fixes → re-runs QA gate → re-reports

### PD-Level Pre-Aggregate QA Gate

After all Coords report DONE, PD spawns `Coord-qa-Canary` (Sonnet, Testing Lead) to QA the combined L3 output before reporting to root.

Deliverables:
- Health score (0–100 integer)
- Issues by severity (CRITICAL/HIGH/MEDIUM/LOW)
- Screenshots in `{project}/memory/qa/screenshots/`
- Report at `{project}/memory/qa/qa-report-final-{timestamp}.md`

---

## Skills Library

The repo ships with ~45 agency-core skills (domain skills install separately) covering the full project lifecycle:

| Category | Skills |
|----------|--------|
| Memory | `save-state`, `recall`, `pd-resume`, `project-status`, `wrap` |
| Coordination | `swarm`, `delegate`, `room-manager`, `nexus-gatekeeper` |
| Ops | `self-healing`, `investigate`, `guard`, `task-store` |
| Planning | `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `office-hours`, `retro` |
| Execution | `ship`, `land-and-deploy`, `setup-deploy`, `canary`, `qa` |
| Quality | `design-review`, `codex`, `cso`, `qa-only`, `document-release`, `superpowers-qa-only` |
| Engineering | `backend`, `frontend`, `tech-writer`, `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy` |

## Technology

- **Runtime**: Claude Code (Anthropic)
- **Task Store**: SQLite (zero-dependency)
- **Memory**: filesystem (markdown files)
- **Coordination**: NEXUS file protocol + Agency Rooms
- **Skills**: markdown-based skill definitions

---

## Agency Rooms

File-based inter-agent chat system for persistent coordination between agents.

```
{agency-root}/agency-rooms/{room}/
├── messages.mdl        # Append-only message log
├── room.json           # Room metadata and member list
├── members.json        # Active members
├── handoffs/           # Pending NEXUS handoffs (JSON)
└── context/
    ├── shared.md       # Extracted DECIDED/ACTION/QUESTION items
    └── rolling.md      # Dept head status feed (dept rooms only)
```

Room types:
- **Project rooms** — one per active project, owned by the project's PD
- **Department rooms** — one per department (engineering, testing, etc.)
- **Oversight room** — `project-oversight/` aggregates all PD statuses

RoomManager polls rooms on a configurable interval. Run with `/room-manager`.

---

## Inter-PD Filesystem Protocol

PDs coordinate via the filesystem, not SendMessage (background agents cannot receive messages).

1. PD-A writes briefing to: `{target-project}/memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md`
2. PD-A creates tracker: `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`
3. PD-A spawns PD-B via Agent tool with `run_in_background: true`
4. PD-B completes work, appends completion to caller's `delegated-{task-id}.md`
5. On next `/pd-resume`, PD-A reads completion and marks task done

Use `/pd-spawn` for the full protocol.

---

## PD Boot Sequence (Lazy Loading)

Target: ~500 tokens on spawn.

**On spawn:**
1. Read `{project}/.claude/PD-BRIEFING.md` (pre-built per-project routing doc)
2. Read `{project-root}/memory/heartbeat.md` (log session start)
3. Proceed immediately

**On route (only when delegating):**
1. Check PD-BRIEFING for a pre-written routing entry
2. If not found, load `{agency-root}/agents/{department}/INDEX.md` (one dept only)
3. Spawn agent directly

See `core/runbooks/pd-boot-sequence.md` for the full protocol.

---

## Status Loop Prohibition

Automated recurring status loops are **disabled by design**. Do not implement periodic status pings.

**Reason:** Naive 15-minute status loops generate 10k–21k reports/week without aggregation, causing token explosion. Instead:
- PDs write to `pd-status-live.md` (append-only)
- The main session reads it **on demand**
- Use `/swarm` for portfolio-wide status checks when needed

---

## Project Scope Management

Each active project can define a `scope.json` at `{project-root}/scope.json`:

```json
{
  "directories": ["src/", "docs/"],
  "departments": ["engineering", "testing"],
  "financialImportance": "medium",
  "directorId": "{project}-pd"
}
```

**Authority tiers:**
| Tier | Scope | Approver |
|------|-------|----------|
| 1 | <10 line edits, read-only, docs | PD (self-approve) |
| 2 | Code >10 lines, new files | Parent AI |
| 3 | Deploy, secrets, destructive | Human operator |

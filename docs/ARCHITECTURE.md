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
- `~/.agency/task-store.db`
- Schema: tasks with status, blocked_by, gate_status, retry_count

### Memory System
Persistent context across sessions:
- `~/.agency/sessions/{project}/` — session logs
- `~/.agency/projects/{project}/STATE.md` — project state
- `~/.agency/lessons/` — lessons learned
- `~/.agency/decisions/` — architectural decisions

### NEXUS Protocol
File-based handoff system for inter-agent coordination:
- Handoff documents with full context
- Phase 0–5 coordination doctrine
- Quality gates before every handoff

### Skills
Reusable workflow procedures invoked via `/skill-name`:
- Loaded from `~/.agency/skills/`
- Registered in `~/.agency/skills/INDEX.md`
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
- **New agents**: add agent spec in `agents/` directory
- **New projects**: run `agency init --project name`
- **Custom coordination**: add rooms in `~/.agency/rooms/` — see `docs/ROOMS.md`

## PD Standard Protocol

Every Project Director follows a mandatory 3-rule protocol (see `core/PD_PROTOCOL.md`):

1. **Decompose** — break every task into the smallest independent sub-tasks before acting
2. **Parallelize** — spawn one subagent per sub-task simultaneously
3. **Report** — send each completion to team-lead immediately (not at the end)

This protocol applies to every PD spawn, every time, without exception.

## Skills Library

The repo ships with 32 skills covering the full project lifecycle:

| Category | Skills |
|----------|--------|
| Memory | `save-state`, `recall`, `pd-resume`, `project-status` |
| Coordination | `swarm`, `delegate`, `room-manager` |
| Ops | `self-healing`, `investigate`, `guard` |
| Planning | `autoplan`, `plan-ceo-review`, `plan-eng-review`, `office-hours`, `retro` |
| Execution | `ship`, `land-and-deploy`, `setup-deploy`, `canary`, `qa` |
| Quality | `design-review`, `codex`, `cso`, `qa-only`, `document-release` |
| Engineering | `backend`, `frontend`, `tech-writer`, `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy` |

## Technology

- **Runtime**: Claude Code (Anthropic)
- **Task Store**: SQLite (zero-dependency)
- **Memory**: filesystem (markdown files)
- **Coordination**: NEXUS file protocol
- **Skills**: markdown-based skill definitions

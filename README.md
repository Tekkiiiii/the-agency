# The Agency

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)
![Cloud: Zero dependencies](https://img.shields.io/badge/Cloud-Zero%20Dependencies-green)
![Skills: 48](https://img.shields.io/badge/Skills-48-orange)
![Agents: 245+](https://img.shields.io/badge/Agents-245%2B-purple)
![QA: Gates on every handoff](https://img.shields.io/badge/QA-Gates%20%2B%20Health%20Scores-red)

**Self-running AI workforce. PD-driven task decomposition, mandatory QA gates, SQLite persistence — no servers, no API keys.**

---

## TL;DR — Get started in 60 seconds

```bash
git clone https://github.com/the-agency/the-agency.git
cd the-agency && npx agency init

agency new my-app "Build a task manager"

# In Claude Code, open your project directory and type:
/recall my-app
```

That's it. The PD loads and asks what to build. You supervise; it executes.

---

## What it does

The Agency runs autonomous multi-agent workflows on Claude Code. A **Project Director (PD)** owns each project end-to-end — decomposing work, coordinating specialists, gating quality at every handoff, and persisting everything to disk. Sessions survive restarts.

**Your job is to supervise, not micromanage.** You set direction and review key decisions. The PD handles execution, coordination, and state.

## What you'll actually do — Day 1

Open Claude Code in your project directory and talk to the PD like a teammate:

```
You:  "Build a REST API for a task manager with JWT auth"
PD:   "Got it. Decomposing into tasks. Spawning specialists."
      → Auth specialist starts, Database specialist starts, API specialist starts (parallel)
PD:   "Phase 1 complete — auth + DB done, API in review. Starting Phase 2."

You:  /save-state

// Come back tomorrow
You:  /recall my-app
PD:   "Phase 1 complete. Phase 2 in progress — 2 of 5 tasks done. Continuing."
```

## Key Features

- **4-tier autonomous chain**: PD → Coord → Mini-Coord → Task-Executor decomposes any project to atomic units. Mini-Coords keep drilling L6→L7→L8 without escalating to PD.
- **QA gates on every handoff**: No work gets ACK'd without a health-score pass. Gate: score ≥ 70 + zero CRITICALs. Example: 70 = tests pass but docs missing; 90+ = ship-ready.
- **Explicit ACK/NACK protocol**: Agents wait for approval before stopping. NACKs return a fix list. Rejected work loops back through QA. Traceability is built into the protocol.
- **40+ production-ready skills**: Memory, execution, QA, engineering, governance — all invoked via `/skill-name`. Full project lifecycle covered.
- **SQLite task store — nothing leaves your machine**: Task pipeline, gates, retries, blocking in `~/.claude/`. No servers. No API keys.
- **Session persistence**: `/save-state` and `/recall` make Claude Code fully resume-capable. Come back days later; the PD shows you exactly where it left off.
- **Agency Rooms** — file-based inter-agent chat with persistent rooms, RoomManager polling, NEXUS JSON handoffs, and 12-hour department digests.
- **Inter-PD Protocol** — PDs coordinate via filesystem, not messaging. Delegation through `inter-spawn-tasks/` directories with completion tracking.
- **PD Boot Sequence** — lazy-loading spawn targeting <500 tokens. Per-project PD-BRIEFING.md for instant routing.
- **Status Loop Prohibition** — no automated ping loops. On-demand status via append-only `pd-status-live.md`.
- **Project Scope Management** — `scope.json` per project with 3-tier authority model (PD self-approve → parent AI → human).

## Architecture

```
YOU (Claude Code terminal)
  ├── agency CLI          ← control panel: init, new, tasks
  ├── /slash commands     ← skills you invoke
  └── PD + Specialists    ← agents that do the work

PD's toolkit:
  ├── SQLite task store   ← what needs building, what's blocked
  ├── Memory filesystem   ← decisions, session history
  ├── NEXUS protocol      ← how agents hand off (PD manages, you don't touch it)
  └── Agency Rooms        ← file-based inter-agent chat, 12-hour department digests

Spawn chain (who creates whom):
  PD → Coord → Mini-Coord → Task-Executor
  (one per project) (one per workstream) (one per complex task) (one per atomic unit)

QA gates at every level:
  Task-Executor output → Mini-Coord QA → Coord QA → PD acceptance gate
  Gate criteria: health score ≥ 70 + zero CRITICALs before ACK
```

## Quick Start

```bash
# 1. Install (requires Node.js 18+ and Claude Code)
git clone https://github.com/the-agency/the-agency.git
cd the-agency && npx agency init

# 2. Create a project
agency new my-app "Build a task manager"

# 3. Open Claude Code in your project directory, then type:
/recall my-app
# The PD loads. Tell it what to build.

# When done for the day:
/save-state
# Everything persists. Next session picks up exactly where you left off.
```

## Core Concepts

### Task Store

SQLite pipeline at `~/.claude/task-store.db`. Created automatically by `agency new`. Track progress with:

```bash
agency status my-app          # see project status
# or from inside Claude Code:
/task-store                   # full task management via the /task-store skill
```

Schema:

| Field | Values | What it means |
|---|---|---|
| `status` | `pending` \| `in_progress` \| `blocked` \| `done` \| `failed` | The PD moves tasks through these states |
| `blocked_by` | `["task-id"]` | Task won't start until these finish first |
| `gate_status` | `open` \| `passed` \| `failed` | QA gate — must pass before `done` |
| `retry_count` | integer | Auto-retries up to `max_retries` on failure |

> **Note:** `agency tasks` CLI commands are coming soon. In the current release, task management is handled by the PD and the `/task-store` skill.

### Memory Layers

Seven layers, each serving a different purpose:

| Layer | Location | Created by |
|---|---|---|
| Sessions | `~/.claude/sessions/{project}/` | `/save-state` |
| State | `~/.claude/projects/{project}/STATE.md` | PD auto-updates |
| Lessons | `~/.claude/lessons/{stack}.md` | After corrections |
| Decisions | `~/.claude/decisions/` | Team Lead |
| Inter-PD tasks | `inter-spawn-tasks/` | Filesystem-based inter-PD coordination |
| Live status | `pd-status-live.md` | Append-only status log (no ping loops) |
| Agency Rooms | `agency-rooms/` | Persistent inter-agent chat and digests |

### NEXUS Protocol

Six-phase structured handoff for inter-agent coordination. **You never touch NEXUS files — the PD manages them.**

```
Register → Brief → Work → Handoff → Review → Archive
```

Every handoff carries: what's done, what's next, health score, and acceptance evidence.

### Project Directors

Spawned via `/recall {project}`. Owns the project end-to-end:

1. Decompose work into tasks
2. Assign to specialists via Coord/Mini-Coord chain
3. Gate completed work against QA criteria
4. Escalate blockers
5. Persist state via `/save-state`

## Skills Library

**Memory & Session**: `/save-state`, `/recall`, `/pd-resume`, `/wrap`, `/unwrap`, `/project-status`

**Coordination**: `/swarm`, `/delegate`, `/pd-spawn`, `/room-manager`, `/room-manager-digest`, `/task-store`, `/task-handoff`, `/project-expansion-scout`

**Planning**: `/autoplan`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/office-hours`, `/retro`

**Execution**: `/ship`, `/land-and-deploy`, `/setup-deploy`, `/canary`, `/document-release`

**Quality**: `/qa`, `/qa-only`, `/guard`, `/investigate`, `/self-healing`, `/codex`, `/cso`, `/design-review`

**Engineering**: `/backend`, `/frontend`, `/tech-writer`, `/github-deploy`, `/railway-deploy`, `/vercel-deploy`, `/supabase-deploy`

Full registry: `skills/INDEX.md` — 41 skills.

## File Structure

```
the-agency/
├── core/
│   ├── agents/          # PD/Coord/Exec/Mini-Coord templates
│   ├── runbooks/        # Boot sequence, escalation, kickoff protocols
│   ├── ORG.md           # Org chart and authority model
│   ├── memory/          # Memory system specification
│   ├── nexus/           # NEXUS coordination protocol
│   ├── tasks/           # Task store pattern
│   └── bootstrap/       # Init scripts
├── cli/                 # Node.js CLI (agency init/new/tasks/skill/status)
├── docs/                # User-facing documentation
├── skills/              # 48 agency-core skills
└── plans/               # Architecture decision records
```

## Contributing

New skills are just markdown files. Create `skills/my-skill.md`:

```markdown
---
name: my-skill
description: Does X
category: tools
---

# My Skill

Use when you need X.

## Steps
1. First do this
2. Then do that
```

Register in `skills/INDEX.md`, then invoke with `/my-skill`.

## License

MIT — use it however you want.
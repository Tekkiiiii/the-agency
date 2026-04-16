# The Agency

**[Technical documentation — for developers]**

*The non-technical version is in [README.simple.md](README.simple.md)*

---

A multi-agent command center that runs on Claude Code. Agents coordinate across sessions through a file-based memory system, task pipeline, and NEXUS handoff protocol.

No cloud services. No running processes. Just a git repo, a task store, and agents that remember.

## What it is

The Agency is a system for running autonomous AI agent workflows. It provides:

- **Task store**: SQLite-based pipeline state with gates, retries, and blocking
- **Memory layers**: Sessions, project state, lessons, cross-project decisions
- **NEXUS protocol**: Structured handoff system for inter-agent coordination
- **Project Directors (PDs)**: One agent owns each project end-to-end
- **Skill library**: Reusable workflows invoked via `/skill-name`
- **CLI**: `agency init`, `agency new`, `agency tasks`, `agency skill install`

## Architecture

```
User (Claude Code)
  ├── CLI (agency init / agency new / agency tasks)
  ├── Skills (/save-state, /recall, /swarm, /delegate, ...)
  └── Agents
        ├── Project Director (owns one project)
        │     ├── Breaks work into tasks
        │     ├── Assigns to specialists
        │     ├── Gates completed work
        │     └── Updates state
        ├── Specialist (executes work)
        └── Team Lead (coordinates across projects)
              └── Council (BOD — optional governance layer)

Task Store (SQLite)
Memory System (filesystem)
NEXUS Handoff Protocol (files)
```

## Installation

```bash
git clone https://github.com/the-agency/the-agency.git
cd the-agency
npx agency init
```

## Quick start

```bash
# Create a project
agency new my-app "Build a task manager"

# In Claude Code
/recall my-app
# → loads project state, recent sessions, relevant lessons

# Do work, then end session
/save-state
# → persists session log, updates project state

# Spawn parallel agents for independent workstreams
/swarm
# → run multiple specialists in parallel

# Delegate to a specialist
/delegate
# → hand off with full context and acceptance criteria
```

## Core concepts

### Task Store

Every task in `~/.agency/task-store.db`. Schema:

| Field | Purpose |
|---|---|
| `status` | `pending` \| `in_progress` \| `blocked` \| `done` \| `failed` |
| `blocked_by` | JSON array of task IDs that must complete first |
| `gate_status` | `open` \| `passed` \| `failed` — quality gate before done |
| `retry_count` | Auto-retry up to `max_retries` times |

Example:

```bash
sqlite3 ~/.agency/task-store.db \
  "INSERT INTO tasks (project_slug, task_name, priority) VALUES ('my-app', 'Auth module', 'high');"
```

### Memory System

| Layer | Location | Created by |
|---|---|---|
| Sessions | `~/.agency/sessions/{project}/` | `/save-state` |
| State | `~/.agency/projects/{project}/STATE.md` | PD |
| Lessons | `~/.agency/lessons/{stack}.md` | After corrections |
| Decisions | `~/.agency/decisions/` | Team Lead |

### NEXUS Protocol

Six-phase coordination:

1. **Register** — create project structure and first task
2. **Brief** — assign work with full context
3. **Work** — execute, document incrementally
4. **Handoff** — transfer with evidence and acceptance criteria
5. **Review** — gate against criteria, pass or fail
6. **Archive** — close out and record lessons

### Project Directors (PDs)

Every project has a PD agent that owns it. The PD:
- Creates tasks in the task store
- Assigns to specialists
- Monitors the pipeline
- Escalates blockers
- Persists state via `/save-state`

PDs spawn on session start via `/recall {project}`.

### Skills

Skills are markdown files that define reusable workflows. They're invoked via slash command.

Core skills — installed by default:
- `/save-state` — persist session to memory
- `/recall` — load project state from memory
- `/pd-resume` — resume all active PDs at session start
- `/swarm` — spawn parallel agents
- `/delegate` — hand off to specialist
- `/self-healing` — diagnose and fix broken workflows

Expanded library (27+ skills, all in this repo):
```bash
agency skill install ship          # automated PR workflow
agency skill install qa           # iterative QA + bug fix
agency skill install canary       # post-deploy monitoring
agency skill install plan-ceo-review   # CEO-level plan review
agency skill install backend      # API and database design
agency skill install frontend    # React/web UI
agency skill install cso         # security audit
# ...and 20 more
```

## File structure

```
the-agency/
├── core/               # Core system (owned by the agency)
│   ├── agents/         # Agent templates (PD, Specialist, Team Lead)
│   ├── memory/         # Memory system documentation
│   ├── tasks/          # Task store schema and patterns
│   ├── nexus/          # NEXUS coordination protocol
│   ├── PD_PROTOCOL.md  # PD Standard Protocol (decompose/parallelize/report)
│   └── bootstrap/      # Initialization system
├── skills/             # Skills library (27+ skills, add yours here)
│   ├── INDEX.md        # Skill registry
│   ├── save-state.md
│   ├── recall.md
│   ├── pd-resume.md
│   ├── ship.md
│   └── ...
├── docs/               # User documentation
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   ├── DEVELOPER.md
│   ├── ROOMS.md        # Agency Rooms — file-based inter-agent chat
│   └── ...
├── cli/                # agency CLI tool
│   ├── bin/agency.js
│   └── commands/
├── README.md            # This file
└── README.simple.md    # Non-technical version
```

## Extending the system

### Add a skill

Create `skills/my-skill.md`:
```markdown
---
name: my-skill
description: Does X
category: tools
---

# My Skill

Use when you need to do X.

## Steps

1. First do this
2. Then do that
```

Register in `skills/INDEX.md`, then invoke with `/my-skill`.

### Add an agent

Create `core/agents/my-agent.md` with frontmatter + instructions. Spawn via `Agent()` in Claude Code.

### Custom coordination

Add rooms in `~/.agency/rooms/{project}/` with `messages.mdl` and `shared.md` for file-based inter-agent communication.

## Technology

- **Runtime**: Claude Code (Anthropic)
- **Task Store**: SQLite (zero external dependencies)
- **Memory**: Filesystem (markdown files)
- **Coordination**: NEXUS file protocol
- **Skills**: Markdown-based
- **CLI**: Node.js 18+

## License

MIT — use it however you want.
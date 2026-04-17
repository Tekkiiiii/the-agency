# Developer Guide

## Project Structure

```
the-agency/
├── core/                # Core system files
│   ├── agents/         # Agent templates (PD, Coord, Mini-Coord, Task-Executor)
│   ├── memory/         # Memory system documentation
│   ├── tasks/          # Task store schema and patterns
│   ├── nexus/          # Coordination protocol
│   └── bootstrap/       # Bootstrap system
├── skills/             # Skills library
├── docs/               # Documentation
└── cli/                # CLI tool
```

## Quick Start

### Clone and Install

```bash
git clone https://github.com/the-agency/the-agency ~/the-agency
cd ~/the-agency
npm install   # optional — CLI is plain Node.js
```

### Initialize the Agency Runtime

```bash
node cli/bin/agency.js init
```

This creates `~/.agency/` on your machine with:
- `skills/` — skills library (34+ skills)
- `task-store.db` — SQLite task pipeline
- `sessions/` — session logs
- `lessons/` — lessons learned
- `decisions/` — architectural decisions

### Create a New Project

```bash
agency new my-project
```

This scaffolds `~/.agency/projects/my-project/` with:
- `memory/` — state, heartbeat, next-session, sessions, lessons
- Agent prompts and task folders

### Register for /pd-resume

Once your project is set up, register it for autonomous resume:

```
/pd-resume my-project
```

On first run, the PD creates its memory structure. On subsequent runs, it reads
`memory/next-session.md` and picks up where it left off.

---

## Adding a Skill

A skill is a markdown file that defines a workflow.

### 1. Create the skill file

```markdown
---
name: my-skill
description: Does X for any project
---

# My Skill

Use this when you need to do X.

## Steps

1. First do this
2. Then do that
3. Finally verify

## Tips

- Tip 1
- Tip 2
```

### 2. Register it

Add to `skills/INDEX.md`:
```markdown
| my-skill | Does X for any project | Skills |
```

### 3. Use it

In Claude Code:
```
/my-skill
```

---

## Adding an Agent

Agents are defined in `core/agents/{name}.md`.

### Agent frontmatter

```yaml
---
name: my-agent
description: What it does
department: engineering
role: specialist
reports_to: project-director
modelTier: sonnet
color: "#8B5CF6"
skills:
  - save-state
  - recall
---
```

### Agent model tiers

| Tier | Model | Use for |
|------|-------|---------|
| `sonnet` | Claude Sonnet | Fast, one-shot, no approval permission |
| `opus` | Claude Opus | Complex reasoning, decomposition authority |

---

## Tiered Agent Chain

The PD → Coord → Mini-Coord → Executor chain:

```
PD  (decomposes L1 → L3, spawns Coords)
 └── Coord  (decomposes L3 → L6, spawns Exec or Mini-Coord)
      └── Mini-Coord  (decomposes L6 → L7+, spawns Exec)
           └── Task-Executor  (executes one atomic unit)
```

See `docs/ARCHITECTURE.md` for the full protocol including ACK/NACK QA gates.

---

## Creating a Project Template

Copy `core/projects/template/` to `projects/{name}/` and customize.

---

## Extending the Task Schema

The task store is SQLite. To add columns:

```sql
ALTER TABLE tasks ADD COLUMN my_field TEXT;
```

---

## Modifying the Bootstrap

The bootstrap system is in `core/bootstrap/`. To customize:
1. Copy what you need
2. Add to `~/.agency/` on init
3. Don't touch `core/bootstrap/` — changes persist across upgrades

---

## Upgrading

```bash
agency upgrade
```

Preserves: `projects/`, `sessions/`, `lessons/`, `decisions/`, `skills/`, `task-store.db`

Overwrites: `core/`, `cli/`, `docs/`

---

## Testing the CLI

```bash
cd ~/the-agency
node cli/bin/agency.js init     # should complete without error
node cli/bin/agency.js status   # should show current state
node cli/bin/agency.js skill list  # should list installed skills
```

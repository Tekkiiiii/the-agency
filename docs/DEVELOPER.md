# Developer Guide

## Project Structure

```
the-agency/
├── core/                # Core system files (don't modify for extensions)
│   ├── agents/         # Agent templates (extend, don't modify originals)
│   ├── memory/         # Memory system documentation
│   ├── tasks/          # Task store schema and patterns
│   ├── nexus/          # Coordination protocol
│   └── bootstrap/       # Bootstrap system
├── skills/             # Skills library
├── docs/               # Documentation
└── cli/                # CLI tool
```

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

## Adding an Agent

Agents are defined in `agents/{name}.md`.

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

## Creating a Project Template

Copy `core/projects/template/` to `projects/{name}/` and customize.

## Extending the Task Schema

The task store is SQLite. To add columns:

```sql
ALTER TABLE tasks ADD COLUMN my_field TEXT;
```

## Modifying the Bootstrap

The bootstrap system is in `core/bootstrap/`. To customize:
1. Copy what you need
2. Add to `~/.agency/` on init
3. Don't touch `core/bootstrap/` — changes persist across upgrades

## Upgrading

```bash
agency upgrade
```

Preserves: `projects/`, `sessions/`, `lessons/`, `decisions/`, `skills/`, `task-store.db`

Overwrites: `core/`, `cli/`, `docs/`

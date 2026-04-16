# Bootstrap System

The Agency self-bootstraps on first run. No manual setup required.

## What Bootstrap Creates

```
~/.agency/                    # Root agency directory
├── task-store.db             # SQLite task store
├── projects/                 # Project states
├── sessions/                # Session logs
├── lessons/                 # Lessons
├── decisions/               # Cross-project decisions
└── skills/                  # Installed skills
```

## Bootstrap Files

These files are created by the `agency init` command:

1. `~/.agency/task-store.db` — initialized with schema
2. `~/.agency/projects/` — directory created
3. `~/.agency/sessions/` — directory created
4. `~/.agency/lessons/` — directory created
5. `~/.agency/decisions/` — directory created

## Bootstrapping a New Project

```bash
agency init --project my-project
```

This creates:
```
~/.agency/projects/my-project/
├── STATE.md
├── ROADMAP.md
└── decisions/
```

And initializes the task store.

## Bootstrapping Skills

Skills are installed by copying from `the-agency/skills/` or installing from the catalog:

```bash
agency skill install save-state
agency skill install recall
agency skill install swarm
```

## Upgrading

```bash
agency upgrade
```

Fetches latest from GitHub, preserves all local data (projects/, sessions/, lessons/).

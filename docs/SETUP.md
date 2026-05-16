# Quick Setup

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Node.js 18+ (for agency CLI)
- Git

## 1. Clone the repo

```bash
git clone https://github.com/the-agency/the-agency.git
cd the-agency
```

## 2. Install

```bash
agency init
```

Creates directories, installs all skills + agent templates, sets up the task store,
and links the `agency` CLI to your PATH.

## 3. Get oriented (optional)

```bash
agency onboard
```

Guided introduction — walks you through creating your first project and agent.
Requires `agency init` to have been run first.

## 4. Start a project

```bash
agency new my-project "Build a task manager app"
```

This creates the project structure and registers it with the agency. Skip this step
if you used `agency onboard` — it already created a project for you.

## 5. Spawn your first agent

In Claude Code:

```
/recall my-project
```

Or start fresh:

```
I'm starting a new project. Use the agency system.
Project: my-project
Goal: Build a task manager app with React and Supabase.
```

## 6. Install individual skills (optional)

`agency init` installs all bundled skills automatically. Use `agency skill install`
only if you want to install a skill that was added after your initial setup:

```bash
agency skill install save-state   # install a specific skill by name
agency skill list                 # see what is installed
```

Running `agency init` again re-syncs all skills without losing existing ones.

## 7. Create PD-BRIEFING.md for each project

For each project, create a per-project routing doc using the template in
`core/runbooks/pd-boot-sequence.md`. Place it at:

```
{project-root}/.claude/PD-BRIEFING.md
```

This file is the first thing a PD reads on spawn (~500 tokens) and contains
pre-written routing entries so the PD can delegate without loading the full agent catalog.

## 8. Initialize agency-rooms

```bash
mkdir -p ~/.claude/agency-rooms/project-oversight/handoffs
mkdir -p ~/.claude/agency-rooms/project-oversight/context
touch ~/.claude/agency-rooms/project-oversight/messages.mdl
touch ~/.claude/agency-rooms/project-oversight/context/shared.md
touch ~/.claude/agency-rooms/project-oversight/context/rolling.md
```

Create a room for each active project and department as needed. See `docs/ROOMS.md`
for the full directory structure and setup instructions.

## What you get

```
~/.claude/
├── task-store.db        # Your task pipeline
├── projects/           # Project states
├── sessions/           # Session logs
├── lessons/           # Lessons learned
└── skills/             # Your skills
```

## First project in 5 minutes

1. `agency new my-project "My first project"`
2. In Claude Code: `/recall my-project`
3. Tell the PD what to build
4. PD creates tasks, spawns specialists
5. Specialists report back, PD gates completed work
6. `/save-state` at end of session

## Troubleshooting

**agency: command not found**
```bash
npm install -g @the-agency/cli
```

**Task store locked**
```bash
sqlite3 ~/.claude/task-store.db "PRAGMA busy_timeout=5000;"
```

**Skills not loading**
Check `~/.claude/skills/INDEX.md` exists. If not, run `agency init` again.

## Next Steps

- [Architecture](ARCHITECTURE.md) — understand how it all fits together
- [Skills Guide](SKILLS.md) — how to install and use skills
- [Developer Guide](DEVELOPER.md) — extending the system

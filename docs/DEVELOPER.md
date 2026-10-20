# Developer Guide

## Project Structure

```
the-agency/
├── core/                # core system files
│   ├── agents/          # PD/Coord/Mini-Coord/Delegator templates (Execs are general-purpose + Skills)
│   ├── runbooks/        # boot, escalation, kickoff, quality loop, content pipeline
│   ├── memory/          # memory system specification
│   ├── nexus/           # NEXUS coordination protocol
│   ├── tasks/           # task store pattern
│   ├── bootstrap/       # bootstrap system
│   ├── ORG.md           # org chart, authority model
│   └── PD_PROTOCOL.md   # PD quick reference
├── agents/              # structural agents: PDs, Coords, critics, council seats, service agents
├── skills/              # reusable workflow skills; catalog in skills/INDEX.md
├── hooks/               # lifecycle hook scripts and hooks.json (see docs/HOOKS.md)
├── mods/                # optional Claude Code mods (see docs/MODS.md)
├── runbooks/            # protocols the agents follow
├── scripts/             # helper scripts called by hooks and skills
├── design-system/       # brand tokens the design skills read
├── cli/                 # Node.js CLI (agency init/new/tasks/skill/status/mods/hooks/prune)
└── docs/                # documentation
```

## Quick Start

### Clone and Install

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency
npm install   # optional — CLI is plain Node.js
```

### Initialize the Agency Runtime

```bash
node cli/bin/agency.js init
```

This creates `~/.claude/` on your machine with:
- `skills/` — skills library (235+ skills)
- `task-store.db` — SQLite task pipeline
- `sessions/` — session logs
- `lessons/` — lessons learned
- `decisions/` — architectural decisions

### Create a New Project

```bash
agency new taskboard "Task manager with auth and billing"
```

This scaffolds `~/.claude/projects/taskboard/` with:
- `STATE.md` — phase, status and next steps
- an empty `memory/` directory, which `/save-state` fills with next-session, heartbeat, decisions and session logs

It also registers the project in `{root}/memory/medium-term.md`, the table `/recall` and `/pd-resume` read.

### Resume with /pd-resume

Start the project's PD from its saved state:

```
/pd-resume taskboard
```

The PD reads `memory/next-session.md` (and, on a project that was never saved, starts from the
goal in `memory/tasks/ongoing/`) and begins on the Next line. A project with no `taskboard-pd`
agent definition falls back to the generic `pd-coordinator`.

---

## Adding a Skill

A skill is a directory with a `SKILL.md` entry point that defines a workflow.
Directory layout is canonical in the repo itself — `skills/<name>/SKILL.md` —
not just at install time; a flat `skills/<name>.md` file is invisible to
`syncSkills()` and never reaches installs (`scripts/check-flat-skills.js`
fails the build if one appears).

### 1. Create the skill directory

```
skills/my-skill/SKILL.md
```

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

Add any supporting files the skill needs (e.g. a `full-scan.md` referenced
from the main file) into the same directory — `syncSkills()` copies the whole
directory recursively.

### 2. Register it

Add to `skills/INDEX.md`:
```markdown
| my-skill | Does X for any project | Skills |
```

### 3. Add the skill-router overlay entry

The repo ships an optional skill router (off by default). Its menu builder needs an entry for every skill directory in `scripts/skill-route/overlay.json`; CI's `check-skill-route-menu.py` fails when `skills/` and the overlay differ.

```bash
python3 scripts/skill-route-overlay-add.py my-skill                                   # not routable ("internal")
python3 scripts/skill-route-overlay-add.py my-skill --domain frontend-ui --hint "Use to build X; not for Y"
```

Run it in the same commit as the new skill. Pick `--domain` from the keys of `overlay["domains"]` (an unknown name exits 2 and lists the valid ones). Details: `scripts/skill-route/README.md`.

### 4. Use it

In Claude Code:
```
/my-skill
```

---

## Adding an Agent

Agents are defined in `core/agents/{name}.md` or `agents/{folder}/{name}.md` and deployed to
`~/.claude/agents/{folder}/` so Claude Code can discover them. A folder is just a home for related agent definitions; it has no lead or coordinator.

### Agent frontmatter

```yaml
---
name: my-agent
description: What it does
department: engineering   # the agent folder name
role: specialist
reports_to: project-director
modelTier: sonnet
color: "#8B5CF6"
skills:
  - save-state
  - recall
---
```

> **Member roles.** Member-level roles are not registered as agent types: callers spawn `general-purpose` + 1-3 skills from `skills/INDEX.md`. Register an agent under `agents/` only for a PD, coord, critic, council seat, or service agent.

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
           └── Exec  (general-purpose + Skills; executes one atomic unit)
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
2. Add to `~/.claude/` on init
3. Don't touch `core/bootstrap/` — changes persist across upgrades

---


## Removing a Shipped File

Installs only add and update files, so a skill, agent, runbook or core doc deleted from the repo would stay on every user's disk. To make a removal reach installed roots:

1. Delete the file from `skills/`, `agents/`, `runbooks/` or `core/` in the normal way.
2. Run `python3 scripts/gen-retired-manifest.py` to regenerate `retired-manifest.json`. It lists each path the repo no longer ships, with the checksum of every version that was ever shipped there. It needs the full git history; CI checks it with `--check`.
3. For a hook, move its entry in `hooks/hooks.json` to `retired` instead (see [HOOKS.md](HOOKS.md#extending-the-hook-system)).

On `install`, `agency upgrade` and `agency prune`, an installed file that matches a shipped version byte for byte is deleted. One the user edited is archived to `{root}/archive/agency-retired-<date>/` or deleted, per `--retired=archive|delete|ask` (`install.ps1`: `-Retired`; env `AGENCY_RETIRED`). The default is `ask` on a terminal and `archive` otherwise, so an edit is never silently lost. A path the manifest does not list, such as a user's own skill, is never touched. The user-facing description is in [SETUP.md](SETUP.md#retired-files).

## Upgrading

```bash
agency upgrade
```

Preserves: `projects/`, `sessions/`, `lessons/`, `decisions/`, `skills/`, `task-store.db`

Overwrites: `core/`, `cli/`, `docs/`

---

## Skill Directory Format

The directory format is canonical everywhere — repo and install alike. Each
skill lives in its own folder with a `SKILL.md` entry point, both in the repo
and once installed:

```
the-agency/skills/{name}/SKILL.md        # repo (source of truth)
~/.claude/skills/{name}/SKILL.md         # installed (synced from repo)
```

`agency init` / `agency upgrade` sync every file in each `skills/<name>/`
directory via content-hash comparison (`cli/commands/sync-assets.js`) — repo
edits always win over local installed edits. A flat `skills/<name>.md` file at
the repo root is not valid and will fail `node scripts/check-flat-skills.js`
(wired into `npm test` in `cli/`).

Third-party Vietnamese marketing skills are never distributed: never copy them into `skills/` or import them from a maintainer's live skills dir. The blocklist is `.github/scripts/never-distribute.txt`, enforced by `node .github/scripts/check-never-distribute.js` in CI.

```bash
agency skill install my-skill   # installs to ~/.claude/skills/my-skill/SKILL.md
```

After creating a new skill, register it in `skills/INDEX.md` immediately — the
system will not discover unregistered skills.
Also add its router overlay entry (`python3 scripts/skill-route-overlay-add.py
<name> [--domain D --hint H]`); without it CI's skill-router menu gate fails.

---

## Testing the CLI

```bash
cd ~/the-agency
node cli/bin/agency.js init     # should complete without error
node cli/bin/agency.js status   # should show current state
node cli/bin/agency.js skill list  # should list installed skills
```

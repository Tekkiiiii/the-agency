# Developer Guide

## Project Structure

```
the-agency/
├── core/                # Core system files
│   ├── agents/         # Agent templates (PD, Coord, Mini-Coord; Execs are general-purpose + Skills)
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

This creates `~/.claude/` on your machine with:
- `skills/` — skills library (235+ skills)
- `task-store.db` — SQLite task pipeline
- `sessions/` — session logs
- `lessons/` — lessons learned
- `decisions/` — architectural decisions

### Create a New Project

```bash
agency new my-project
```

This scaffolds `~/.claude/projects/my-project/` with:
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

> **Generalist switch (2026-10-06).** Member-level roles are no longer registered as agent types. A new member role goes into `agents-archive/` as a role file with a row in `agents-archive/ROLE-MAP.md` (role to 1-3 skills), and callers spawn it as `general-purpose` + those skills. Register an agent under `agents/` only for a PD, coord, critic, council seat, or service agent. `agents-archive/` is deployed beside `agents/`, never under it (see `docs/INSTALL-LAYOUT.md`).

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

## Release Notes

Users install The Agency via `git clone` + `agency upgrade` — there's no package
registry and no version prompts. That means a change is invisible to users unless
it shows up in `CHANGELOG.md`. Follow this rule:

> Every commit pushed to `main` that changes user-facing behavior — a new CLI
> command or flag, a change to what `agency init`/`agency upgrade` installs or
> does, a bug fix a user would have hit, a new or removed skill/agent a user
> would notice, or a security/privacy fix — MUST add a `CHANGELOG.md` entry in
> the **same commit**.

Add the entry under a `## [Unreleased]` section at the top of `CHANGELOG.md`
(create one if it isn't there yet). It gets a dated header the next time someone
does a release-note pass — don't date it yourself.

Skip the entry for purely internal changes: refactors with no behavior change,
comment typo fixes, CI-only tweaks.

Date headers are `YYYY-MM-DD`. This repo has no semver and no version file —
never introduce one. Git history plus dated changelog headers are the only
source of truth this project needs.

### CHANGELOG.md is dual-language: Vietnamese first, then English

`CHANGELOG.md` documents every release wave in both languages, Vietnamese
before English. Every `## [date]` block (including `## [Unreleased]`) nests
two sub-sections in this order:

```markdown
## [Unreleased]

### Tiếng Việt

#### Added
- ...

#### Fixed
- ...

### English

#### Added
- ...

#### Fixed
- ...
```

Each language sub-section repeats the full Keep-a-Changelog category set
(`#### Added`, `#### Fixed`, `#### Changed`, `#### Deprecated`, `#### Removed`,
`#### Security`) one level deeper than before, since it now nests under the
language heading — `##` → `###` → `####`, never skipped or inverted. This
keeps both languages grep-able (`grep "### Tiếng Việt"` / `grep "### English"`
finds every block of that language) and requires zero changes to
`cli/commands/upgrade.js`'s `printChangelogSince()` — that function only
splits on `^## \[.+\]` and prints the body between headers verbatim, so the
nested VN/EN sub-structure flows through untouched. The upgrade-time display
prints both languages exactly as written in the file; there is no
language-filtering logic anywhere in the CLI.

Commit hashes, file paths, and code identifiers inside a Vietnamese entry are
carried over unchanged from the English entry — never translated.

**Before the commit lands, the Vietnamese text must go through the
`content-polish` skill's Vietnamese pipeline**
(`~/.claude/skills/content-polish/SKILL.md`, Vietnamese branch): a
`translationese-cleaner-vi` pre-pass (mandatory here — the VN draft is
translated from an English source, exactly the scenario that pre-pass exists
for) → `humanizer-vi` → an anti-fragmentation check → `grammar-checker-vi`.
Apply this to the VN prose only, not to code/URLs/identifiers embedded in it
— those skills already know not to touch them. Fix anything flagged before
committing, same as the pass that first introduced this format did.

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

```bash
agency skill install my-skill   # installs to ~/.claude/skills/my-skill/SKILL.md
```

After creating a new skill, register it in `skills/INDEX.md` immediately — the
system will not discover unregistered skills.
Also add its router overlay entry (`python3 scripts/skill-route-overlay-add.py
<name> [--domain D --hint H]`); without it CI's skill-router menu gate fails.

---

## Agency Rooms

Agents coordinate via file-based rooms in `{agency-root}/agency-rooms/`. Each room
is a directory with an append-only message log, shared context extracts, and a
`handoffs/` directory for NEXUS handoff JSON files.

See `docs/ROOMS.md` for the full room structure, PD status protocol, agent request
protocol, and handoff format.

---

## Testing the CLI

```bash
cd ~/the-agency
node cli/bin/agency.js init     # should complete without error
node cli/bin/agency.js status   # should show current state
node cli/bin/agency.js skill list  # should list installed skills
```

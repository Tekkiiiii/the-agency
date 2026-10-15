# User Guide

A complete run from a fresh clone to a shipped feature, in about 15 minutes. It covers the install, your first project, a working session, saving state, and resuming the next day. For prerequisites, upgrades, troubleshooting and optional setup (graphify, context budgets), see [SETUP.md](SETUP.md).

## Installation

Clone the repo anywhere **except** your Claude Code configuration directory, then run the installer from the clone. The installer syncs skills, agents, hooks and core docs *into* the configuration directory (the "root"). Cloning straight into `~/.claude` fails for anyone who already uses Claude Code, because that folder already exists.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency
```

| Platform | Command | Requirements |
|----------|---------|-------------|
| macOS / Linux | `bash install.sh` | bash |
| Windows | `.\install.ps1` | PowerShell |
| Any (Node.js) | `node cli/bin/agency.js init` | Node.js 18+ |

**The root.** It is `$AGENCY_HOME` if set, else `$CLAUDE_CONFIG_DIR`, else `~/.claude` (on Windows, `%USERPROFILE%\.claude\`). The installer prints it as `Sync root: <path> (from <source>)` and warns when it fell back to the default and found no `settings.json` there, so you notice a configuration folder that lives elsewhere. The installers, the CLI and every shipped hook and script resolve the root in the same order, so a custom root (`AGENCY_HOME=/custom/path bash install.sh`) is installed to and read from consistently. See [INSTALL-LAYOUT.md](INSTALL-LAYOUT.md#where-the-root-comes-from).

**What is left alone.** Skills, agents and memory the Agency does not ship are never touched. The Agency hooks are merged into `settings.json` without disturbing hooks you already have, and a backup is written next to it.

**What gets installed:**

```
~/.claude/
├── skills/              # 235+ skills as {name}/SKILL.md directories
├── agents/              # structural agents: PDs, Coords, critics, council seats, service agents
├── hooks/               # lifecycle hook scripts (security, cost tracking, crash detection)
├── mods/                # Claude Code mods, wired into settings.json (Claude Code 2.1.287+)
├── runbooks/            # protocols the agents follow
├── scripts/             # helper scripts the hooks and skills call
├── design-system/       # brand tokens the design skills read
├── core/                # agent templates, memory spec, NEXUS protocol, task-store pattern
├── projects/            # per-project state (created by `agency new`)
├── sessions/            # session logs (created by `/save-state`)
├── memory/              # persistent memory layer and the project registry
├── archive/             # retired files you had edited, moved here by install/upgrade
└── task-store.db        # SQLite task pipeline (Node.js install only)
```

Two steps run as part of every install and `agency upgrade`; both have a full description in [SETUP.md](SETUP.md):

- **Mods.** The five Claude Code mods in `mods/` are copied to `{root}/mods/<name>/` and added to `env.CLAUDE_CODE_PLUGIN_DIRS`. Opt out with `AGENCY_NO_MODS=1`; undo with `agency mods remove`. See [MODS.md](MODS.md) and [SETUP.md](SETUP.md#mods).
- **Retired files.** Files the repo has stopped shipping are pruned from your root; one you edited is archived, never silently lost. Preview with `agency prune --dry-run`. See [SETUP.md](SETUP.md#retired-files).

## Quick Start

**Prerequisites:** Claude Code, Node.js 18+.

```bash
# 1. Create a project
node cli/bin/agency.js new my-app "Build a task manager"

# 2. Open Claude Code in your project directory, then type:
/recall my-app
```

The PD loads and asks what to build. Tell it. When you are done for the day:

```
/save-state
```

Next session:

```
/recall my-app
```

No servers. No API keys beyond Claude Code. Everything stays on your machine.

---

## End-to-End Demo Walkthrough

### Part 1: Install

```bash
# Clone next to your Claude Code config, not into it (~/.claude already exists)
git clone https://github.com/Tekkiiii/the-agency.git ~/the-agency
cd ~/the-agency

# Sync skills, agents and hooks into your Claude Code root and put `agency` on PATH
bash install.sh        # Windows: .\install.ps1

# Guided setup: checks prerequisites and walks you through your first project
agency onboard
```

`agency onboard` guides you through each step interactively. At the end you have:

- `agency` on your PATH
- skills, agents and hooks synced into your root
- a first project registered for `/recall` and `/pd-resume`

If you already have Claude Code set up and want just the skills and agents:

```bash
agency init   # non-interactive: directories + skills + agents + task store
```

### Part 2: Create Your First Project

```bash
agency new saas-app "Build a task manager with auth and billing"
```

This creates:

```
~/.claude/projects/saas-app/
├── STATE.md          # current phase, blockers, next steps
└── memory/           # next-session brief, session logs, decisions
```

and registers the project in `~/.claude/memory/medium-term.md`, the registry `/recall` and `/pd-resume` read.

### Part 3: Start Working

Open Claude Code in your project directory:

```bash
cd ~/.claude/projects/saas-app
claude
```

Start the PD:

```
/recall saas-app
```

**First session:** the PD reads the project state and asks what you want to build.

```
PD-saas-app: No prior session found. What's the goal?

You: Build user authentication — email/password signup, login, logout,
     JWT sessions, password reset via email. Supabase backend.

PD-saas-app: Understood. Decomposing into 3 workstreams:
  - Auth Coord: JWT + session management
  - DB Coord: Supabase schema + migrations
  - Email Coord: password reset email flow

Spawning now. I'll report back when all three complete.
```

The three Coords run in parallel. Each decomposes further and spawns Execs. You see output as each unit completes:

```
Auth Coord: JWT middleware complete. Health score 89. ACKed.
DB Coord: Schema migrated, seed data loaded. Health score 91. ACKed.
Email Coord: Password reset flow complete. Health score 84. ACKed.

PD-saas-app: QA gate running across all workstreams...
QA gate passed. Overall health: 88.
Auth: signup, login, logout, and JWT refresh all working.
DB: users and sessions tables with RLS policies.
Email: reset email fires within 2 seconds in staging.

Ready for your review. Awaiting ACK.

You: ACK — looks good.

PD-saas-app: All done. Next session: run /save-state first.
```

How the gates behind those scores work is in [ARCHITECTURE.md](ARCHITECTURE.md#quality-gates-acknack-protocol).

### Part 4: End the Session

Before closing Claude Code:

```
/save-state saas-app
```

What this writes:

```
~/.claude/projects/saas-app/memory/
├── next-session.md    # what the PD reads at startup next time
├── heartbeat.md       # current phase and top priorities
├── decisions.md       # locked decisions that affect future work
└── sessions/
    └── 2026-05-17.md  # full session log
```

`next-session.md` is one file, under 15 lines:

```
# saas-app
Phase: Auth complete — billing next
Next: Implement Stripe checkout — monthly/annual plans, webhook handling
Blockers: none
Decisions: D1 — Supabase for DB; D2 — JWT in HTTP-only cookies (not localStorage)
Mid-flight: none
Last saved: 2026-05-17
```

### Part 5: Resume the Next Day

```bash
cd ~/.claude/projects/saas-app
claude
```

```
/recall saas-app
```

```
PD-saas-app: Auth complete. Next: Stripe billing.
  Decisions locked: Supabase, JWT in HTTP-only cookies.
  Starting billing workstream now.

Spawning Billing Coord...
```

No re-explaining. The PD picks up the exact next action.

### Part 6: Install an Individual Skill

All bundled skills are installed with the Agency. To add a skill that shipped after your install:

```bash
agency skill install ship     # automated PR creation + test run
agency skill install cso      # security audit (OWASP Top 10)
agency skill list             # see everything installed
```

Use it in Claude Code:

```
/ship
```

`/ship` reads the diff, runs tests, creates the PR, and writes a review report. The full catalog is in [SKILLS.md](SKILLS.md) and `skills/INDEX.md`.

### Part 7: Add a Parallel Project

You can run several projects at once. Each has its own PD:

```bash
agency new marketing-site "Redesign the marketing site"
agency new data-pipeline "Build ETL pipeline for user analytics"
```

Check all projects at once:

```bash
agency status
```

Resume all active PDs in one shot, from Claude Code:

```
/pd-resume all
```

Each PD spawns independently, runs its workstream, and reports back. PDs hand work to each other through the filesystem; see [Inter-PD Filesystem Protocol](ARCHITECTURE.md#inter-pd-filesystem-protocol).

### What You Now Have

- **`~/.claude/projects/`** — project state that persists across sessions
- **`~/.claude/skills/`** — 235+ skills ready to invoke
- **`~/.claude/agents/`** — the structural agents (PDs, Coords, critics, council seats, service agents)
- **`~/.claude/task-store.db`** — SQLite task pipeline with gate tracking

The PD handles decomposition, delegation, QA gating and state persistence. You give direction and review results.

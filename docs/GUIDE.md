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
node cli/bin/agency.js new taskboard "Task manager with auth and billing"

# 2. Open Claude Code and type:
/recall taskboard
```

A new project has no saved state, so `/recall` answers "no prior session found". Tell Claude what to build, then start the project lead with `/pd-resume taskboard`. When you are done for the day:

```
/save-state taskboard
```

Next session:

```
/recall taskboard
```

No servers. No API keys beyond Claude Code. Everything stays on your machine.

---

## End-to-End Demo Walkthrough

### Part 1: Install

```bash
# Clone next to your Claude Code config, not into it (~/.claude already exists)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
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

The running example is `taskboard`, a task-manager app with sign-up, login and subscription billing.

```bash
agency new taskboard "Task manager with auth and billing"
```

This creates:

```
~/.claude/projects/taskboard/
├── STATE.md          # phase, status, next steps
└── memory/           # next-session brief, session logs, decisions (filled by /save-state)
```

and registers the project in `~/.claude/memory/medium-term.md`, the registry `/recall` and `/pd-resume` read.

### Part 3: Start Working

Open Claude Code in your project directory:

```bash
cd ~/.claude/projects/taskboard
claude
```

Check what the project knows:

```
/recall taskboard
```

`/recall` reads `memory/next-session.md` and prints a six-field briefing. A project that has never been saved has no such file, so the briefing is the empty one:

```
RECALL — taskboard

Phase: unknown
Next: read project memory and assess current state
Blockers: none
Decisions: none
Mid-flight: none
Context: no prior session found
```

**First session.** Tell Claude the goal in plain words. For `taskboard` it is the first of two features: "Add email and password sign-up, login, logout and password reset to the task manager." Put it where the project lead (the PD) reads it on startup, a short task file in `memory/tasks/ongoing/` (ask Claude to write it), then start the PD:

```
/pd-resume taskboard
```

```
PD RESUME — 1 projects (1 spawned, 0 blocked)

taskboard — unknown — spawned
  next: read project memory and assess current state
  blockers: none

Spawned PDs running in background. Progress arrives via SendMessage.
```

The PD runs in the background. It writes `memory/dev-plan.md`, splits the goal into chunks (here: the users table first, then session handling and the reset-email flow side by side), and hands each chunk to a Coord, which spawns Execs for the actual edits. Every Exec result is checked before it is accepted: health 85 or higher, nothing CRITICAL or HIGH. [ARCHITECTURE.md](ARCHITECTURE.md#worked-example-adding-billing-to-a-task-manager) follows one such run step by step, including the QA gates and the Exec limit.

When all chunks pass QA and the integration test, the PD sends one final digest to your session and waits for your reply:

```
PD-taskboard: ALL L3s COMPLETE + QA GATE COMPLETE
Overall Health: 88
Per-L3 scores: {Coord-session-Gatekeeper: 89, Coord-users-Architect: 91, Coord-resetmail-Courier: 84}
Failure Classes: {Coord-session-Gatekeeper: none, Coord-users-Architect: none, Coord-resetmail-Courier: none}
Open CRITICAL/HIGH: none
Full QA Digest: ~/.claude/projects/taskboard/memory/qa/qa-report-final-<timestamp>.md
Deliverable Proof: <ls -la output for each claimed file>
Awaiting root ACK/NACK...
```

Reply "ACK" to accept, or "fix:" and a list to send it back for another round. The scores above are example values. How the gates behind them work is in [ARCHITECTURE.md](ARCHITECTURE.md#quality-gates-acknack-protocol).

### Part 4: End the Session

After your ACK the PD saves state itself. If you stop work yourself, run it before closing Claude Code:

```
/save-state taskboard
```

What this writes:

```
~/.claude/projects/taskboard/memory/
├── next-session.md    # what the PD reads at startup next time
├── heartbeat.md       # current phase and next action
├── decisions.md       # locked decisions that affect future work
└── sessions/
    └── 2026-05-17.md  # session log
```

`next-session.md` is one file of at most 15 lines:

```
# taskboard
Phase: Auth complete, billing next
Next: Add Stripe subscription billing: monthly and annual plans, a checkout page, a webhook that marks an account paid
Blockers: none
Decisions: Supabase for the database; session token in an HTTP-only cookie, not localStorage
Mid-flight: none
Delegated: none
Pending inbound: none
Last saved: 2026-05-17
```

### Part 5: Resume the Next Day

```bash
cd ~/.claude/projects/taskboard
claude
```

```
/recall taskboard
```

```
RECALL — taskboard

Phase: Auth complete, billing next
Next: Add Stripe subscription billing: monthly and annual plans, a checkout page, a webhook that marks an account paid
Blockers: none
Decisions: Supabase for the database; session token in an HTTP-only cookie, not localStorage
Mid-flight: none
Context: sign-up, login, logout and password reset shipped and accepted
```

Then `/pd-resume taskboard` starts a PD from that same file and the PD begins on the Next line. No re-explaining.

### Part 6: Install an Individual Skill

All bundled skills are installed with the Agency. To add a skill that shipped after your install:

```bash
agency skill install ship     # ship workflow: tests, diff review, commit, push, PR
agency skill install cso      # security audit: secrets, dependencies, CI/CD, OWASP Top 10
agency skill list             # see everything installed
```

Use it in Claude Code:

```
/ship
```

`/ship` merges the base branch, runs the tests, reviews the diff, bumps the version, updates the changelog, commits, pushes and opens the pull request. The full catalog is in [SKILLS.md](SKILLS.md) and `skills/INDEX.md`.

### Part 7: Add a Parallel Project

You can run several projects at once. Each has its own PD:

```bash
agency new pricing-page "Rebuild the pricing page with an annual-plan toggle"
agency new usage-report "Weekly usage report emailed to account owners"
```

Check all projects at once:

```bash
agency status
```

Resume all active PDs in one shot, from Claude Code:

```
/pd-resume all
```

Each PD runs in the background and reports to your session. A project whose only pending work is a decision of yours is not spawned: `/pd-resume` lists it as blocked and says what it is waiting for. PDs hand work to each other through the filesystem; see [Inter-PD Filesystem Protocol](ARCHITECTURE.md#inter-pd-filesystem-protocol).

### What You Now Have

- **`~/.claude/projects/`** — project state that persists across sessions
- **`~/.claude/skills/`** — 235+ skills ready to invoke
- **`~/.claude/agents/`** — the structural agents (PDs, Coords, critics, council seats, service agents)
- **`~/.claude/task-store.db`** — SQLite task pipeline with gate tracking

The PD handles decomposition, delegation, QA gating and state persistence. You give direction and review results.

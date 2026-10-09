# The Agency

**Claude Code, fixed for everyone.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)
![Cloud: Zero dependencies](https://img.shields.io/badge/Cloud-Zero%20Dependencies-green)
![QA: Gates on every handoff](https://img.shields.io/badge/QA-Gates%20%2B%20Health%20Scores-red)

Out of the box, Claude Code forgets everything when a session ends. Long tasks stall halfway, or come back marked "done" with nothing to prove it. And every new session burns tokens rebuilding context it already had. The Agency fixes those pains with plain files installed to `~/.claude/`:

- **Memory that survives sessions.** `/save-state` before you close, `/recall` when you come back. Open tasks, decisions, and blockers return with it.
- **Agents that finish what they start.** A Project Director breaks the work down, hands it to specialists, and owns it until it is delivered.
- **QA gates before "done".** No handoff is accepted without a health-score pass and evidence.
- **Token-lean routing.** Cheap lookups before expensive agent spawns, and the right model for each job: Opus plans, Sonnet executes, Haiku does bulk work.

Skills and agents as plain files. No cloud, no extra API keys.

```bash
agency init                   # full quality gates
```

---

## Install in 60 Seconds

```bash
# Clone anywhere except ~/.claude (that folder already exists if you use Claude Code)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency

# macOS / Linux
bash install.sh

# Windows (PowerShell)
.\install.ps1
```

That's it. The skills and agents are synced into your Claude Code config directory (`~/.claude/` by default), and the `agency` command is added to your PATH. Open Claude Code and they're ready. The installer prints a `Sync root:` line naming the directory it used. Keep the clone: `agency upgrade` pulls it and re-syncs.

```bash
agency onboard                        # Interactive setup wizard (start here)
agency new my-app "Build a task manager"
# In Claude Code: /recall my-app
```

**Already cloned but haven't set up?** Run this from inside the repo:

```bash
node cli/bin/agency.js init      # installs skills, agents, CLI link
agency onboard                   # guided tour + first project
```

The PD loads and asks what to build. You supervise; it executes.

**Stuck? `agency upgrade` failing? Don't have the repo?** Run this one-liner from anywhere:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

It finds your existing clone (checks your agency root, then `~/.claude/` and `~/the-agency/`), pulls the latest, and recovers from broken states. If you don't have the repo yet, it clones it to `~/the-agency/` (never into `~/.claude/`, which already exists if you use Claude Code) and tells you to run the installer. If `~/the-agency/` already holds something else, it leaves it alone and prints the `git clone` command for a different folder.

---

## What The Agency Does

Four things make it different from a conversation with an AI:

**1. Memory that persists.** You run `/save-state` before you close Claude Code. Tomorrow you run `/recall`. The agent picks up exactly where it left off — open tasks, decisions made, what was blocked, what shipped. No re-explaining. No context collapse.

**2. A real team structure.** Work routes PD → Coord → Exec. A Project Director owns the project, a Coord owns one gated task, and an Exec is a `general-purpose` agent with one to three named skills. Critics (`critique-*`) review the result. Agent folders (engineering, design, content-creation, testing, project-management, specialized, critiques, video-studio) group the agent definitions. The right route is picked for you.

**3. Autonomous coordination.** You give direction to a Project Director. The PD decomposes the work, assigns it to specialists, runs the tasks in parallel, checks the output at every handoff, and reports back. You don't coordinate. You supervise.

**4. Intelligent model routing.** Agents carry a model assignment. Planning and orchestration work goes to Opus. Execution work goes to Sonnet. High-volume research and scraping goes to Haiku. You get the right model for every task without thinking about it.

---

## See It In Action

### Scenario A: Work that survives the night

```
You:  /recall my-saas-app
PD:   Phase 2 in progress. Auth complete. Dashboard 60% done.
      2 blockers logged. Continuing now.

// 3 hours of work happens — you check in occasionally

You:  /save-state
PD:   State saved. Next session: finish dashboard, start billing.

// You close your laptop. Come back tomorrow.

You:  /recall my-saas-app
PD:   Dashboard complete. Billing ready to start. 
      Spawning payment specialist now.
```

You didn't explain anything the second day. The agent remembered.

- **4-tier autonomous chain**: PD → Coord → Mini-Coord → Exec (general-purpose + Skills) decomposes any project to atomic units. Mini-Coords keep drilling L6→L7→L8 without escalating to PD.
- **QA gates on every handoff**: No work gets ACK'd without a health-score pass. Gate: score ≥ 70 + zero CRITICALs. Example: 70 = tests pass but docs missing; 90+ = ship-ready.
- **Explicit ACK/NACK protocol**: An agent's report lands when it stops. If it is not re-spawned, that is the ACK. A NACK spawns a fresh continuation agent with the fix list, and the rework loops back through QA. Consent for a permission-gated action is a file the main session writes under `{project}/memory/tasks/revisions/acks/`, never chat prose.
- **Hook lifecycle system**: shell scripts across 5 lifecycle events (SessionStart, PreToolUse, PostToolUse, Stop, UserPromptSubmit) — security gating, secret scanning, config protection, crash detection, cost tracking, plus an opt-in Fable-on-Opus hook (ships unwired) that injects Fable-style reasoning discipline (`hooks/fable/`) whenever the active model is Opus-line. Profile-aware (`standard` / `strict` / `minimal`). See `docs/HOOKS.md`.
- **Production-ready skills**: Memory, execution, QA, engineering, deployment, design, content, video, and more — all invoked via `/skill-name`.
- **SQLite task store — nothing leaves your machine**: Task pipeline, gates, retries, blocking in `~/.claude/`. No servers. No API keys.
- **Session persistence**: `/save-state` and `/recall` make Claude Code fully resume-capable. Come back days later; the PD shows you exactly where it left off.
- **Agency Rooms** — file-based inter-agent chat with persistent rooms and NEXUS JSON handoffs, written through `room-utils.sh` and read on demand (no polling process).
- **Inter-PD Protocol** — PDs coordinate via filesystem, not messaging. Delegation through `inter-spawn-tasks/` directories with completion tracking.
- **Delegator Agent** — routing-as-a-service. When the right route is not obvious, an agent spawns the Delegator; it reads the agency catalog and returns the route. Worker roles run as `general-purpose` plus 1-3 skills (archived role files live in `agents-archive/`). No hardcoded selection hierarchies.
- **Curator Agent** — context retrieval on demand. PDs and Coords spawn curator to query per-project knowledge graphs, Pinecone, and NotebookLM. Never reads full memory files into context.
- **PD → Coord → Exec routing** — a Project Director decomposes, a Coord owns one task, an Exec (`general-purpose` plus 1-3 named skills) does the work, and critics review it. Quality gates sit on every handoff.
- **Agency Council** — one seat per Claude model tier plus an optional Codex seat, asked the same question in one wave. See [Agency Council and Governance](#agency-council-and-governance).
- **PD Boot Sequence** — lazy-loading spawn targeting <500 tokens. Per-project PD-BRIEFING.md for instant routing.
- **Status Loop Prohibition** — no automated ping loops. On-demand status via append-only `pd-status-live.md`.
- **Project Scope Management** — `scope.json` per project with 3-tier authority model (PD self-approve → parent AI → human).

## Architecture

```
You:  Build the REST API — auth, database, and all endpoints.

PD:   Decomposing. Spawning Auth Coord, DB Coord, API Coord in parallel.

// Three workstreams run simultaneously

Auth Coord:   JWT complete. Tests passing. Health score 94.
DB Coord:     Schema migrated. Seed data loaded. Health score 88.
API Coord:    Endpoints wired. Integration tests passing. Health score 91.

PD:   All three workstreams complete. QA gate passed. 
      Ready for your review.
```

## Installation

Clone the repo anywhere **except** your Claude Code configuration directory, then run the installer from the clone. The installer syncs skills, agents, hooks and core docs *into* the configuration directory (the "root"). On Windows the default root is `%USERPROFILE%\.claude\`. Cloning straight into `~/.claude` fails for anyone who already uses Claude Code, because that folder already exists.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency
```

| Platform | Command | Requirements |
|----------|---------|-------------|
| macOS / Linux | `bash install.sh` | bash |
| Windows | `.\install.ps1` | PowerShell |
| Any (Node.js) | `node cli/bin/agency.js init` | Node.js 18+ |

The root is `$AGENCY_HOME` if set, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`. The installer prints it as `Sync root: <path> (from <source>)` and warns when it fell back to the default and found no `settings.json` there, so you notice a config folder that lives elsewhere. Skills, agents and memory the agency does not ship are left alone, and the agency hooks are merged into `settings.json` without touching hooks you already have (a backup is written next to it).

**What gets installed:**

```
~/.claude/
├── skills/              ← 235+ skills as {name}/SKILL.md directories
│   ├── backend/SKILL.md
│   ├── frontend/SKILL.md
│   ├── ship/SKILL.md
│   └── ...
├── agents/              ← 35+ agents in agent folders
│   ├── engineering/
│   ├── design/
│   ├── content-creation/
│   └── ...
├── hooks/               ← lifecycle hook scripts (security, cost tracking, crash detection)
│   ├── gate-guard.sh
│   ├── secret-scanner.sh
│   ├── cost-tracker.sh
│   ├── fable-on-opus.sh # UserPromptSubmit: inject Fable reasoning discipline on Opus
│   ├── fable/           # Fable playbook modules read by fable-on-opus.sh
│   └── ...
├── projects/            ← per-project state (created by `agency new`)
├── sessions/            ← session logs (created by `/save-state`)
├── memory/              ← persistent memory layer
└── task-store.db        ← SQLite task pipeline (Node.js install only)
```

Override the install location with `AGENCY_HOME=/custom/path ./install.sh`. The
installers, the CLI, and every shipped hook and script resolve the same root in the
same order — `$AGENCY_HOME`, then `$CLAUDE_CONFIG_DIR`, then `~/.claude` — so a
custom root is installed to *and* read from consistently. CI verifies this on both
Linux and Windows on every push. See
[docs/INSTALL-LAYOUT.md](docs/INSTALL-LAYOUT.md#where-the-root-comes-from).

---

## Quick Start

**Prerequisites:** Claude Code, Node.js 18+

```bash
# 1. Create a project
node cli/bin/agency.js new my-app "Build a task manager"

# 2. Open Claude Code in your project directory, then type:
/recall my-app
```

The PD loads and asks what to build. Tell it.

When you're done for the day:
```bash
/save-state
```

Next session:
```bash
/recall my-app
```

No servers. No API keys beyond Claude Code. Everything on your machine.

For the full setup walkthrough, see `docs/SETUP.md`.

---

## End-to-End Demo Walkthrough

This is a complete run-through from clone to shipped feature, using a real project as the example. Takes about 15 minutes to follow along.

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

`agency onboard` guides you through each step interactively. At the end, you have:
- `~/.agency/` — your persistent workspace (projects, skills, sessions)
- `agency` on your PATH
- A first project and agent definition

If you already have Claude Code set up and want just the skills/agents:

```bash
agency init   # non-interactive: directories + skills + agents + task store
```

### Part 2: Create Your First Project

```bash
agency new saas-app "Build a task manager with auth and billing"
```

This creates:

```
~/.agency/projects/saas-app/
├── STATE.md          ← current phase, blockers, decisions
├── memory/           ← sessions, heartbeat, next-session brief
└── agents/           ← per-project agent definitions
```

### Part 3: Start Working

Open Claude Code in your project directory:

```bash
cd ~/.agency/projects/saas-app
claude
```

In Claude Code, start the PD:

```
/recall saas-app
```

**First session:** The PD reads the project state and asks what you want to build.

```
PD-saas-app: No prior session found. What's the goal?

You: Build user authentication — email/password signup, login, logout,
     JWT sessions, password reset via email. Supabase backend.

PD-saas-app: Understood. Decomposing into 3 workstreams:
  - Auth Coord-Gatekeeper: JWT + session management
  - DB Coord-TombRaider: Supabase schema + migrations
  - Email Coord-Postmaster: password reset email flow

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

### Part 4: End the Session

Before closing Claude Code:

```
/save-state saas-app
```

What this writes:

```
~/.agency/projects/saas-app/memory/
├── next-session.md    ← what the PD reads at startup next time
├── heartbeat.md       ← current phase and top priorities  
├── decisions.md       ← locked decisions that affect future work
└── sessions/
    └── 2026-05-17.md  ← full session log
```

The `next-session.md` is one file, under 15 lines:

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
cd ~/.agency/projects/saas-app
claude
```

```
/recall saas-app
```

```
PD-saas-app: Auth complete. Next: Stripe billing.
  Decisions locked: Supabase, JWT in HTTP-only cookies.
  Starting billing workstream now.

Spawning Billing Coord-CashRegister...
```

No re-explaining. No context collapse. The PD picks up the exact next action.

### Part 6: Install an Individual Skill

After initial setup, all bundled skills are already installed. To add a skill that shipped after your install:

```bash
agency skill install ship     # automated PR creation + test run
agency skill install cso      # security audit (OWASP Top 10)
agency skill list             # see everything installed
```

Use it in Claude Code:

```
/ship
```

`/ship` reads the diff, runs tests, creates the PR, and writes a review report.

### Part 7: Add a Parallel Project

You can run multiple projects simultaneously. Each has its own PD:

```bash
agency new marketing-site "Redesign the marketing site"
agency new data-pipeline "Build ETL pipeline for user analytics"
```

Check all projects at once:

```bash
agency status
```

```
Projects:
  saas-app          Phase: billing — in progress
  marketing-site    Phase: new — not started
  data-pipeline     Phase: new — not started
```

Resume all active PDs in one shot:

```
/pd-resume all
```

Each PD spawns independently, runs its workstream, and reports back.

### What You Now Have

After this walkthrough:

- **`~/.agency/projects/`** — project state that persists across sessions
- **`~/.agency/skills/`** — 235+ skills ready to invoke
- **`~/.agency/agents/`** — 35+ agents in agent folders
- **`~/.agency/task-store.db`** — SQLite task pipeline with gate tracking

The PD handles decomposition, delegation, QA gating, and state persistence. You give direction and review results.

---

## Works With 9 Tools

The Agency runs natively in Claude Code. It also works as an agent layer inside other tools:

| Tool | How it works |
|------|-------------|
| **Claude Code** | Native — agents load directly from `~/.claude/agents/` |
| **GitHub Copilot** | Native `.md` agents in `~/.github/agents/` |
| **Cursor** | Auto-converted `.mdc` rule files in `.cursor/rules/` |
| **Windsurf** | Compiled into `.windsurfrules` in your project root |
| **Aider** | Compiled into a single `CONVENTIONS.md` |
| **Antigravity (Gemini)** | `SKILL.md` per agent in `~/.gemini/antigravity/skills/` |
| **Gemini CLI** | Extension format with manifest |
| **OpenCode** | `.md` agents in `.opencode/agents/` |
| **OpenClaw** | `SOUL.md` + `AGENTS.md` + `IDENTITY.md` per agent |

```bash
./scripts/convert.sh   # generate all integration formats
./scripts/install.sh   # interactive installer — auto-detects your tools
```

Full integration details and per-tool setup: `agents/README.md`

---

## Skills and Pipelines

Key skills in the library:

| Skill | What it does |
|-------|-------------|
| `/recall` | Load project briefing and resume the PD |
| `/save-state` | Freeze session to memory — logs, state, next-session brief |
| `/pd-resume` | Resume all active PDs at once (parallel) |
| `/swarm` | One-shot status check across all projects |
| `/autoplan` | Multi-reviewer planning pass: CEO, engineering, design |
| `/ship` | Automated: merge, test, review, PR |
| `/qa` | Iterative QA testing and bug fixing |
| `/cso` | Security audit against OWASP Top 10 |

Skills chain into pipelines. Example — full content workflow:

```
/pipeline-content "How AI agents handle memory"
→ research phase
→ draft phase
→ critique gate
→ humanize pass
→ knowledge capture
```

Full catalog: `skills/INDEX.md`

### Skill router (optional, off by default)

`scripts/skill-route.py` can pick 1-3 skills for a task text, plus a model tier and a tool profile, using Jev (TypeSafe SystemOne) with a Haiku and a local grep fallback. **It is off.** Nothing calls it, it makes no network request while off, and routing stays "pick 1-3 skills from `skills/INDEX.md`". The Agency ships no key.

To enable: get your own key from TypeSafe, put `TYPESAFE_API_KEY=...` in `~/.config/typesafe/.env`, set `AGENCY_SKILL_ROUTER=1` (the `env` block of `settings.json` works), rebuild the menu with `skill-route.py --rebuild-menu`. Exact steps for macOS, Linux and Windows, the output contract, fallback and cost logging: [`scripts/skill-route/README.md`](scripts/skill-route/README.md).

### Project Directors

Spawned via `/recall {project}`. Owns the project end-to-end:

1. Decompose work into tasks
2. Assign to specialists via Coord/Mini-Coord chain
3. Gate completed work against QA criteria
4. Escalate blockers
5. Persist state via `/save-state`

## Skills Library

**Memory & Session**: `save-state`, `recall`, `pd-resume`, `wrap`, `unwrap`, `project-status`, `context-save`, `context-restore`, `freeze`, `unfreeze`

**Coordination**: `swarm`, `delegate`, `pd-spawn`, `task-handoff`, `task-store`, `nexus-gatekeeper`, `sync-md-json`

**Planning**: `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `plan-devex-review`, `plan-tune`, `office-hours`, `retro`, `seed`, `project-expansion-scout`

**Pipelines** (multi-stage workflows): `pipeline-feature`, `pipeline-bugfix`, `pipeline-content`, `pipeline-audit`, `pipeline-deploy`, `pipeline-seo-geo-aeo`

**Execution**: `ship`, `land-and-deploy`, `setup-deploy`, `canary`, `qa`, `qa-only`, `run-acceptance-tests`

**Quality & Critique**: `design-review`, `review`, `codex`, `cso`, `document-release`, `backend-critique`, `design-critique`, `content-critique`, `marketing-critique`, `operations-critique`, `product-critique`, `security-critique`, `workflow-critique`, `devex-review`, `careful`

**Content & Writing**: `humanizer`, `proofreader`, `content-polish`, `content-creator`, `content-strategy`, `copywriting`, `stop-slop`, `tech-writer`, `marp`, `markitdown`, `make-pdf`, `promt-engineering`, `xlsx-toolkit`, `vietnamese-language`

**Engineering — Backend**: `backend`, `security`, `webhook-security`, `postgresql-schema`, `supabase-sql`, `multi-role-auth`, `laravel-builder`, `admin-shell-foundation`

**Engineering — Frontend**: `frontend`, `shadcn-ui`, `cult-ui`, `tailwind`, `next-best-practices`, `css-animations`, `image-to-code`, `svgl`, `extract-design`, `excalidraw-diagram`

**Design & UI/UX**: `ui-ux-pro-max`, `impeccable`, `design-html`, `high-end-visual-design`, `minimalist-ui`, `industrial-brutalist-ui`, `emil-design-eng`, `gpt-taste`, `brandkit`, `figma-ui-ux-consistency`

**Video & Media**: `ffmpeg`, `video-use`, `hyperframes`, `hyperframes-cli`, `hyperframes-media`, `remotion-best-practices`, `lottie`, `animejs`, `gsap`, `waapi`, `three`, `gpt-image-prompts`, `imagegen-frontend-web`, `imagegen-frontend-mobile`

**Deployment**: `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy`

**Cloud & Infrastructure**: `agents-sdk`, `refactor-module`, `finops`

**Ops & Debugging**: `self-healing`, `investigate`, `guard`, `health`, `web-perf`, `webapp-testing`

**Browser & Scraping**: `browse`, `agent-browser`, `lightpanda`, `scrape`, `firecrawl-agent`, `firecrawl-crawl`, `firecrawl-scrape`, `pair-agent`

**Superpowers** (14 gstack workflow skills): `superpowers-brainstorming`, `superpowers-systematic-debugging`, `superpowers-dispatching-parallel-agents`, `superpowers-executing-plans`, `superpowers-writing-plans`, `superpowers-test-driven-development`, and 8 more.

**Domain-Specific**: `better-auth-best-practices`, `legal-contract-review`, `n8n-automation`, `sanity-best-practices`, `tech-stack`

Full categorized registry: [`skills/INDEX.md`](skills/INDEX.md)

## File Structure

```
the-agency/
├── core/
│   ├── agents/          # PD/Coord/Mini-Coord/Exec/Delegator/Curator templates
│   ├── runbooks/        # Boot, escalation, kickoff, quality loop, content pipeline
│   ├── ORG.md           # Org chart, authority model
│   ├── PD_PROTOCOL.md   # PD quick reference
│   ├── memory/          # Memory system specification
│   ├── nexus/           # NEXUS coordination protocol
│   └── tasks/           # Task store pattern
├── cli/                 # Node.js CLI (agency init/new/tasks/skill/status)
├── docs/                # User-facing documentation
│   ├── HOOKS.md         # Hook system reference
│   └── ecc-patterns.md  # ECC pattern library (adopted design patterns)
├── hooks/               # lifecycle hook scripts
│   ├── gate-guard.sh    # PreToolUse: gate writes to sensitive files
│   ├── secret-scanner.sh# PreToolUse: scan bash commands for credentials
│   ├── config-protection.sh # PreToolUse: block linter config modification
│   ├── track-edits.sh   # PostToolUse: buffer edited file paths
│   ├── startup-sync.sh  # SessionStart: auto-pull config from remote
│   ├── check-settings-secrets.sh # SessionStart: warn on plaintext tokens
│   ├── check-session-state.sh    # SessionStart: detect unclean exit
│   ├── session-end.sh   # Stop: mark session clean
│   ├── batch-check.sh   # Stop: typecheck + shellcheck edited files
│   ├── cost-tracker.sh  # Stop: compute session token cost
│   ├── fable-on-opus.sh # UserPromptSubmit: inject Fable reasoning discipline on Opus
│   └── fable/           # Fable playbook modules read by fable-on-opus.sh
├── agents/              # 35+ agent definitions (PD/Coord/critic/council + project PDs)
├── skills/              # 235+ reusable workflow skills
└── plans/               # Architecture decision records
```

## Contributing

Two ways to extend the system:

**New agents** — add an agent to an existing agent folder or propose a new folder. See `agents/CONTRIBUTING.md` for the agent spec format and review process.

**New skills** — create a markdown file in `skills/`, register it in `skills/INDEX.md`, and invoke it with `/skill-name`. Skills are reusable workflows: a skill can call other skills, spawn agents, or chain multi-stage pipelines. Contributors also add an overlay entry for the new skill (`python3 scripts/skill-route-overlay-add.py <name> [--domain D --hint H]`); CI's skill-router menu gate fails without it. Users who enable the optional skill router need an entry for their own skills too, to make them routable. See `docs/DEVELOPER.md` for the full guide.

---

## For Technical Builders

Everything above describes what the system does. This section describes how it works. It assumes familiarity with Claude Code's agent and task primitives.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User (you)                             │
│                  Claude Code + agency CLI                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌─────────────────┼─────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼────┐     ┌─────▼─────┐
   │  Task   │      │ Memory   │     │   NEXUS   │
   │ Store   │      │ System   │     │ Handoffs  │
   │ SQLite  │      │ Sessions │     │           │
   └─────────┘      └──────────┘     └───────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
        ┌─────▼────┐  ┌───▼───┐    ┌────▼────────┐
        │  PD per  │  │Skills │    │ Inter-Agent │
        │ Project  │  │Library│    │ Coordination│
        └──────────┘  └───────┘    └─────────────┘
```

**Task Store** (`~/.claude/task-store.db`) — SQLite pipeline state. Schema: tasks with `status`, `blocked_by`, `gate_status`, `retry_count`.

**Memory System** — four filesystem layers (see Memory System below).

**NEXUS Protocol** — file-based 6-phase handoff doctrine for inter-agent coordination. Handoff artifacts are JSON files, read on demand with `room-utils.sh`.

**Hook System** — shell scripts wired into Claude Code's 5 lifecycle events. Live at `{root}/hooks` (root = `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`); install and `agency upgrade` copy them and wire them into `settings.json` from `hooks/hooks.json` (`agency hooks sync|remove` does the wiring on demand). Profile-aware (`standard` / `strict` / `minimal`).

**Skills** — markdown-based reusable workflows loaded from `~/.claude/skills/`, registered in `INDEX.md`.

**Project Directors** — one per project, own delivery end-to-end.

### 4-Tier Agent Chain

```
PD  (L1→L3 decomposition, spawns Coords)
 └── Coord × N  (L3→L4→L5→L6, spawns Exec or Mini-Coord, autonomous)
      └── Mini-Coord × M  (L6→L7→L8→L9, spawned for complex L6 tasks)
           └── Exec × K  (general-purpose + Skills; executes exactly one atomic unit)
```

| Layer | Agent | Decomposes | Spawns | Model |
|-------|-------|-----------|--------|-------|
| L1–L3 | PD | L1 → L2 → L3 | Coord | Opus |
| L3–L6 | Coord | L3 → L4 → L5 → L6 | Exec or Mini-Coord | Sonnet |
| L6+ | Mini-Coord | L6 → L7 → L8 → L9 | Exec | Opus |
| Atomic | Exec (general-purpose + Skills) | — | — | Sonnet |

**Naming convention:**
- PD: `PD-{slug}` (e.g., `PD-my-saas-app`)
- Coord: `Coord-{l3-name}-{pun}` (e.g., `Coord-auth-Gatekeeper`)
- Mini-Coord: `Mini-{l3-name}-{pun}-{branch}` (e.g., `Mini-auth-Gatekeeper-loginFlow`)
- Exec: `Exec-{task}-{pun}` (e.g., `Exec-login-Keymaster`)

### PD Standard Protocol

Every Project Director follows 3 mandatory rules on every spawn, without exception:

1. **Decompose** — break every task into the smallest independent sub-tasks before acting
2. **Agent Selection via Delegator** — when spawning a subagent, spawn the Delegator first. It reads the full agency catalog and returns the right agent, skill, or protocol. Never default to general-purpose — always route through Delegator.
3. **Parallelize** — spawn one subagent per sub-task simultaneously
4. **Report** — send each completion immediately, not at the end

### ACK/NACK Quality Gates

Every agent-to-agent handoff passes through a mandatory QA gate:

| Handoff | Reporter | Reviewer | ACK condition | NACK condition |
|---------|----------|----------|---------------|----------------|
| Exec → Coord | Exec: DONE + QA report | Coord reviews | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| Coord → PD | Coord: L3 complete + QA | PD reviews | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| PD → root | PD: final digest + QA | Root (operator) | Explicit ACK | Explicit NACK with fix list |

**ACK** — approved; reporting agent deletes scratch and stops.

**NACK** — returns a fix list; reporter fixes, re-runs QA gate, re-reports.

After all Coords report DONE, PD spawns `Coord-qa-Canary` (Sonnet, QA Coord) to QA the combined L3 output before reporting to root. Deliverables: health score (0–100), issues by severity (CRITICAL/HIGH/MEDIUM/LOW), screenshots at `{project}/memory/qa/screenshots/`, report at `{project}/memory/qa/qa-report-final-{timestamp}.md`.

### Memory System

The memory system uses `next-session.md` as the SSOT for PD startup. `/save-state` writes it; `/recall` reads it. This keeps the startup payload small (15 lines max) and avoids loading stale state.

| File | Location | Purpose |
|------|----------|---------|
| `next-session.md` | `{project}/memory/` | PD startup SSOT — phase, next action, blockers, decisions (max 15 lines) |
| `sessions/YYYY-MM-DD.md` | `{project}/memory/sessions/` | Full session logs — append-only |
| `decisions.md` | `{project}/memory/` | Architectural decisions — append-only |
| `heartbeat.md` | `{project}/memory/` | Live phase status — updated each session |
| `lessons/*.md` | `~/.claude/memory/lessons/` | Root-cause lessons by stack — append-only |

Each project carries its own memory structure:
```
{project}/memory/
├── next-session.md      # PD startup SSOT — read on every /recall
├── heartbeat.md         # Phase status — updated each session
├── decisions.md         # Architectural decisions (append-only)
├── sessions/            # Session logs by date
├── lessons/             # Per-stack lessons (synced from root)
├── tasks/
│   ├── ongoing/         # Active task files
│   └── completed/       # Completed task archive
├── agents/
│   ├── pd-scratch.md    # PD working scratch
│   ├── pd-status-live.md# Append-only status log (zero-cost on-demand reads)
│   └── coords/          # Coord scratch files
└── qa/
    ├── qa-report-final-{timestamp}.md
    └── screenshots/
```

### NEXUS Protocol (6 Phases)

NEXUS is the handoff doctrine. Core principle: every agent writes what it knows; the next agent reads what it needs.

| Phase | Name | What happens |
|-------|------|-------------|
| 0 | Register | Create project structure and task |
| 1 | Brief | Assign work with full context |
| 2 | Work | Execute, document incrementally |
| 3 | Handoff | Transfer with evidence and acceptance criteria |
| 4 | Review | Gate work against acceptance criteria |
| 5 | Archive | Close out, record lessons |

<details>
<summary>NEXUS key rules and escalation levels</summary>

**Key rules:**
1. Write before you stop — never end a session without saving state
2. Gate before handoff — don't pass work that doesn't meet criteria
3. Blockers surface fast — escalate within one session
4. Lessons from mistakes — append, never overwrite

**Escalation:**

| Level | Trigger | Action |
|-------|---------|--------|
| tier-1 | Minor blocker | Note in session log, continue |
| tier-2 | Major blocker | Escalate to team-lead, pause task |
| tier-3 | Crisis | Escalate to council, stop work |

Handoff artifacts are JSON files placed in `{room}/handoffs/`. the sender tells the receiving agent the handoff exists, and `room-utils.sh read-handoffs <room> pending` lists the open ones.

</details>

### Delegator — Routing Layer

The Delegator is a stateless service agent. Any agent (PD or Coord) spawns it when they need to pick the right agent, skill, or protocol for a task.

```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Delegator — route: {task-summary}",
  prompt: "Read ~/.claude/agents/specialized/delegator.md fully.\n\nRouting question: {task}\nCaller: {your name}"
})
```

The Delegator reads the agency catalog (`memory/agency-dispatch.md`), org chart, agent-folder INDEX files, and skill index. It returns a structured `DELEGATOR ROUTING` recommendation. It never executes work, never writes files, never holds state.

**Routing rules:** Skills before agents (cheaper), PDs for project deliverables, Coords for one gated task, an Exec (`general-purpose` plus 1-3 skills) for the work itself, inter-spawn for cross-authority tasks.

### Curator — Context Retrieval

The Curator is a read-only retrieval agent. PDs and Coords spawn it when they need project context not available in their briefing.

```
Agent({
  subagent_type: "curator",
  model: "sonnet",
  description: "Curator — {topic}",
  prompt: "Project: {slug}\nPath: {project_path}\nQuestion: {your question}"
})
```

Retrieval order: per-project graph → unified graph (MCP) → NotebookLM → Pinecone → raw file reads. Returns a `CURATOR ANSWER` block with source references and confidence level. Never fabricates. Never appears in Children tables — it's a service call.

### PD → Coord → Exec Routing

Project work runs as one chain. Departments with their own leads and coordinators were retired in the 2026-10-08 sunset (the archived files and restore steps are in `agents-archive/MANIFEST.md`).

```
PD (Opus)              — owns the project, decomposes L1 → L3, spawns Coords
  └── Coord (Sonnet)       — owns one gated task, hands it to one Exec or splits it
        └── Exec (Sonnet)      — `general-purpose` + 1-3 named skills, does the work
```

Critics (`critique-*`, `sag-critique`) are spawned directly by the PD or Coord and report to whoever spawned them. Content goes PD → Coord → writer → `/content-polish` → critics via `/cc-loop` (`runbooks/content-request-protocol.md`).

### Inter-PD Filesystem Protocol

Background agents cannot receive messages. PDs coordinate via the filesystem instead of SendMessage.

5-step protocol:

1. PD-A writes briefing to: `{target-project}/memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md`
2. PD-A creates tracker: `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`
3. PD-A spawns PD-B via Agent tool with `run_in_background: true`
4. PD-B completes work, appends completion to caller's `delegated-{task-id}.md`
5. On next `/pd-resume`, PD-A reads completion and marks task done

Use `/pd-spawn` for the full protocol.

### Hook System

Bash scripts across 5 lifecycle events, copied to `{root}/hooks` (root = `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`) by `install.sh`, `agency init` and `agency upgrade`, which also wire the hooks listed in `hooks/hooks.json` into `settings.json`; `agency hooks sync|remove` does the wiring on demand.

| Script | Event | What it does |
|--------|-------|-------------|
| `fable-on-opus.sh` | UserPromptSubmit | Inject Fable-style reasoning discipline (`hooks/fable/`) when the active model is Opus-line |
| `startup-sync.sh` | SessionStart | Auto-pull `~/.claude` from GitHub — every session starts fresh |
| `check-settings-secrets.sh` | SessionStart | Warn if `settings.json` has plaintext tokens in MCP env blocks |
| `check-session-state.sh` | SessionStart | Detect unclean prior exit (crash/Ctrl+C) |
| `gate-guard.sh` | PreToolUse (Edit/Write) | Warn on writes to settings, agents, hooks, and SKILL.md files (deny under `strict`) |
| `secret-scanner.sh` | PreToolUse (Bash) | Ask (deny under `strict`) on shell commands containing JWTs, API keys, GitHub tokens |
| `config-protection.sh` | PreToolUse (Edit/Write) | Block modification of existing linter/formatter configs |
| `track-edits.sh` | PostToolUse (Edit/Write) | Buffer edited file paths for session-end batch check |
| `session-end.sh` | Stop | Mark session cleanly ended; `check-session-state.sh` reads this |
| `batch-check.sh` | Stop | Typecheck TypeScript, shellcheck shell scripts edited this session |
| `cost-tracker.sh` | Stop | Compute session token usage and estimated USD cost |

**Profile system** — hooks read `~/.claude/.hook-profile` at runtime:
- `standard` — gate-guard warns only (`additionalContext`, the write goes ahead); secret-scanner asks (`hookSpecificOutput.permissionDecision: "ask"`)
- `strict` — block on any match (`hookSpecificOutput.permissionDecision: "deny"`)
- `minimal` — all safety hooks disabled (useful inside CI or trusted automation)

```bash
echo "strict" > ~/.claude/.hook-profile   # tighten up
echo "minimal" > ~/.claude/.hook-profile  # loosen for automation
```

Full reference: [`docs/HOOKS.md`](docs/HOOKS.md)

### Mods (optional, Claude Code 2.1.287+)

Five plugins in `mods/`, loaded by hand (the installer does not set them up yet):

- `context-band`: Claude Code shows no context, cache or usage-window figures above the prompt -> a band with context %, cost, cache countdown and 5h/7d reset timers.
- `agent-ctx`: an agent does not notice its context filling up -> it is told at 70% and 80%.
- `loop-guard`: an agent repeats the same tool call forever -> a stall warning after five identical calls.
- `spawn-ledger`: subagent spawns leave no record and nothing pins their model or caps parallel Execs -> a JSONL spawn ledger, model pin, Exec cap and artifact check.
- `voice-compact`: the CAVEMAN / PONYTAIL startup injections cost tokens every session -> compact ~150-token rules.

How to load them, what overlaps with the shell hooks, and what each one reads: [mods/README.md](mods/README.md).

### Model Routing Table

All agents carry a `modelTier` tag in their frontmatter. Routing is automatic.

| Model | Role | Used for |
|-------|------|---------|
| Opus | Leadership, planning | PDs, architecture and final review |
| Sonnet | Orchestration, execution | Coords, Mini-Coords, Execs, QA agents |
| Haiku | Menial, high-volume | Scraping, research, data extraction |

**1M context (`[1m]`) is selective, not fleet-wide.** Only orchestrator roles —
PD, Coord, Mini-Coord — carry the `[1m]` model suffix, because they are
the only agents whose context grows with the size of the work rather than the size of
their own brief. Everything below them stays plain. Full policy and rationale:
[`core/ORG.md` § Model tiering](core/ORG.md).

Note that `modelTier:` is a documentation tag only — `model:` is the key Claude Code
actually reads, and it is the one `[1m]` attaches to.

### Agency Rooms

File-based inter-agent communication. Agents coordinate through rooms, not direct messaging.

Two room types:
- **Project rooms** — one per active project, owned by the project's PD
- **Oversight room** — `project-oversight/`; all PDs post status; main session reads on demand

<details>
<summary>Room directory structure</summary>

```
{agency-root}/agency-rooms/{room}/
├── messages.mdl        # Append-only message log
├── room.json           # Room metadata and member list
├── members.json        # Active members
├── handoffs/           # Pending NEXUS handoffs (JSON)
└── context/
    ├── shared.md       # Extracted DECIDED/ACTION/QUESTION items
```

Message format:
```
[{ISO timestamp}] @{agent-name} [{phase}]: {content}
```

Rooms are plain files written by `agents/scripts/room-utils.sh` (and by the feedback-pipeline cron under `agency-rooms/feedback/`). There is no polling process: the `room-manager` skill was archived in the 2026-10-08 department sunset, so nothing auto-notifies members, auto-summarizes `context/shared.md` (keep it by hand), or routes `ESCALATE:` messages. Read a room on demand with `room-utils.sh read`. See `runbooks/agency-rooms-protocol.md`.

Anti-patterns:
- Do NOT send direct messages between agents — everything goes through rooms
- Do NOT implement recurring status loops — use on-demand reads via `/swarm`
- Do NOT skip the handoff JSON — without it, context is lost between sessions

</details>

### Agency Council and Governance

The Agency Council is an advisory board of five seats, one per Claude model tier plus an optional Codex seat. The caller (the parent AI, acting as council chair) asks all seats the same question and synthesises the answers. The seats are read-only opinion agents; they never edit, write, or spawn.

| Seat | Agent | Model tier |
|------|-------|-----------|
| 1 | `council-fable` | Fable |
| 2 | `council-opus` | Opus (also the tie-break seat) |
| 3 | `council-sonnet` | Sonnet |
| 4 | `council-haiku` | Haiku |
| 5 (optional) | `codex` CLI | Codex, only when the `codex` CLI is installed |

<details>
<summary>Council protocol, quorum and approval tiers</summary>

**Trigger phrases:** "BOD", "assemble", "the board", "the council", "convene the council". `/resume-bod` restores the board context from memory, then runs the same protocol.

**One wave, no team:**

1. The caller writes one brief and sends it to every seat in a single message, so all seats get the identical text.
2. No seat sees another seat's answer. There is no `TeamCreate` and there are no waves.
3. Each seat answers in at most 300 words: `VERDICT`, `REASONS`, `RISKS`, `CONFIDENCE`, `DISSENT`.
4. The caller synthesises: a table of verdicts, the points of agreement, the points of disagreement, and a recommendation.

**Quorum:** 3 of 5 seats. When the caller is a cheap model, `council-opus` breaks a tie.

The full protocol is in `core/memory/agency-council.md` (installed at `{agency-root}/core/memory/agency-council.md`).

**Approval tiers:**

| Tier | Approver | Examples |
|------|----------|---------|
| 1 | Project Director (within `scope.json`) | File edits <10 lines, read-only, docs within project scope |
| 2 | Council Chair (parent AI) | New files, code >10 lines, config changes, deps, migrations |
| 3 | Human operator | Deployments, secrets, destructive ops, external comms, financial |

Each project carries a `scope.json` that defines the PD's authority boundaries. Tier 1 bypass is limited to the scope defined there.

</details>

### Extension Points

**Adding a skill:**
1. Create `skills/{skill-name}/SKILL.md` with the skill definition
2. Register it in `skills/INDEX.md`
3. Add its skill-router overlay entry: `python3 scripts/skill-route-overlay-add.py {skill-name} [--domain D --hint H]` (required for contributors: CI's menu gate fails without it; for users it is only needed to make the skill routable once the optional router is enabled)
4. Invoke with `/{skill-name}` in Claude Code

**Adding an agent:**
1. Create the agent spec in `agents/{folder}/{agent-name}.md`
2. Follow the frontmatter convention (name, role, modelTier)
3. Reference it in the folder's `INDEX.md`
4. See `agents/CONTRIBUTING.md` for the full spec format

**Adding an agent folder:**
1. Create `agents/{folder}/` with an `INDEX.md`
2. Add the agent files (project PD definitions live in these folders; `project-scaffolder` writes new PDs there)
3. See `docs/DEVELOPER.md` for the full guide

---

**GitHub:** [https://github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency)

**License:** MIT — use it however you want.

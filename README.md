# The Agency

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)
![Cloud: Zero dependencies](https://img.shields.io/badge/Cloud-Zero%20Dependencies-green)
![Skills: 270+](https://img.shields.io/badge/Skills-270%2B-orange)
![Agents: 204+](https://img.shields.io/badge/Agents-204%2B-purple)
![QA: Gates on every handoff](https://img.shields.io/badge/QA-Gates%20%2B%20Health%20Scores-red)

**Your AI agents remember everything, coordinate like a real team, and ship while you sleep.**

A multi-agent orchestration system built on Claude Code. 204+ specialist agents across 19 departments. Autonomous project execution with persistent memory, quality gates on every handoff, and intelligent model routing — all running on your machine, with no servers and no extra API keys.

---

## The Problem

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/.claude

# macOS / Linux
cd ~/.claude && ./install.sh

# Windows (PowerShell)
cd $HOME\.claude; .\install.ps1
```

That's it. 270+ skills and 200+ agents are live in `~/.claude/`, and the `agency` command is added to your PATH. Open Claude Code and they're ready.

```bash
agency onboard                        # Interactive setup wizard (start here)
agency new my-app "Build a task manager"
# In Claude Code: /recall my-app
```

**Already cloned but haven't set up?** Run this from inside the repo:

```bash
node cli/bin/agency.js onboard
```

It does everything — installs skills and agents, puts `agency` on your PATH, creates your first project and agent, and verifies the setup.

The PD loads and asks what to build. You supervise; it executes.

**Stuck? `agency upgrade` failing? Don't have the repo?** Run this one-liner from anywhere:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

It finds your existing clone (checks `~/.claude/`, `~/the-agency/`), pulls the latest, and recovers from broken states. If you don't have the repo yet, it clones it to `~/.claude/` for you.

---

## What The Agency Does

Four things make it different from a conversation with an AI:

**1. Memory that persists.** You run `/save-state` before you close Claude Code. Tomorrow you run `/recall`. The agent picks up exactly where it left off — open tasks, decisions made, what was blocked, what shipped. No re-explaining. No context collapse.

**2. A real team structure.** 200+ specialist agents are organized across 19 departments: Engineering, Design, Marketing, Content Creation, Sales, Testing, Game Development, Paid Media, Product, Project Management, Operations, Career, Specialized, Spatial Computing, Strategy, Integrations, and more. The right agent gets the right task automatically.

**3. Autonomous coordination.** You give direction to a Project Director. The PD decomposes the work, assigns it to specialists, runs the tasks in parallel, checks the output at every handoff, and reports back. You don't coordinate. You supervise.

**4. Intelligent model routing.** Every agent in the system carries a model assignment. Planning and orchestration work goes to Opus. Execution work goes to Sonnet. High-volume research and scraping goes to Haiku. You get the right model for every task without thinking about it.

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

- **4-tier autonomous chain**: PD → Coord → Mini-Coord → Task-Executor decomposes any project to atomic units. Mini-Coords keep drilling L6→L7→L8 without escalating to PD.
- **QA gates on every handoff**: No work gets ACK'd without a health-score pass. Gate: score ≥ 70 + zero CRITICALs. Example: 70 = tests pass but docs missing; 90+ = ship-ready.
- **Explicit ACK/NACK protocol**: Agents wait for approval before stopping. NACKs return a fix list. Rejected work loops back through QA. Traceability is built into the protocol.
- **270+ production-ready skills**: Memory, execution, QA, engineering, deployment, design, content, video, cloud (Cloudflare, Netlify, Terraform), and more — all invoked via `/skill-name`.
- **SQLite task store — nothing leaves your machine**: Task pipeline, gates, retries, blocking in `~/.claude/`. No servers. No API keys.
- **Session persistence**: `/save-state` and `/recall` make Claude Code fully resume-capable. Come back days later; the PD shows you exactly where it left off.
- **Agency Rooms** — file-based inter-agent chat with persistent rooms, RoomManager polling, NEXUS JSON handoffs, and 12-hour department digests.
- **Inter-PD Protocol** — PDs coordinate via filesystem, not messaging. Delegation through `inter-spawn-tasks/` directories with completion tracking.
- **Delegator Agent** — routing-as-a-service. Every agent spawns the Delegator before picking a subagent; it reads the full agency catalog and returns the right route. No hardcoded selection hierarchies.
- **Curator Agent** — context retrieval on demand. PDs and Coords spawn curator to query per-project knowledge graphs, Pinecone, and NotebookLM. Never reads full memory files into context.
- **Dept-Coord System** — department operations run as a parallel chain: Dept Head → Dept-Coord → Dept Member. Handles pipeline management, protocol improvement, and member development without mixing with project delivery.
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

Clone directly into `~/.claude/` — the Claude Code configuration directory. On Windows, this is `%USERPROFILE%\.claude\`. The repo becomes your config directory.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/.claude
cd ~/.claude
```

| Platform | Command | Requirements |
|----------|---------|-------------|
| macOS / Linux | `./install.sh` | bash |
| Windows | `.\install.ps1` | PowerShell |
| Any (Node.js) | `node cli/bin/agency.js init` | Node.js 18+ |

**What gets installed:**

```
~/.claude/
├── skills/              ← 270+ skills as {name}/SKILL.md directories
│   ├── backend/SKILL.md
│   ├── frontend/SKILL.md
│   ├── ship/SKILL.md
│   └── ...
├── agents/              ← 200+ agents organized by department
│   ├── engineering/
│   ├── design/
│   ├── content-creation/
│   └── ...
├── projects/            ← per-project state (created by `agency new`)
├── sessions/            ← session logs (created by `/save-state`)
├── memory/              ← persistent memory layer
└── task-store.db        ← SQLite task pipeline (Node.js install only)
```

Override the install location with `AGENCY_HOME=/custom/path ./install.sh`.

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
# Clone into ~/.claude — this IS the Claude Code config directory
git clone https://github.com/Tekkiiiii/the-agency.git ~/.claude
cd ~/.claude

# One command sets everything up: checks prerequisites, installs all
# skills and agents, creates ~/.agency/, and walks you through first project
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

The three Coords run in parallel. Each decomposes further and spawns Task-Executors. You see output as each unit completes:

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
- **`~/.agency/skills/`** — 270+ skills ready to invoke
- **`~/.agency/agents/`** — 200+ specialist agents organized by department
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

### Project Directors

Spawned via `/recall {project}`. Owns the project end-to-end:

1. Decompose work into tasks
2. Assign to specialists via Coord/Mini-Coord chain
3. Gate completed work against QA criteria
4. Escalate blockers
5. Persist state via `/save-state`

## Skills Library — 270+ Skills

**Memory & Session**: `save-state`, `recall`, `pd-resume`, `wrap`, `unwrap`, `project-status`, `context-save`, `context-restore`, `freeze`, `unfreeze`

**Coordination**: `swarm`, `delegate`, `pd-spawn`, `task-handoff`, `task-store`, `room-manager`, `room-manager-digest`, `nexus-gatekeeper`, `sync-md-json`

**Planning**: `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `plan-devex-review`, `plan-tune`, `office-hours`, `retro`, `seed`, `project-expansion-scout`

**Pipelines** (multi-stage workflows): `pipeline-feature`, `pipeline-bugfix`, `pipeline-content`, `pipeline-audit`, `pipeline-deploy`, `pipeline-seo-geo-aeo`

**Execution**: `ship`, `land-and-deploy`, `setup-deploy`, `canary`, `qa`, `qa-only`, `run-acceptance-tests`

**Quality & Critique**: `design-review`, `review`, `codex`, `cso`, `document-release`, `backend-critique`, `design-critique`, `content-critique`, `marketing-critique`, `operations-critique`, `product-critique`, `security-critique`, `workflow-critique`, `devex-review`, `careful`

**Content & Writing**: `humanizer`, `proofreader`, `content-polish`, `content-creator`, `content-strategy`, `copywriting`, `stop-slop`, `tech-writer`, `marp`, `markitdown`, `make-pdf`, `promt-engineering`, `xlsx-toolkit`, `vietnamese-language`

**Engineering — Backend**: `backend`, `security`, `webhook-security`, `postgresql-schema`, `supabase-sql`, `multi-role-auth`, `laravel-builder`, `admin-shell-foundation`

**Engineering — Frontend**: `frontend`, `shadcn-ui`, `cult-ui`, `tailwind`, `next-best-practices`, `css-animations`, `image-to-code`, `svgl`, `extract-design`, `excalidraw-diagram`

**Design & UI/UX**: `ui-ux-pro-max`, `impeccable`, `design-html`, `high-end-visual-design`, `minimalist-ui`, `industrial-brutalist-ui`, `emil-design-eng`, `gpt-taste`, `brandkit`, `figma-ui-ux-consistency`

**Video & Media**: `ffmpeg`, `video-use`, `hyperframes`, `hyperframes-cli`, `hyperframes-media`, `remotion-best-practices`, `lottie`, `animejs`, `gsap`, `waapi`, `three`, `gpt-image-prompts`, `imagegen-frontend-web`, `imagegen-frontend-mobile`

**Deployment**: `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy`, `netlify-deploy`

**Cloud — Cloudflare**: `cloudflare`, `workers-best-practices`, `wrangler`, `durable-objects`, `agents-sdk`, `cloudflare-email-service`

**Cloud — Netlify**: `netlify-config`, `netlify-functions`, `netlify-edge-functions`, `netlify-forms`, `netlify-blobs`, `netlify-db`, `netlify-caching`, `netlify-image-cdn`, `netlify-frameworks`, `netlify-ai-gateway`

**Cloud — Terraform**: `terraform-style-guide`, `terraform-test`, `terraform-stacks`, `terraform-search-import`, `new-terraform-provider`, `provider-actions`, `provider-resources`, `refactor-module`, `azure-verified-modules`, `finops`

**Ops & Debugging**: `self-healing`, `investigate`, `guard`, `health`, `web-perf`, `webapp-testing`

**Browser & Scraping**: `browse`, `agent-browser`, `lightpanda`, `scrape`, `firecrawl-agent`, `firecrawl-crawl`, `firecrawl-scrape`, `pair-agent`

**Superpowers** (28 gstack workflow skills): `superpowers-brainstorming`, `superpowers-systematic-debugging`, `superpowers-dispatching-parallel-agents`, `superpowers-executing-plans`, `superpowers-writing-plans`, `superpowers-test-driven-development`, and 22 more.

**Domain-Specific**: `hotel-pms`, `restaurant-pos`, `reservation-booking`, `stripe-best-practices`, `better-auth-best-practices`, `legal-contract-review`, `n8n-automation`, `sanity-best-practices`, `tech-stack`

Full categorized registry: [`skills/INDEX.md`](skills/INDEX.md)

## File Structure

```
the-agency/
├── core/
│   ├── agents/          # PD/Coord/Mini-Coord/Exec/Delegator/Curator templates
│   ├── runbooks/        # Boot, escalation, kickoff, dept-coord, protocol registry
│   ├── ORG.md           # Org chart, authority model, dept-coord system
│   ├── PD_PROTOCOL.md   # PD quick reference
│   ├── memory/          # Memory system specification
│   ├── nexus/           # NEXUS coordination protocol
│   └── tasks/           # Task store pattern
├── cli/                 # Node.js CLI (agency init/new/tasks/skill/status)
├── docs/                # User-facing documentation
├── agents/              # 204+ agent definitions (19 departments + dept-coords)
├── skills/              # 270+ reusable workflow skills
└── plans/               # Architecture decision records
```

## Contributing

Two ways to extend the system:

**New agents** — add a specialist to an existing department or propose a new one. See `agents/CONTRIBUTING.md` for the agent spec format and review process.

**New skills** — create a markdown file in `skills/`, register it in `skills/INDEX.md`, and invoke it with `/skill-name`. Skills are reusable workflows: a skill can call other skills, spawn agents, or chain multi-stage pipelines. See `docs/DEVELOPER.md` for the full guide.

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

**NEXUS Protocol** — file-based 6-phase handoff doctrine for inter-agent coordination. Handoff artifacts are JSON files, processed by RoomManager.

**Skills** — markdown-based reusable workflows loaded from `~/.claude/skills/`, registered in `INDEX.md`.

**Project Directors** — one per project, own delivery end-to-end.

### 4-Tier Agent Chain

```
PD  (L1→L3 decomposition, spawns Coords)
 └── Coord × N  (L3→L4→L5→L6, spawns Exec or Mini-Coord, autonomous)
      └── Mini-Coord × M  (L6→L7→L8→L9, spawned for complex L6 tasks)
           └── Task-Executor × K  (executes exactly one atomic unit)
```

| Layer | Agent | Decomposes | Spawns | Model |
|-------|-------|-----------|--------|-------|
| L1–L3 | PD | L1 → L2 → L3 | Coord | Opus |
| L3–L6 | Coord | L3 → L4 → L5 → L6 | Exec or Mini-Coord | Opus |
| L6+ | Mini-Coord | L6 → L7 → L8 → L9 | Exec | Opus |
| Atomic | Task-Executor | — | — | Sonnet |

**Naming convention:**
- PD: `PD-{slug}` (e.g., `PD-my-saas-app`)
- Coord: `Coord-{l3-name}-{pun}` (e.g., `Coord-auth-Gatekeeper`)
- Mini-Coord: `Mini-{l3-name}-{pun}-{branch}` (e.g., `Mini-auth-Gatekeeper-loginFlow`)
- Exec: `Exec-{task}-{pun}` (e.g., `Exec-login-Keymaster`)

### PD Standard Protocol

Every Project Director follows 3 mandatory rules on every spawn, without exception:

1. **Decompose** — break every task into the smallest independent sub-tasks before acting
2. **Agent Selection via Delegator** — when spawning a subagent, spawn the Delegator first. It reads the full agency catalog and returns the right agent, department, skill, or protocol. Never default to general-purpose — always route through Delegator.
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

After all Coords report DONE, PD spawns `Coord-qa-Canary` (Sonnet, Testing Lead) to QA the combined L3 output before reporting to root. Deliverables: health score (0–100), issues by severity (CRITICAL/HIGH/MEDIUM/LOW), screenshots at `{project}/memory/qa/screenshots/`, report at `{project}/memory/qa/qa-report-final-{timestamp}.md`.

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

Handoff artifacts are JSON files placed in `{room}/handoffs/`. RoomManager processes them automatically and routes to the receiving agent.

</details>

### Delegator — Routing Layer

The Delegator is a stateless service agent. Any agent (PD, Coord, dept head) spawns it when they need to pick the right agent, skill, department, or protocol for a task.

```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Delegator — route: {task-summary}",
  prompt: "Read ~/.claude/agents/specialized/delegator.md fully.\n\nRouting question: {task}\nCaller: {your name}"
})
```

The Delegator reads the agency catalog (`memory/agency-dispatch.md`), org chart, department INDEX files, protocol registry, and skill index. It returns a structured `DELEGATOR ROUTING` recommendation. It never executes work, never writes files, never holds state.

**Routing rules:** Skills before agents (cheaper), department leads for department-scoped work, PDs for project deliverables, Dept-Coord for department-operational work, inter-spawn for cross-authority tasks.

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

### Dept-Coord System

Departments run their own operational work through a parallel chain that mirrors the PD-Coord chain but is scoped to department initiatives (pipeline management, protocol improvement, member development).

```
Dept Head (Opus)       — decomposes D1 → D2 → D3, dispatches Dept-Coords
  └── Dept-Coord (Sonnet)  — owns D3 track, decomposes D3 → D6, dispatches members
        └── Dept Member (Sonnet)  — executes one D6 atomic task
```

Each department has a `{dept}-coord.md` agent in its directory. Dept-Coords use identical patterns to project Coords: scratch files, QA gates, ACK/NACK handshakes, curator for memory retrieval, and hard authority ceilings.

### Inter-PD Filesystem Protocol

Background agents cannot receive messages. PDs coordinate via the filesystem instead of SendMessage.

5-step protocol:

1. PD-A writes briefing to: `{target-project}/memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md`
2. PD-A creates tracker: `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`
3. PD-A spawns PD-B via Agent tool with `run_in_background: true`
4. PD-B completes work, appends completion to caller's `delegated-{task-id}.md`
5. On next `/pd-resume`, PD-A reads completion and marks task done

Use `/pd-spawn` for the full protocol.

### Model Routing Table

All agents carry a `modelTier` tag in their frontmatter. Routing is automatic.

| Model | Role | Used for |
|-------|------|---------|
| Opus | Leadership, orchestration | PDs, Coords, Mini-Coords, dept heads, planning |
| Sonnet | Execution, synthesis | Task-Executors, assistants, QA agents |
| Haiku | Menial, high-volume | Scraping, research, data extraction |

### Agency Rooms

File-based inter-agent communication. Agents coordinate through rooms, not direct messaging.

Three room types:
- **Project rooms** — one per active project, owned by the project's PD
- **Department rooms** — one per department; dept heads coordinate members here
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
    └── rolling.md      # Dept head status feed (dept rooms only)
```

Message format:
```
[{ISO timestamp}] @{agent-name} [{phase}]: {content}
```

RoomManager polls on a configurable interval (default: 10 minutes). On each poll it reads new messages, extracts structured signals into `context/shared.md`, routes handoff JSON to named agents, and emits 12-hour digests to department heads.

Run with `/room-manager`.

Anti-patterns:
- Do NOT send direct messages between agents — everything goes through rooms
- Do NOT implement recurring status loops — use on-demand reads via `/swarm`
- Do NOT skip the handoff JSON — without it, context is lost between sessions

</details>

### Agency Council and Governance

The Agency Council is the governing body for all cross-department decisions. All 19 department leaders report to the Council Chair (the parent AI).

Council members:

| Leader | Role | Department |
|--------|------|-----------|
| Backend Architect | engineering-lead | Engineering |
| Brand Guardian | design-lead | Design |
| Game Designer | game-development-lead | Game Development |
| Growth Hacker | marketing-lead | Marketing |
| Chief Content Officer | content-creation-lead | Content Creation |
| Sales Coach | sales-lead | Sales |
| PPC Campaign Strategist | paid-media-lead | Paid Media |
| Sprint Prioritizer | product-lead | Product |
| Studio Producer | pm-lead | Project Management |
| Reality Checker | testing-lead | Testing |
| Infrastructure Maintainer | operations-lead | Operations |
| Agents Orchestrator | specialized-lead | Specialized |
| XR Interface Architect | spatial-lead | Spatial Computing |
| career-ops PD | career-lead | Career |

<details>
<summary>Council spawn protocol and approval tiers</summary>

**Trigger phrases:**
- "BOD", "assemble", "assemble the board", "the board", "the council", "activate the agency council"
- "convene the council", "call the board to order", "full agency", "all hands", "agency-wide [project]"

**Spawning steps:**

```
1. Use TeamCreate to create a team named "agency-council"
2. Spawn leaders in TWO WAVES (race-condition prevention):
   Wave 1 (6): engineering-lead, design-lead, game-development-lead,
               marketing-lead, content-creation-lead, sales-lead
   Wave 2 (8): paid-media-lead, product-lead, pm-lead, testing-lead,
               operations-lead, specialized-lead, spatial-lead, career-lead
   Wait ~30s for Wave 1 before spawning Wave 2.
3. Each leader joins "agency-council" and sends intro to "team-lead"
4. Parent AI is the council chair
5. Send welcome brief explaining current priorities
```

**Why two waves:** Spawning more than 6 agents in parallel causes race-condition writes to the team config file, breaking late-joiners.

**Approval tiers:**

| Tier | Approver | Examples |
|------|----------|---------|
| 1 | Department Leader | File edits <10 lines, read-only, docs within project scope |
| 2 | Council Chair (parent AI) | New files, code >10 lines, config changes, deps, migrations |
| 3 | Human operator | Deployments, secrets, destructive ops, external comms, financial |

Each project carries a `scope.json` that defines the PD's authority boundaries. Tier 1 bypass is limited to the scope defined there.

</details>

### Extension Points

**Adding a skill:**
1. Create `skills/{skill-name}/SKILL.md` with the skill definition
2. Register it in `skills/INDEX.md`
3. Invoke with `/{skill-name}` in Claude Code

**Adding an agent:**
1. Create the agent spec in `agents/{department}/{agent-name}.md`
2. Follow the frontmatter convention (name, role, modelTier, department)
3. Reference in the department's index file
4. See `agents/CONTRIBUTING.md` for the full spec format

**Adding a department:**
1. Create `agents/{department}/` directory
2. Add department head and member agent files
3. Register the department head in `agents/ORG.md` Leadership Table
4. Add the department room to `agency-rooms/`
5. See `docs/DEVELOPER.md` for the full guide

---

**GitHub:** [https://github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency)

**License:** MIT — use it however you want.

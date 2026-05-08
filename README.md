# The Agency

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)
![Agents: 175+](https://img.shields.io/badge/Agents-175%2B-purple)
![Skills: 166](https://img.shields.io/badge/Skills-166-orange)
![Departments: 14](https://img.shields.io/badge/Departments-14-green)
![Tools: 9](https://img.shields.io/badge/Tools-9-red)

**Your AI agents remember everything, coordinate like a real team, and ship while you sleep.**

A multi-agent orchestration system built on Claude Code. 175+ specialist agents across 14 departments. Autonomous project execution with persistent memory, quality gates on every handoff, and intelligent model routing — all running on your machine, with no servers and no extra API keys.

---

## The Problem

Every AI session starts from zero. You describe your project. You explain what you already built. You re-establish the context you lost when the last conversation ended. You do this every single time.

And even when the AI is working, you are the bottleneck. You can only have one conversation. While the AI is writing backend code, nothing is happening on the frontend. You manage the flow. You pass the handoffs. You are the coordinator.

The ceiling hits fast when projects get complex. The AI can write a function. It can draft an email. But keeping track of a multi-week project across sessions, running parallel workstreams, checking its own work — that requires more than a single conversation.

Most people reach this ceiling and conclude that AI just can't handle real projects. That conclusion is wrong. The tooling was missing.

---

## What The Agency Does

Four things make it different from a conversation with an AI:

**1. Memory that persists.** You run `/save-state` before you close Claude Code. Tomorrow you run `/recall`. The agent picks up exactly where it left off — open tasks, decisions made, what was blocked, what shipped. No re-explaining. No context collapse.

**2. A real team structure.** 175+ specialist agents are organized across 14 departments: Engineering, Design, Marketing, Content Creation, Sales, Testing, Game Development, Paid Media, Product, Project Management, Operations, Career, Specialized, and Spatial Computing. The right agent gets the right task automatically.

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

### Scenario B: Give direction, walk away

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

You didn't write the auth code. You didn't coordinate the specialists. You didn't check the tests. The PD owned the whole thing.

---

## How It Works

The system runs on a four-tier agent chain:

```
YOU
 └── Project Director (PD)
      └── Coordinator (one per workstream)
           └── Mini-Coordinator (for complex branches)
                └── Task Executor (one per atomic unit)
```

**Project Director.** One per project. Owns the work from first conversation to final ship. Breaks the project into workstreams, assigns them to Coordinators, and stays in the loop on every result. This is who you talk to.

**Coordinator.** One per major workstream — auth, database, frontend, testing. Owns its piece end-to-end. Spawns executors in parallel. Reviews their output before reporting done.

**Mini-Coordinator.** Steps in when a workstream gets complex enough to branch further. Handles the sub-tasks so the Coordinator stays focused on the big picture.

**Task Executor.** Does exactly one thing. Writes one function, runs one test, updates one file. Reports back with a health score and QA evidence. No shortcuts.

Quality gates sit between every level. An agent cannot pass work up the chain until its output scores at or above the threshold. Work that fails comes back with a fix list.

---

## Key Capabilities

### Autonomous Agent Orchestration

Project Directors run end-to-end ownership on every project. The PD decomposes your goal into tasks, spawns the right specialists, parallelizes independent workstreams, and gates every output before accepting it. You set the direction and review key decisions. The PD handles everything else.

When you need a cross-department effort, say "assemble" and the Agency Council convenes — department leaders across all functions, ready to coordinate.

### Memory That Survives Sessions

Four memory layers work together to keep your project's context intact:

- **Sessions** — what happened in each working session
- **State** — the current phase, open blockers, and next steps
- **Lessons** — patterns learned from corrections (append-only, never rewritten)
- **Decisions** — architectural choices that apply across projects

Run `/save-state` when you stop. Run `/recall` when you return. That's the full interface.

### Smart Context Management

Agents boot in ~500 tokens. Each project has a pre-built routing file that loads only what the PD needs to start, and department indexes load on demand — not at startup. Agents pull in context relevant to their current task and nothing else, keeping the context window lean even on complex projects.

### Intelligent Model Routing

Every agent is tagged with a model tier in its definition file:

- Leadership, planning, and orchestration work runs on **Opus**
- Feature development and execution runs on **Sonnet**
- Research, scraping, and high-volume tasks run on **Haiku**

The system routes automatically. You never pick the model manually.

### Skills Library

166 skills ship with the repo — workflows you invoke with a slash command. `/save-state` saves your session. `/autoplan` runs a multi-reviewer planning pass (CEO, engineering, and design review). `/ship` handles merge, test, and PR creation. `/swarm` checks status across your entire project portfolio at once.

Skills can chain into pipelines. A single command can trigger research, then draft content, then critique it, then polish it — with quality gates between each stage.

### 14 Departments, 175+ Specialists

Every department has a head who owns quality for that function. Members execute under PD direction. The matrix model means specialists bring deep skill without losing coordination.

The **Agency Council** is the governing body for cross-department decisions — department heads chaired by the parent AI. When a decision affects multiple departments, the council assembles and resolves it.

---

## Quick Start

**Prerequisites:** Claude Code, Node.js 18+

```bash
# 1. Clone and initialize
git clone https://github.com/Tekkiiiii/the-agency.git
cd the-agency && npx agency init

# 2. Create your first project
agency new my-app "Build a task manager"

# 3. Open your project in Claude Code, then type:
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

---

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
2. **Parallelize** — spawn one subagent per sub-task simultaneously
3. **Report** — send each completion to team-lead immediately, not at the end

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

### Memory System (4 Layers)

| Layer | Location | Written by | Purpose |
|-------|----------|-----------|---------|
| Sessions | `~/.claude/sessions/{project}/` | `/save-state` | Per-session logs, resumable |
| State | `~/.claude/projects/{project}/STATE.md` | PD continuously | Current phase, blockers, next-session prompt |
| Lessons | `~/.claude/lessons/{stack}.md` | After corrections | Root-cause → lesson → avoid pattern; append-only |
| Decisions | `~/.claude/decisions/` | Team-lead | Cross-cutting architectural decisions |

Initialization (`agency init` creates):
```
~/.claude/
├── sessions/
├── projects/
├── lessons/
├── decisions/
└── memory/
```

Each project also carries its own memory structure:
```
{project}/
├── scope.json
├── approvals/
└── memory/
    ├── sessions/
    ├── decisions.md
    ├── lessons/
    └── status/
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

The Agency Council is the governing body for all cross-department decisions. All 14 department leaders report to the Council Chair (the parent AI).

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

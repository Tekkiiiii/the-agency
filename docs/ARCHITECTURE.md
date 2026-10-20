# Architecture

## Overview

The Agency is a layer of skills, agents, and memory files that installs into Claude Code (`~/.claude/`). It fixes the gaps Claude Code has out of the box: memory that survives sessions, agents that finish what they start, QA gates before "done", and token-lean routing. It coordinates work through a file-based memory and task system — no cloud, no extra API keys.

```
┌─────────────────────────────────────────────────────────────┐
│                      User (you)                            │
│                  Claude Code + agency CLI                  │
└──────────────────────────┬────────────────────────────────┘
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

## Core Components

### Task Store (SQLite)
Source of truth for pipeline state. All agents read/write here.
- `~/.claude/task-store.db`
- Schema: tasks with status, blocked_by, gate_status, retry_count

### Memory System

The memory system uses `next-session.md` as the single source of truth for PD startup. `/save-state` writes it; `/recall` reads it. That keeps the startup payload small (15 lines max) and avoids loading stale state.

| File | Location | Purpose |
|------|----------|---------|
| `next-session.md` | `{project}/memory/` | PD startup SSOT: phase, next action, blockers, decisions (max 15 lines) |
| `sessions/YYYY-MM-DD.md` | `{project}/memory/sessions/` | Full session logs, append-only |
| `decisions.md` | `{project}/memory/` | Architectural decisions, append-only |
| `heartbeat.md` | `{project}/memory/` | Live phase status, updated each session |
| `lessons/*.md` | `{root}/memory/lessons/` | Root-cause lessons by stack, append-only |

Each project carries its own memory structure:

```
{project}/memory/
├── next-session.md      # PD startup SSOT, read on every /recall
├── heartbeat.md         # phase status, updated each session
├── decisions.md         # architectural decisions (append-only)
├── sessions/            # session logs by date
├── lessons/             # per-stack lessons (synced from root)
├── tasks/
│   ├── ongoing/         # active task files
│   └── completed/       # completed task archive
├── agents/
│   ├── pd-scratch.md    # PD working scratch
│   ├── pd-status-live.md# append-only status log (zero-cost on-demand reads)
│   └── coords/          # Coord scratch files
└── qa/
    ├── qa-report-final-{timestamp}.md
    └── screenshots/
```

### Project Knowledge: Direct Lookups

PDs and Coords look project context up themselves, in this order:

1. The wiki: `MEMORY.md`, the memory files it indexes, and the project's own `memory/` files.
2. A shared-memory MCP server, if you run one.
3. NotebookLM, for research topics only.

When a question spans several of these, or you cannot name the source, spawn one read-only `general-purpose` agent (Sonnet) with that order in its prompt. Full protocol: `runbooks/service-lookups.md`.

### NEXUS Protocol

NEXUS is the handoff doctrine. Every agent writes what it knows; the next agent reads what it needs. Handoff artifacts are JSON files, and the sender tells the receiving agent the handoff exists.

| Phase | Name | What happens |
|-------|------|-------------|
| 0 | Register | Create project structure and task |
| 1 | Brief | Assign work with full context |
| 2 | Work | Execute, document incrementally |
| 3 | Handoff | Transfer with evidence and acceptance criteria |
| 4 | Review | Gate work against acceptance criteria |
| 5 | Archive | Close out, record lessons |

Key rules:

1. Write before you stop: never end a session without saving state.
2. Gate before handoff: do not pass work that fails its criteria.
3. Surface blockers fast: escalate within one session.
4. Lessons from mistakes: append, never overwrite.

| Escalation | Trigger | Action |
|------------|---------|--------|
| tier-1 | Minor blocker | Note in session log, continue |
| tier-2 | Major blocker | Escalate to team-lead, pause task |
| tier-3 | Crisis | Escalate to council, stop work |

Protocol files: `core/nexus/`.

### Hook System

Shell scripts wired into four Claude Code lifecycle events (SessionStart, PreToolUse, PostToolUse, Stop). They gate sensitive writes, scan for secrets, protect linter config, detect stalls and crashes, and track cost. Profile-aware (`standard` / `strict` / `minimal`). Reference: [HOOKS.md](HOOKS.md).

### Skills
Reusable workflow procedures invoked via `/skill-name`:
- Loaded from `~/.claude/skills/`
- Registered in `~/.claude/skills/INDEX.md`
- Can be installed from the agency catalog

### Project Directors (PDs)
Each project has a dedicated PD agent that:
- Owns the project from spec to ship
- Maintains the task pipeline
- Reports to the parent AI (the main session)
- Persists state via memory system

## Data Flow

1. **User** spawns a project or assigns work
2. **PD** creates tasks in task store, hands them to Coords or Execs (workers run as `general-purpose` + 1-3 skills)
3. **Execs** execute, write session logs, gate tasks
4. **PD** monitors pipeline, escalates blockers
5. **On session end**: `/save-state` writes session log
6. **Next session**: agent reads memory, resumes

### Worked example: adding billing to a task manager

The project is `taskboard`, a task-manager app whose sign-up and login already shipped. The goal: "Add subscription billing: monthly and annual Stripe plans, a checkout page, and a webhook that marks an account as paid." The paths below are illustrative.

**1. Plan.** The PD reads `next-session.md`, finds no `memory/dev-plan.md`, and writes one. It decomposes the goal into three L3 chunks and applies the two-condition parallel rule (no dependency edge, disjoint `writes-to[]`):

| L3 chunk | Writes to | Depends on | Layer |
|----------|-----------|------------|-------|
| Billing schema (plans and subscriptions tables) | `db/migrations/`, `src/db/types.ts` | none | 1 |
| Stripe webhook handler | `src/api/stripe-webhook.ts`, its tests | schema | 2 |
| Checkout page | `src/app/billing/` | schema | 2 |

The webhook and the checkout page both need the tables, so they wait for layer 1. They share no dependency and no file, so they run in parallel once it is done. A freshly written plan with layers and cross-L3 dependencies counts as structurally complex, so the PD runs `/save-state taskboard` and asks the main session for a fresh PD (a `RESPAWN_REQUEST taskboard` line) to deploy it with a clean context window. A single-layer plan skips this step and runs in the same session.

**2. Layer 1.** The PD spawns one Coord, `Coord-schema-Architect`, with its scoped structure file. The migration fits one Exec, so the Coord does not decompose it. It spawns one Exec (`general-purpose` plus `/backend`). The migration touches two files, so the Exec is TIER_B: it writes an APPROACH request to its checkpoint file before editing, and the Coord replies `ACK_APPROACH`. At about 50% effort the Exec writes a CHECKPOINT and gets `ACK_CONTINUE`. It finishes with `DONE` plus evidence: the migration applying and rolling back on a scratch database. A database migration also needs the four-item evidence bundle (script diff, dry-run and rollback output, affected-row or schema-diff confirmation, no-data-loss confirmation) before the Coord accepts it.

**3. Gate.** The Coord accepts an Exec report at health 85 or higher with no CRITICAL or HIGH issue. Accepting means not re-spawning the Exec. A lower score spawns a continuation Exec that carries the fix list. When every child is accepted, the Coord spawns a QA Exec (`/qa-only`) over the combined L3 output, then delivers `L3 COMPLETE + QA GATE COMPLETE` with the health score as its final result and stops. The PD checks the score against the same bar and logs the ACK to `memory/agents/pd-status-live.md`.

**4. Layer 2.** In one message the PD spawns the webhook Coord and the checkout Coord, and tells each how many Execs it may run (`Exec slots allotted: 3` and `2`), because a PD tree runs at most five Execs at once. The webhook Coord runs the handler first and its tests after, since the tests depend on the handler. The checkout Coord needs one Exec. Each follows the same gate as in step 3.

**5. Integration.** With all three Coords accepted, the PD reads `pd-structure.md` for the integration contracts and spawns an integration tester (`general-purpose` plus `/qa-only`, `/run-acceptance-tests`, `/webapp-testing`). It drives the whole path: pick a plan on the checkout page, receive a Stripe test event, see the account flip to paid. A pass needs a score of 85 or higher and no CRITICAL violation. A failure sends targeted fix Execs and repeats only this phase.

**6. Report and save.** Before it claims any file as delivered, the PD runs `ls -la` and `wc -l` on it and pastes the output into the final digest (overall health, per-L3 scores, open CRITICAL and HIGH issues, report path). It sends the digest to the main session and waits for your ACK or NACK. After an ACK it writes a `Session Delta` block to `memory/agents/pd-scratch.md`, runs `/save-state taskboard`, and stops. The next `/recall taskboard` shows the saved next action.

## Extensibility

The system is designed to be extended:

- **New projects**: `agency new <slug> "<description>"`.
- **New skills**: create `skills/{skill-name}/SKILL.md`, register it in `skills/INDEX.md`, add its skill-router overlay entry (`python3 scripts/skill-route-overlay-add.py {skill-name} [--domain D --hint H]`; CI's menu gate requires it for contributors), then invoke it with `/{skill-name}`.
- **New agents**: add the spec in `agents/{folder}/{agent-name}.md` with the frontmatter convention (name, role, modelTier), and list it in the folder's `INDEX.md`. Register an agent only for a PD, Coord, critic, council seat or service agent; domain work is `general-purpose` plus skills.
- **New agent folders**: create `agents/{folder}/` with an `INDEX.md`; project PD definitions live in these folders and `project-scaffolder` writes new PDs there.

The step-by-step guide is [DEVELOPER.md](DEVELOPER.md).

---

## Tiered Agent Architecture

Work runs as one chain: PD → Coord → Exec.

### Project Delivery Chain (PD-Coord)

```
PD  (L1→L3 decomposition, spawns Coords)
 └── Coord × N  (L3→L4→L5→L6, spawns Exec or Mini-Coord, autonomous)
      └── Mini-Coord × M  (L6→L7→L8→L9, spawned for complex L6 tasks, reports to parent Coord)
           └── Exec × K  (general-purpose + Skills; executes exactly one atomic unit, reports to spawner)
```

| Layer | Agent | Decomposes | Spawns | Model |
|-------|-------|-----------|--------|-------|
| L1–L3 | PD | L1 → L2 → L3 | Coord | Opus |
| L3–L6 | Coord | L3 → L4 → L5 → L6 | Exec or Mini-Coord | Sonnet |
| L6+ | Mini-Coord | L6 → L7 → L8 → L9... | Exec | Sonnet |
| Atomic | Exec (general-purpose + Skills) | No | — | Sonnet |

**Critics.** `critique-*` agents and `sag-critique` are spawned directly by the PD or Coord and report to whoever spawned them (the caller). They sit outside any folder hierarchy.

**Agent folders.** `agents/<folder>/` directories (`council`, `critiques`, `project-management`, `specialized`) stay as homes for PD definitions (`project-scaffolder` writes new PDs there). They have no heads and no coordinators.

**Content.** One pipeline: PD → Coord → writer → `/content-polish` → critics via `/cc-loop` (`runbooks/content-request-protocol.md`).

### Naming Convention

- PD = `PD-{slug}` — project-level orchestrator (e.g. `PD-taskboard`)
- Coord = `Coord-{l3-name}-{pun}` — L3 owner (e.g. `Coord-auth-Gatekeeper`)
- Mini-Coord = `Mini-{l3-name}-{pun}-{branch}` — L6 owner (e.g. `Mini-auth-Gatekeeper-loginFlow`)
- Exec = `Exec-{task}-{pun}` — implementation unit (e.g. `Exec-login-Keymaster`)

### Decomposition Rules

| Level | Who | Stops At |
|-------|-----|---------|
| L1 | PD | L3 |
| L3 | Coord | L6 |
| L6 | Mini-Coord | Smallest implementable unit |
| Atomic | Exec (general-purpose + Skills) | — |

### PD Standard Protocol

Every Project Director follows a mandatory 3-rule protocol:

1. **Decompose**: break every task into the smallest independent sub-tasks before acting.
2. **Parallelize**: spawn one subagent per sub-task simultaneously.
3. **Report**: log each completion to `memory/agents/pd-status-live.md` as it lands, not at the end. The main session is messaged only for an escalation, a blocker, or when all work is complete and awaiting your ACK.

When the right agent or skill is not obvious, the PD spawns the [Delegator](#delegator--agency-routing-agent) first.

This protocol applies to every PD spawn, every time, without exception.

### Model Routing

Every agent carries a `modelTier` tag in its frontmatter, and routing follows it.

| Model | Role | Used for |
|-------|------|---------|
| Opus | Leadership, planning | PDs, architecture and final review |
| Sonnet | Orchestration, execution | Coords, Mini-Coords, Execs, QA agents |
| Haiku | Menial, high-volume | Scraping, research, data extraction, the Delegator |

**1M context (`[1m]`) is selective, not fleet-wide.** Only orchestrator roles (PD, Coord, Mini-Coord) carry the `[1m]` model suffix, because their context grows with the size of the work rather than the size of their own brief. Everything below them stays plain. Policy and rationale: `core/ORG.md` (Model tiering).

`modelTier:` is a documentation tag only. `model:` is the key Claude Code reads, and it is the one `[1m]` attaches to. Reasoning effort per task type is a separate policy; see [SKILLS.md](SKILLS.md#effort-policy).

### Tool Access Stays Restricted Even With Tool Search

Per-agent `tools:` restrictions in frontmatter (e.g. orchestrators limited to
`Read, Write, Edit, Grep, Glob, Bash, Agent, SendMessage, Skill, Task*, WebFetch,
WebSearch` — no MCP tools) remain necessary even though Claude Code ships MCP tool
search (deferred tool-schema loading). Tool search is conditionally unavailable —
proxies without the `ENABLE_TOOL_SEARCH` override set, Google Cloud Agent Platform,
and Haiku models all fall back to full upfront schema loading regardless of intent.
The `tools:` restriction is the guaranteed floor against context blowout; tool
search is a bonus optimization layered on top of it, not a replacement for it. Do
not remove or "simplify away" a `tools:` restriction on the reasoning that it's
redundant once tool search exists — the two mechanisms fail independently.

---

## Delegator — Agency Routing Agent

The Delegator is a stateless Haiku agent that routes work to the correct agent, skill, pipeline, or protocol. Any agent (PD or Coord) can spawn the Delegator when the right route is not obvious.

Member-level specialist roles are not registered agents. The Delegator returns `general-purpose` plus 1-3 skills from `skills/INDEX.md`. Coords, PDs, critics, council seats, and service agents (codebase-search) stay registered and are still returned by name.

```
Agent({
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Delegator — route: {task-summary}",
  prompt: "Read ~/.claude/agents/specialized/delegator.md fully.\n\nRouting question: {task}\nCaller: {your name}"
})
```

The Delegator:
- Reads the agency catalog (`memory/agency-dispatch.md`), org chart, agent-folder INDEX files and skill index
- Returns a structured routing recommendation (AGENT | SKILL | PIPELINE | PROTOCOL | INTER-SPAWN)
- Dies immediately after returning the recommendation — it holds no state

**Routing rules:** skills before agents (cheaper), PDs for project deliverables, Coords for one gated task, an Exec (`general-purpose` plus 1-3 skills) for the work itself, inter-spawn for cross-authority tasks.

**Routing exceptions** — spawn Delegator is NOT required when:
- The correct agent or skill is already known (e.g. `general-purpose` + `/frontend` for a UI task)
- The task is a `codebase-search` spawn (read-only file lookup — always fire-and-forget)

Definition: `agents/specialized/delegator.md`

---

## Agency Council

An advisory board of five seats: `council-fable`, `council-opus`, `council-sonnet`, `council-haiku` (one per Claude model tier, in `agents/council/`) plus an optional fifth seat run through the `codex` CLI when it is installed. Seats are read-only and answer in at most 300 words (`VERDICT`, `REASONS`, `RISKS`, `CONFIDENCE`, `DISSENT`).

The caller sends one identical brief to every seat in a single message (one wave, no `TeamCreate`); no seat sees another's answer. The caller synthesises a table of verdicts, agreements, disagreements, and a recommendation. Three of five seats is a quorum, and `council-opus` breaks a tie when the caller is a cheap model. Triggers: "BOD", "assemble", "the board", "the council", "convene the council"; `/resume-bod` restores context and then runs it. Protocol: `core/memory/agency-council.md` (installed at `{agency-root}/core/memory/agency-council.md`). Approval tiers for the actions a council advises on are in [Project Scope Management](#project-scope-management).

---

## Quality Gates (ACK/NACK Protocol)

Every agent-to-agent handoff has a mandatory QA gate before approval:

| Handoff | Reporter | Reviewer | ACK condition | NACK condition |
|---------|----------|----------|---------------|----------------|
| Exec → Coord | Exec sends DONE + QA | Coord reviews QA report | Health ≥ 85 (≥ 90 design/visual), no CRITICAL/HIGH | Health < 85 (< 90 design/visual) OR CRITICAL/HIGH present |
| Coord → PD | Coord sends L3 complete + QA | PD reviews Coord QA report | Health ≥ 85 (≥ 90 design/visual), no CRITICAL | Health < 85 (< 90 design/visual) OR CRITICAL/HIGH present |
| PD → root | PD sends final digest + QA | root (operator) | Explicit ACK | Explicit NACK with fix list |

Reports are asynchronous: an agent's report lands when the agent stops, and the agent is gone by then.

**ACK** = the reviewer accepts the report and does not re-spawn the agent. Nothing more is needed.
**NACK** = the reviewer spawns a fresh continuation agent with the fix list → it fixes → re-runs the QA gate → re-reports

**Consent for a permission-gated action** is not an ACK in chat. It is a file the main session writes under `{project}/memory/tasks/revisions/acks/`, which the re-dispatched agent must verify before it acts. See `runbooks/escalation-protocol.md` (Permission-Gated Action Consent Path).

### Two-Phase QA

**Phase A, per L3.** Before a Coord reports to the PD, it spawns a QA Exec (`general-purpose` plus `/qa-only`) over the combined output of that L3 and writes the result to `{project}/memory/qa/qa-report-l3-{name}-{timestamp}.md`. The L3 has to pass at the bar above before the Coord may report it.

**Phase B, integration.** After every Coord is accepted, the PD spawns an integration tester (`general-purpose` plus `/qa-only`, `/run-acceptance-tests`, `/webapp-testing`) against the contracts in `pd-structure.md`. A score of 85 or higher with no CRITICAL violation passes, 70 to 84 passes with warnings in the digest, and a CRITICAL violation or a score under 60 sends fix Execs and repeats Phase B only.

Deliverables of a QA run:
- Health score (0-100 integer)
- Issues by severity (CRITICAL/HIGH/MEDIUM/LOW)
- Screenshots in `{project}/memory/qa/screenshots/`
- Report at `{project}/memory/qa/qa-report-final-{timestamp}.md` for the final run

---

## Skills Library

The repo ships its full skill library; the catalog is `skills/INDEX.md` and the guide is [SKILLS.md](SKILLS.md).

## Technology

- **Runtime**: Claude Code (Anthropic)
- **Task Store**: SQLite (zero-dependency)
- **Memory**: filesystem (markdown files)
- **Coordination**: NEXUS file protocol
- **Skills**: markdown-based skill definitions

---

## Inter-PD Filesystem Protocol

PDs coordinate via the filesystem, not SendMessage (background agents cannot receive messages).

1. PD-A writes briefing to: `{target-project}/memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md`
2. PD-A creates tracker: `{caller-project}/memory/tasks/ongoing/delegated-{task-id}.md`
3. PD-A spawns PD-B via Agent tool with `run_in_background: true`
4. PD-B completes work, appends completion to caller's `delegated-{task-id}.md`
5. On next `/pd-resume`, PD-A reads completion and marks task done

Use `/pd-spawn` for the full protocol.

---

## PD Boot Sequence (Lazy Loading)

Target: ~500 tokens on spawn.

**On spawn:**
1. Read `{project}/.claude/PD-BRIEFING.md` (pre-built per-project routing doc)
2. Read `{project-root}/memory/heartbeat.md` (log session start)
3. Proceed immediately

**On route (only when delegating):**
1. Check PD-BRIEFING for a pre-written routing entry
2. If not found, load `{agency-root}/agents/{folder}/INDEX.md` (one folder only)
3. Spawn agent directly

See `core/runbooks/pd-boot-sequence.md` for the full protocol.

---

## Status Loop Prohibition

Automated recurring status loops are **disabled by design**. Do not implement periodic status pings.

**Reason:** Naive 15-minute status loops generate 10k–21k reports/week without aggregation, causing token explosion. Instead:
- PDs write to `pd-status-live.md` (append-only)
- The main session reads it **on demand**
- Use `/swarm` for portfolio-wide status checks when needed

---

## Project Scope Management

Each active project can define a `scope.json` at `{project-root}/scope.json`:

```json
{
  "directories": ["src/", "docs/"],
  "financialImportance": "medium",
  "directorId": "{project}-pd"
}
```

**Authority tiers:**

| Tier | Approver | Examples |
|------|----------|----------|
| 1 | Project Director, within `scope.json` | File edits under 10 lines, read-only, docs within project scope |
| 2 | Council chair (parent AI) | New files, code over 10 lines, config changes, dependencies, migrations |
| 3 | Human operator | Deployments, secrets, destructive operations, external comms, financial |

Tier 1 bypass is limited to the scope defined in the project's `scope.json`.

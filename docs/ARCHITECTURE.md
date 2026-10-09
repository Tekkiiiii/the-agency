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
Persistent context across sessions:
- `~/.claude/sessions/{project}/` — session logs
- `~/.claude/projects/{project}/STATE.md` — project state
- `~/.claude/lessons/` — lessons learned
- `~/.claude/decisions/` — architectural decisions

### NEXUS Protocol
File-based handoff system for inter-agent coordination:
- Handoff documents with full context
- Phase 0–5 coordination doctrine
- Quality gates before every handoff

### Skills
Reusable workflow procedures invoked via `/skill-name`:
- Loaded from `~/.claude/skills/`
- Registered in `~/.claude/skills/INDEX.md`
- Can be installed from the agency catalog

### Project Directors (PDs)
Each project has a dedicated PD agent that:
- Owns the project from spec to ship
- Maintains the task pipeline
- Reports to team-lead
- Persists state via memory system

## Data Flow

1. **User** spawns a project or assigns work
2. **PD** creates tasks in task store, hands them to Coords or Execs (workers run as `general-purpose` + 1-3 skills)
3. **Execs** execute, write session logs, gate tasks
4. **PD** monitors pipeline, escalates blockers
5. **On session end**: `/save-state` writes session log
6. **Next session**: agent reads memory, resumes

## Extensibility

The system is designed to be extended:

- **New skills**: drop in `skills/` directory, register in INDEX.md
- **New agents**: add agent spec in `core/agents/` and copy to `~/.claude/agents/{folder}/` — see `docs/DEVELOPER.md`
- **New projects**: run `agency init --project name`
- **Custom coordination**: add rooms in `{agency-root}/agency-rooms/` — see `docs/ROOMS.md`

---

## Tiered Agent Architecture

Work runs as one chain: PD → Coord → Exec. The department layer (lead agents and coordinators) was retired in the 2026-10-08 sunset; the archived files and restore steps are in `{agency-root}/agents-archive/MANIFEST.md`.

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
| L6+ | Mini-Coord | L6 → L7 → L8 → L9... | Exec | Opus |
| Atomic | Exec (general-purpose + Skills) | No | — | Sonnet |

**Critics.** `critique-*` agents and `sag-critique` are spawned directly by the PD or Coord and report to whoever spawned them (the caller). They sit outside any folder hierarchy.

**Agent folders.** `agents/<folder>/` directories (engineering, design, content-creation, testing, project-management, specialized, critiques, video-studio) stay as homes for PD definitions (`project-scaffolder` writes new PDs there). They have no heads and no coordinators.

**Content.** One pipeline: PD → Coord → writer → `/content-polish` → critics via `/cc-loop` (`runbooks/content-request-protocol.md`).

### Naming Convention

- PD = `PD-{slug}` — project-level orchestrator (e.g. `PD-my-saas-app`)
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

1. **Decompose** — break every task into the smallest independent sub-tasks before acting
2. **Parallelize** — spawn one subagent per sub-task simultaneously
3. **Report** — send each completion to team-lead immediately (not at the end)

This protocol applies to every PD spawn, every time, without exception.

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

The Delegator is a stateless Sonnet agent that routes work to the correct agent, skill, pipeline, or protocol. Any agent (PD or Coord) can spawn the Delegator when the right route is not obvious.

Since the generalist switch (2026-10-06) the member-level specialist roles are archived. The Delegator does not pick a specialist agent for them. It returns `general-purpose` plus 1-3 skills, and names the role file to read first. Role files live in `{agency-root}/agents-archive/` (deployed by all four installers), and `agents-archive/ROLE-MAP.md` maps each archived role to its skills. Coords, PDs, critics, council seats, and service agents (curator, codebase-search) stay registered and are still returned by name.

```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Delegator — route: {task-summary}",
  prompt: "Read ~/.agency/agents/specialized/delegator.md fully.\n\nRouting question: {task}\nCaller: {your name}"
})
```

The Delegator:
- Reads the agency catalog, org chart, and skill index
- Returns a structured routing recommendation (AGENT | SKILL | PIPELINE | PROTOCOL | INTER-SPAWN)
- Dies immediately after returning the recommendation — it holds no state

**Routing exceptions** — spawn Delegator is NOT required when:
- The correct agent or skill is already known (e.g. `general-purpose` + `/frontend` for a UI task)
- The task is a curator spawn (memory retrieval — always fire-and-forget)

Definition: `agents/specialized/delegator.md`

---

## Agency Council

An advisory board of five seats: `council-fable`, `council-opus`, `council-sonnet`, `council-haiku` (one per Claude model tier, in `agents/council/`) plus an optional fifth seat run through the `codex` CLI when it is installed. Seats are read-only and answer in at most 300 words (`VERDICT`, `REASONS`, `RISKS`, `CONFIDENCE`, `DISSENT`).

The caller sends one identical brief to every seat in a single message (one wave, no `TeamCreate`); no seat sees another's answer. The caller synthesises a table of verdicts, agreements, disagreements, and a recommendation. Three of five seats is a quorum, and `council-opus` breaks a tie when the caller is a cheap model. Triggers: "BOD", "assemble", "the board", "the council", "convene the council"; `/resume-bod` restores context and then runs it. Protocol: `core/memory/agency-council.md`.

---

## Quality Gates (ACK/NACK Protocol)

Every agent-to-agent handoff has a mandatory QA gate before approval:

| Handoff | Reporter | Reviewer | ACK condition | NACK condition |
|---------|----------|----------|---------------|----------------|
| Exec → Coord | Exec sends DONE + QA | Coord reviews QA report | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| Coord → PD | Coord sends L3 complete + QA | PD reviews Coord QA report | Health ≥ 70, no CRITICAL | Health < 70 OR CRITICAL/HIGH present |
| PD → root | PD sends final digest + QA | root (operator) | Explicit ACK | Explicit NACK with fix list |

Reports are asynchronous: an agent's report lands when the agent stops, and the agent is gone by then.

**ACK** = the reviewer accepts the report and does not re-spawn the agent. Nothing more is needed.
**NACK** = the reviewer spawns a fresh continuation agent with the fix list → it fixes → re-runs the QA gate → re-reports

**Consent for a permission-gated action** is not an ACK in chat. It is a file the main session writes under `{project}/memory/tasks/revisions/acks/`, which the re-dispatched agent must verify before it acts. See `runbooks/escalation-protocol.md` (Permission-Gated Action Consent Path).

### PD-Level Pre-Aggregate QA Gate

After all Coords report DONE, PD spawns `Coord-qa-Canary` (Sonnet, QA Coord) to QA the combined L3 output before reporting to root.

Deliverables:
- Health score (0–100 integer)
- Issues by severity (CRITICAL/HIGH/MEDIUM/LOW)
- Screenshots in `{project}/memory/qa/screenshots/`
- Report at `{project}/memory/qa/qa-report-final-{timestamp}.md`

---

## Skills Library

The repo ships its full skill library (the catalog is `skills/INDEX.md`). The core lifecycle skills:

| Category | Skills |
|----------|--------|
| Memory | `save-state`, `recall`, `pd-resume`, `project-status`, `wrap` |
| Coordination | `swarm`, `delegate`, `nexus-gatekeeper` |
| Ops | `self-healing`, `investigate`, `guard`, `task-store` |
| Planning | `autoplan`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `office-hours`, `retro` |
| Execution | `ship`, `land-and-deploy`, `setup-deploy`, `canary`, `qa` |
| Quality | `design-review`, `codex`, `cso`, `qa-only`, `document-release` |
| Engineering | `backend`, `frontend`, `tech-writer`, `github-deploy`, `vercel-deploy`, `railway-deploy`, `supabase-deploy` |

## Technology

- **Runtime**: Claude Code (Anthropic)
- **Task Store**: SQLite (zero-dependency)
- **Memory**: filesystem (markdown files)
- **Coordination**: NEXUS file protocol + Agency Rooms
- **Skills**: markdown-based skill definitions

---

## Agency Rooms

File-based inter-agent chat system for persistent coordination between agents.

```
{agency-root}/agency-rooms/{room}/
├── messages.mdl        # Append-only message log
├── room.json           # Room metadata and member list
├── members.json        # Active members
├── handoffs/           # Pending NEXUS handoffs (JSON)
└── context/
    └── shared.md       # Shared summary, maintained by hand
```

Room types:
- **Project rooms** — one per active project, owned by the project's PD
- **Oversight room** — `project-oversight/` aggregates all PD statuses

Rooms are plain files written by `agents/scripts/room-utils.sh`; there is no polling process (the `room-manager` skill was archived in the 2026-10-08 sunset). Read rooms on demand. See `docs/ROOMS.md`.

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
  "departments": ["engineering", "testing"],
  "financialImportance": "medium",
  "directorId": "{project}-pd"
}
```

**Authority tiers:**
| Tier | Scope | Approver |
|------|-------|----------|
| 1 | <10 line edits, read-only, docs | PD (self-approve) |
| 2 | Code >10 lines, new files | Parent AI |
| 3 | Deploy, secrets, destructive | Human operator |

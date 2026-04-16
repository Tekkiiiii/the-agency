# Plan: Tiered PD-Coord Architecture

## Context

User wants a tiered task decomposition model:
- PD (top-level): receives work, breaks into L3 chunks, spawns Coords, collects final reports
- Coord (mid-level, autonomous): owns one L3 chunk, breaks to smallest, spawns executors, manages to completion, reports back, despawns
- Task-Executor (leaf): actual implementation, reports to direct spawner

This replaces the flat single-layer model.

---

## Scope: All PDs, No Exceptions

This architecture applies to **every Project Director** — existing and future.

**Existing PDs** (must be updated):
- `marketsenseapp-pd` → adopts `pd-coordinator.md` behavior
- `amanicrm-pd` → adopts `pd-coordinator.md` behavior
- `ltv-pd` → adopts `pd-coordinator.md` behavior
- `website-pitch-pd` → adopts `pd-coordinator.md` behavior
- `research-pd` → adopts `pd-coordinator.md` behavior

When any existing PD is invoked via `/pd-resume` or `/swarm`, it uses the new architecture.
Existing project state files (`memory/`, `next-session.md`, etc.) are preserved — only the PD's
behavior changes, not the project's data.

**Future PDs**: must follow this architecture by default. New PD spawns use `pd-coordinator.md`
as their agent template. No ad-hoc spawning outside this structure.

**One exception to the rule**: `/swarm` status-only queries (no work assigned) do not trigger
Coord/Executor spawning — just the PD status response.

---

## Architecture

```
PD  (L1→L2→L3, then spawns Coords)
 └── Coord × N  (L3→L4→...→smallest, then spawns Executors, autonomous — despawns when L3 done)
      └── Task-Executor × M  (executes what Coord gives, no decomposition, reports to Coord)
```

| Agent | Decomposes | Implements |
|-------|-----------|------------|
| PD | L1 → L2 → L3 | No |
| Coord | L3 → L4 → ... → smallest | No |
| Task-Executor | No | Yes (exactly what Coord assigns) |

**Reporting chain: executor → direct spawner only.**
- Coord-spawned Executor → reports to Coord
- Coord → reports to PD (final L3 completion)

---

## Default Permissions

| Agent | Default permissions |
|-------|--------------------|
| Task-Executor | Read + write on all files, folders, and resources within its assigned sub-task scope |
| Coord | Read + write on all resources within its L3 task scope |
| PD | Read + write on all resources within the project |

**Outside-scope actions require escalation.** If an action would affect resources or scope beyond what was assigned, always escalate — do not act without approval.

---

## Agent Definitions

### PD (spawned by pd-resume / swarm) — **Opus model, approval permission**

Role: Top-level orchestrator. Decomposes to L3, hands off to Coord, aggregates final reports.

Authority: Decomposes L1 → L2 → L3. Hands off at L3 to Coord. Never decomposes past L3.

Lifecycle:
1. Decompose incoming work to L3 chunks
2. Spawn one Coord per L3 chunk
3. Wait for all Coord completion reports (incoming as conversation turns)
4. Aggregate results and send final digest to team-lead
5. Run `/save-state [{slug}]`
6. Stop

Constraints:
- PD does NOT decompose below L3. That authority belongs to Coord.
- PD does NOT do implementation.
- Has approval permission within project scope.
- Does NOT have approval permission for tasks delegated from other PDs — escalate to Tekki.

### Coord (spawned by PD, one per L3 task) — **Opus model, approval permission**

Role: Autonomous work owner. Receives one L3 task, owns it fully until done.

Authority: Decomposes L3 → L4 → L5 → ... → smallest implementation unit.
Coord is the **only agent with decomposition authority** below L3.

Lifecycle:
1. Decompose L3 all the way down to the smallest implementable unit (file, function, component)
2. Group smallest units into batches — one Task-Executor per batch
3. Spawn all Task-Executors in parallel
4. Wait for all executor reports (incoming as conversation turns)
5. Send final L3 completion report to PD via SendMessage
6. `/save-state [{slug}]`
7. Despawn

Constraints:
- Coord has full decomposition authority from L3 to smallest. No other agent decomposes below L3.
- Max depth: PD → Coord → Executor. Coord does NOT spawn other Coords.
- Coord has Opus model and approval permission within its L3 scope.
- Executor receives exactly what to do — Executor does NOT decompose.

### Task-Executor (spawned by PD or Coord) — **Sonnet model, no approval permission**

Role: One-shot implementation unit. Receives exactly one smallest task from Coord, executes it, reports to direct spawner, stops. **No decomposition authority.**

Lifecycle:
1. Execute the task exactly as given by Coord (read + write on all scoped resources — default permission)
2. If action requires scope beyond the assigned task → ESCALATE, do not act
3. Send DONE, BLOCKED, or ESCALATE to **direct spawner** via SendMessage:
   - PD-spawned Executor → reports to PD
   - Coord-spawned Executor → reports to Coord
4. Stop

Constraints:
- Sonnet model. No approval permission. No decomposition authority.
- Default: read + write on all resources within the assigned task scope.
- If blocked by scope or needing directions, reports BLOCKED to spawner — do not attempt to decompose or escalate scope beyond what was assigned.
- Findings and lessons learned are saved at the appropriate scope:
  - Atomic (agent) level: sub-task specific, written to project memory / task log
  - Dept level: if finding affects a department's way of working → escalate to dept head
  - Project level: if finding affects project direction or decisions → escalate to PD
- If a domain specialist agent (e.g. a ui-ux-agent running as Sonnet) is called and needs directions, it asks its **dept head**, not Coord.

---

## Decomposition Levels

| Level | Who decomposes | Who implements | Model | Description |
|-------|---------------|---------------|-------|-------------|
| L1 | PD | — | Opus | Large feature or epic — "build the news feed" |
| L2 | PD | — | Opus | Major components — "auth", "feed UI", "RSS parser" |
| L3 | PD breaks to L3, hands to Coord | — | Opus | Independently deliverable unit — "auth", "feed UI", "RSS parser" |
| L4+ | Coord decomposes | Coord manages | Opus | Coord owns decomposition from L4+ all the way to smallest |
| Smallest | — | **Executor** executes what Coord gives it | Sonnet | No decomposition authority — Coord tells Executor exactly what to do |

**PD authority: L1 → L3.** PD decomposes to L3 and hands off. Never goes past L3.
**Coord authority: L3 → smallest.** Coord receives at L3, decomposes all the way down to the implementation unit, spawns Executors to execute.
**Executor: zero decomposition authority.** Receives a single smallest unit from Coord and executes it. Reports back only.

**Max spawn depth: PD → Coord → Executor.**

---

## Context Budget

Each layer only accumulates its own scope:

| Layer | Decomposes | Context grows with |
|-------|-----------|-------------------|
| PD | L1 → L2 → L3 | Coord completion tags + final aggregation |
| Coord | L3 → L4 → ... → smallest | Executor completion tags + L3 management. Clears after L3 done. |
| Task-Executor | Zero (no authority) | Its own implementation work. Clears after despawn. |

Findings and lessons are routed to the right scope level, not held in agent context.

---

## Finding / Lesson Routing

When an agent surfaces a finding or lesson:

```
Does it change how THIS sub-task was done?
  → Save at agent (atomic) level — project memory / task log

Does it change how a DEPARTMENT works?
  → Escalate to dept head

Does it change the PROJECT's direction or decisions?
  → Escalate to PD
```

Domain specialist agents (e.g. ui-ux-agent on Sonnet) route questions to their
dept head, not to Coord or PD.

---

## Escalation Protocol — Permission Failures

**Rule: Never retry a permission failure. Always escalate.**

If a task fails because something needs approval (deploy, delete, write outside scope, cost, destructive action, etc.):

1. Report the failure up the chain with the specific permission needed
2. Wait for approval before continuing
3. Do NOT retry, do NOT skip, do NOT stop

### Escalation Path

```
Task-Executor (Sonnet, no approval)
 └── ESCALATE → Coord (Opus, approval at L3 scope)
      └── If Coord lacks scope → ESCALATE → PD (Opus, approval at project scope)
           └── If PD lacks scope → ESCALATE → Parent Session (can approve within project scope)
                └── If parent session also lacks scope → ESCALATE → Tekki (ultimate approver)
```

**Parent session approval scope:** anything within the project's scope that exceeds PD's authority.
**Tekki scope:** cross-project decisions, cost, irreversible actions, strategic choices.

### Escalation Message Format

When escalating, always include:
```
[{subtask-label}]: ESCALATE — failed due to no {permission type} permission
Needed: {specific action that needs approval}
Scope: {what scope the action would affect}
Awaiting: {who needs to approve}
```

### Escalation Examples

- Executor: "login-ui: ESCALATE — failed due to no Railway env write permission. Needed: set OLLAMA_HOST. Scope: Railway production. Awaiting: Coord"
- Coord: "Coord-auth-L3: ESCALATE — PD-level approval needed to delete legacy users table. Awaiting: PD"
- PD: "PD-MarketSense: ESCALATE — cost approval needed for Neon branch create ($0.50/day). Scope: project. Awaiting: parent session"
- PD: "PD-MarketSense: ESCALATE — irreversible action: delete all test DBs across 3 projects. Scope: multi-project. Awaiting: Tekki"

### On Approval

Once approved at a level, approval flows back down to the originally escalating agent:
- Parent session approves → notifies PD → PD continues or re-delegates with approved scope
- PD approves → notifies Coord → Coord continues or re-delegates
- Coord approves → notifies Executor → Executor continues

The originally escalating agent does NOT retry on its own — approval must flow back from the approving level before continuation.

---

## Session Context & State Management

### When parent session calls `/save-state`

Calling `/save-state` in the parent session **does not stop subagents.** Agents are independent — they hold their own contexts and continue running in the background after the parent session resets.

Flow when parent session calls `/save-state` mid-execution:

```
Parent session calls /save-state
 └── Parent context resets
      ├── PD continues: waiting for Coord completion reports
      ├── Coords continue: decomposing L3, spawning Executors, waiting for executor reports
      ├── Executors continue: executing tasks
      └── All agents continue until their task is done
```

When each agent finishes, its message arrives as a new conversation turn in the parent session. The parent session accumulates only completion tags (not full agent context) — so context grows slowly even with many agents reporting back.

### Persistence model

Each agent writes its own state on completion:

| Agent | When it saves | What it saves |
|-------|--------------|---------------|
| Task-Executor | After DONE/BLOCKED | Task result, lessons, any findings |
| Coord | After L3 complete | L3 completion summary, executor results, lessons |
| PD | After all L3s done | Final digest, updated heartbeat, decisions, next-session.md |

If parent session resets mid-execution, the project state is already persisted per-Coord. The next `/recall` reads this per-L3 state.

### Context window health

If parent session context grows too large during execution:

1. **Don't wait** — agents continue running independently
2. Check `memory/heartbeat.md` to see live status without consuming context
3. On next natural pause, call `/save-state` to reset
4. New conversation turn picks up agent completion messages as they arrive

**Key invariant:** no agent depends on the parent session's context to continue. Parent session context only accumulates agent completion messages — not their internal work.

### Invoking a new PD while one is mid-flight

If Tekki calls `/pd-resume [slug]` or gives new work to the project while existing Coords and Executors are still running:

```
Existing agents (continue independently):
 └── Coords: running, waiting for executor reports → will complete their L3
 └── Executors: running → will complete, report to their Coord

New PD spawns:
 └── Reads /save-state state → sees which L3s are already done
 └── Sees which L3s are in-flight (running Coords)
 └── Does NOT re-spawn completed or in-flight Coords
 └── Only spawns Coords for L3s that are not yet started
```

**New PD is additive, not destructive.** It reads what is done, sees what is running, and fills the gaps. Existing Coords continue uninterrupted — they are not killed by a new PD spawn.

If Tekki wants to override or cancel mid-flight work:
- Write a directive in `memory/next-session.md` before invoking the new PD
- e.g. "cancel Coord-auth-L3 — auth approach changed, restart required"
- New PD reads this and does not resume the cancelled Coord

### Stopping mid-flight agents

Currently no hard kill mechanism. To stop agents mid-flight:
1. Write a stop directive to `memory/heartbeat.md`
2. Agents can be instructed to check this file on their next turn and stop if directive is present
3. Alternatively, document the stop in `next-session.md` and let the current session finish naturally

*(Hard stop via signal is out of scope for this version — agents are designed to complete their current task and stop naturally.)*

### Visibility without consuming context

While agents run, Tekki can read these files without touching context:
- `memory/heartbeat.md` — PD writes progress tags here as Coords complete
- `memory/decisions.md` — decisions locked during execution
- `memory/next-session.md` — what remains open if session was cut

This gives Tekki a live project view at any time without consuming context.

---

## Agent Naming Convention

Agents get punny, task-appropriate names. Names are memorable, scannable in logs, and give Tekki instant context without reading the full brief.

### Naming Pattern

```
Coord: Coord-{l3-name}-{pun}
        e.g. Coord-auth-Gatekeeper
              Coord-feed-Digest
              Coord-rss-Spinner

Executor: Exec-{subtask}-{pun}
        e.g. Exec-login-Keymaster
              Exec-schema-TombRaider
              Exec-ui-PixelPusher
```

### Guidelines

- **Match the domain**: auth → Gatekeeper/Warden/LockSmith; feed → Spinner/Digest; DB → Architect/TombRaider; UI → PixelPusher/Canvas; deploy → Pilot/Captain
- **Keep it short**: 2-3 words max
- **Unique per task**: no two active agents share the same name in the same project
- **PD assigns the name**: the spawner (PD or Coord) picks the punny name when spawning

### Examples by Domain

| Domain | Name ideas |
|--------|-----------|
| Auth | Gatekeeper, LockSmith, Warden, Bouncer |
| Feed/UI | Spinner, Digest, Flowmaster |
| DB/Migration | TombRaider, Architect, RelicHunter |
| Deploy/DevOps | Pilot, Captain, Launchpad |
| API | BridgeBuilder, Router |
| File/IO | Conductor, Pipeline |
| Testing | Prober, Scout |
| Config | Tuner, Dialer |

### Reporting with names

When reporting to team-lead or spawning, always use the punny name:

```
Gatekeeper: DONE — auth endpoint written and tested
Coord-auth-Gatekeeper: L3 COMPLETE — 5/5 executors done, login/register/logout all deployed
PD-MarketSense: All L3s done. Digest: [Coord-feed-Digest: done, Coord-auth-Gatekeeper: done, ...]
```

Names travel with the agent throughout its lifecycle. PD scratch file, scratch file paths, and all reports use the same punny name.

---

## Short-Term Memory (Scratch Board)

Every agent has a personal scratch file — a working board where they dump everything they're actively doing. Session-scoped, lightweight.

### File Location & Naming

```
{project}/memory/agents/
 ├── pd-scratch.md                    # PD scratch — persists across sessions
 ├── coords/
 │   └── coord-{l3-name}-scratch.md # One per Coord (e.g. coord-auth-L3-scratch.md)
 └── executors/
     └── exec-{id}-scratch.md        # One per Task-Executor
```

### Structure (identical for every agent)

```markdown
# {agent-name} Scratch — {project} — {timestamp}

## Current Tasks
- [ ] task A
- [ ] task B

## task A
Started: {timestamp}
Working on: ...
Next step: ...
Blockers: ...
```

### Format Rules

- **Task block**: `## {task-label}` with timestamp, current work, next step, blockers
- **Current Tasks**: checklist at top — `[ ]` = in progress, nothing = done
- **Blockers**: noted in the block, escalated immediately
- **Notes**: any discovery or decision goes here — not held in context

### Lifecycle & Archive Policy

| Agent | On completion |
|-------|--------------|
| Task-Executor | Delete scratch file entirely. Scratch was per-task, no history needed. |
| Coord | Delete scratch file entirely. Scratch was per-L3, no history needed — all important outcomes reported to PD. |
| PD | Archive done blocks to `memory/pd-history.md`, keep scratch lean for next session. PD scratch persists. |

### PD History File (`memory/pd-history.md`)

```markdown
# PD History — {project}

## {date} Session

### Done
- task A — completed, result: ...
- task B — completed, result: ...

### Decisions made
- ...

### Open items
- task C — carried to next session
```

### Scratch is Lean by Design

- Executor/Coord scratch: deleted on completion — zero maintenance
- PD scratch: max ~10 active blocks; done blocks archived to pd-history.md
- If PD scratch would exceed ~50 lines, archive completed blocks first before continuing

### What Goes in Scratch vs Context vs Project Memory

| What | Scratch | Agent Context | Project Memory |
|------|---------|--------------|---------------|
| Current work in progress | ✓ | — | — |
| Next step decision | ✓ | — | — |
| Task blockers | ✓ | — | — |
| Findings | scratch → pd-history.md on archive | — | ✓ |
| Locked decisions | — | — | ✓ |
| Completion results | scratch → pd-history.md on archive | — | ✓ |

---

## Files to Create

```
~/.claude/agents/project-management/pd-coordinator.md   # PD spawn prompt (Opus, approval permission)
~/.claude/agents/project-management/coord.md           # Coord spawn prompt (Opus, approval permission)
~/.claude/agents/specialized/task-executor.md          # Task-Executor spawn prompt (Sonnet, no approval)
```

## Files to Update

```
~/.claude/skills/pd-resume/SKILL.md    # Step 4: spawn pd-coordinator.md
~/.claude/skills/swarm/SKILL.md        # Same
~/.claude/agents/project-management/INDEX.md  # Register pd-coordinator + coord agents
~/.claude/agents/specialized/INDEX.md   # Register task-executor agent
```

---

## Implementation Steps

### Step 1 — Create `pd-coordinator.md`
PD spawn prompt. Authority: L1 → L2 → L3 decomposition, then spawns one Coord per L3 task.
Collects Coord completion reports, aggregates, sends digest to team-lead, `/save-state`, stops.
Opus model. Approval permission within project scope.

### Step 2 — Create `coord.md`
Coord spawn prompt. Authority: L3 → L4 → ... → smallest decomposition.
Receives one L3 task, decomposes to smallest, groups into executor batches, spawns all
Task-Executors in parallel, waits for reports, sends L3 completion to PD, `/save-state`, despawns.
Opus model. Approval permission within L3 scope.

### Step 3 — Create `task-executor.md`
Executor spawn prompt. Zero decomposition authority. Receives exactly one smallest task
from Coord, executes it, sends DONE/BLOCKED/ESCALATE to direct spawner, stops.
Sonnet model. No approval permission.

### Step 4 — Update `pd-resume/SKILL.md` Step 4
Replace current PD spawn prompt with spawn of `pd-coordinator.md` agent.
Include project name, recall briefing, and agent template path.

### Step 5 — Update `swarm/SKILL.md`
Same change for PD dispatch.

### Step 6 — Register in department INDEX files
Add `pd-coordinator` and `coord` to `project-management/INDEX.md`.
Add `task-executor` to `specialized/INDEX.md`.

### Step 7 — Verify
Run `/pd-resume [one project]`. Confirm:
- PD decomposes to L3 chunks only
- One Coord spawned per L3 task
- Each Coord decomposes L3 all the way to smallest, spawns Task-Executors in parallel
- Executors execute exactly what Coord gave them — no decomposition
- Executors report DONE/BLOCKED/ESCALATE to Coord
- Coords report L3 completion to PD
- PD aggregates and sends final digest to team-lead
- Coord runs `/save-state` then despawns
- PD runs `/save-state` then stops

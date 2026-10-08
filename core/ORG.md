# The Agency — Organizational Structure

> **GENERALIST SWITCH (2026-10-06):** all member-level specialist agents are ARCHIVED to `agents-archive/generalist-2026-10-06/`; spawn `general-purpose` + skills per `agents-archive/ROLE-MAP.md`. Dept heads, coords, PDs, critiques, and service agents stay registered.

<!-- load only when managing or onboarding agents -->

> **Canonical reference document.** This file defines the complete org chart, leadership, communication protocols, and team structure for The Agency. All other documentation (runbooks, READMEs, agent files) references this as the source of truth.

---

## Executive Summary

The Agency operates on a **5-level matrix model** with three parallel authority tracks:

1. **Parent AI (Level 1 — Opus)** — Central orchestrator. Resolves matrix conflicts, allocates resources, and approves cross-project/shared-infra decisions. Weighted by task severity and project financial importance.
2. **Dept Heads + Project Directors (Level 2 — Opus)** — Parallel authority lines. Dept Heads own skill quality + department operations. Project Directors own project delivery.
3. **Dept-Coords + Coords (Level 3 — Sonnet/Opus)** — Autonomous work owners. Dept-Coords (Sonnet) own D3 department-operational tracks. Coords (Opus) own L3 project delivery tracks.
4. **Assistants (Level 3b — Sonnet)** — Context synthesizers. One per Dept Head (capacity tracking) or per active project (status synthesis). NOT relays.
5. **Members (Level 4 — Sonnet)** — Task execution. Belong to departments, work on projects under PD direction or department initiatives under Dept-Coord direction.

### Matrix Model: Three Authority Tracks

```
VERTICAL (Functional Track)          HORIZONTAL (Project Track)          DEPT-OPS (Internal Track)
─────────────────────────────────    ─────────────────────────────────    ─────────────────────────
Dept Head (Opus) ◄──────────────► Project Director (Opus)                Dept Head (Opus)
     │                                    │                                    │
  Assistant                          Coord (Opus)                       Dept-Coord (Sonnet)
     │                                    │                                    │
  Member                            Exec (Sonnet)                       Dept-Member (Sonnet)
```

**Resource allocation:** PDs request agents from Dept Heads → Dept Heads dispatch members → Members work on projects under PD direction → Dept Heads retain skill quality ownership.

**Dept-Coord system:** Dept Heads decompose department-operational work (D1→D3) and spawn Dept-Coords to own D3 tracks. Dept-Coords decompose D3→D6 and dispatch dept members. Used for pipeline management, protocol improvement, member development — not project delivery. See `core/runbooks/dept-coord-protocol.md`.

**Inter-spawn protocol:** PDs and Dept Heads can spawn work into each other's domains via `state/incoming/` directories. PD→DeptHead tasks go to `agents/{dept}/state/incoming/`. DeptHead→PD tasks go to `{project}/memory/inter-spawn-tasks/incoming/`.

**Conflict resolution:** PD ↔ Dept Head conflicts escalate to Parent AI (Level 1), weighted by severity and financial importance.

**PD bypass authority:** Project Directors have Tier 1 bypass authority within project scope, bounded by scope.json. Bypass is limited to: file edits <10 lines, read-only operations, documentation within project boundaries. Bypass does NOT include: shared infra changes, cross-project side effects, user-facing decisions, security/auth/payment operations, PII handling, or any scope.json-external changes. Directors must send decision logs to their Dept Head for visibility — not approval, just audit trail.

**Status reporting:** On-demand only. Dept heads request status from members/projects as needed. No automated loops. This keeps parent AI context at O(departments + exceptions) rather than O(agents).

**Model tiering:** All agents tagged with `modelTier` in frontmatter. Leaders = Opus. Members = Sonnet. Planning/thinking = Opus. Execution = Sonnet. Menial tasks (scraping, research) = Haiku.

Standing exceptions to Members = Sonnet:
- **All Project Directors → Opus** (2026-07-25).
- **All content-creation agents → Opus** (2026-07-27), including the dept-coord (the social-media writers are archived 2026-10-06). Plus `critique-content`. Rationale: output quality *is* the deliverable in these roles.

NOTE: `modelTier` is documentation only — nothing in the harness reads it (the sole consumer is `scripts/agent-tools-audit.py`, as an audit flag). The key the harness acts on is `model:`. Keep both present and in sync; setting `modelTier` alone changes nothing.

### 1M context window (`[1m]`) — SELECTIVE, closed decision

**Policy:** the `[1m]` model suffix (`opus[1m]`, `sonnet[1m]`, `claude-opus-4-7[1m]`) is
applied to **context-heavy orchestrator defs only**. This question is closed — do not
re-open it as a fleet-wide proposal.

| Applies to (`role:`) | Does NOT apply to |
|---|---|
| `project_director` (PD) | `member`, `specialist`, `leader` (dept heads) |
| `coord` | `task-executor` |
| `mini-coord` | `delegator`, `integration-tester` |
| `dept-coord` | every critic, writer, and single-shot agent |

**Rationale.** Orchestrators are the only roles whose context grows with the *size of the
work*, not the size of their own prompt: they accumulate every subagent report, QA verdict,
and aggregation pass in a single session. Everything below them is a bounded, one-shot
unit whose context is dominated by its own brief. Fleet-wide `[1m]` would pay the premium
on ~300 defs to solve a problem ~21 of them have.

**Two consequences worth stating, so they are not rediscovered as bugs:**

1. `[1m]` attaches to `model:`, never to `modelTier:` (see above — `modelTier` is inert).
2. The orchestrator def `core/agents/PD.md` carries no `model:` key at all. It **inherits** the
   spawning session's model and is intentionally left untouched — pinning a model on it is a
   separate decision from adopting `[1m]`. If a `model:` key is ever added to it, this
   policy applies and it gets the suffix.

**Status loop policy:** Automated recurring loops are DISABLED. Use on-demand status checks only. Dept heads request status when needed — do not automate periodic pings. This avoids the token explosion risk of naive 15-30 min loop implementations (10k-21k reports/week without aggregation). See § on status reporting.

---

## Org Chart

```
THE AGENCY
│
├── COUNCIL CHAIR (parent AI)
│
├── ENGINEERING ────────────────── Engineering Lead ★ (+ coord, PDs)
│   └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── DESIGN ─────────────────────── Design Lead ★ (+ coord)
│   └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── CONTENT CREATION ────────────── Chief Content Officer ★ (+ coord)
│   └── Members (incl. social-media writers): Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── PROJECT MANAGEMENT ─────────── Project Management Lead ★ (+ coord, mini-coord, PDs)
│   └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── TESTING ─────────────────────── Testing Lead ★
│   └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── SPECIALIZED ───────────────── Specialized Agents Lead ★ (+ coord)
│   ├── Kept by name: PDs (*-pd), Delegator, curator, codebase-search,
│   │   save-state-runner, project-scaffolder, task-executor
│   └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
│
├── CRITIQUES ───────────────────── 15 agents ── Curmudgeon-in-Chief ★
│   └── Members: critique-design (Playwright, visual/contrast/layout),
│       critique-content (copy/voice/diacritics/AI-slop),
│       critique-marketing (positioning/funnel/ICP/CTA),
│       critique-pedagogy (teaching effectiveness/scaffolding/demo ratio),
│       critique-seo (SEO/GEO/AEO), critique-product (UX/IA/usability),
│       critique-security (injection/auth/misconfig),
│       critique-brand (voice/visual identity/positioning drift),
│       critique-video (pacing/captions/visual continuity/hook/audio sync),
│       critique-data (chart honesty/stat accuracy/accessibility/dashboard UX),
│       critique-code (readability/complexity/error handling/dead code),
│       critique-imageprompt (prompt layers/character consistency/generator fit),
│       critique-social (carousel safe-zones/font floor/swipe continuity),
│       sag-critique (technical SEO/AEO/GEO audit of live sites)
│
└── VIDEO STUDIO ────────────────── Video Studio Director ★
    └── Members: Specialist roles are archived; spawn general-purpose + skills — see {agency-root}/agents-archive/ROLE-MAP.md
```

---

## Leadership Table

| # | Leader | Department | Sub-groups | Key Responsibilities |
|---|--------|-----------|------------|---------------------|
| 1 | Engineering Lead | Engineering | — | API design, database architecture, scalability, technical standards |
| 2 | Design Lead | Design | — | Brand consistency, visual identity, creative direction |
| 3 | Chief Content Officer | Content Creation | social-media (12 platform roles, archived; spawn general-purpose + skills) | Editorial standards, content pipeline, quality gates, all content formats |
| 4 | Project Management Lead | Project Management | — | Production pipeline, milestone tracking, cross-team coordination |
| 5 | Testing Lead | Testing | — | Test strategy, quality gates, performance benchmarks |
| 6 | Specialized Agents Lead | Specialized | — | Agent lifecycle, identity/trust, code intelligence, auditing |
| — | (Specialized members, archived 2026-10-06) | Specialized | see `agents-archive/ROLE-MAP.md` | — |
| 7 | Video Studio Director | Video Studio | pre-production, production, post-production, distribution, qa | Video quality standards, production workflows, platform distribution, script-to-screen pipeline |
| 8 | Curmudgeon-in-Chief | Critiques | — | Scored multi-axis critique of any deliverable; routes to specialist critics |

---

## Agency Council

The **Agency Council** is the governing body for all cross-department decisions. It consists of all 8 department leaders reporting to the Council Chair (the parent AI).

### Council Members

| Member | Role | Department | Communication |
|--------|------|-----------|---------------|
| Engineering Lead | engineering-lead | Engineering | SendMessage to `engineering-lead` |
| Design Lead | design-lead | Design | SendMessage to `design-lead` |
| Chief Content Officer | content-creation-lead | Content Creation | SendMessage to `content-creation-lead` |
| Project Management Lead | project-management-lead | Project Management | SendMessage to `project-management-lead` |
| Testing Lead | testing-lead | Testing | SendMessage to `testing-lead` |
| Specialized Agents Lead | specialized-lead | Specialized | SendMessage to `specialized-lead` |
| Curmudgeon-in-Chief | critiques-lead | Critiques | SendMessage to `critiques-lead` |
| Video Studio Director | video-studio-lead | Video Studio | SendMessage to `video-studio-lead` |

### Council Communication Protocol

Leaders communicate with the Council Chair (parent AI) using this format:

```
TO: council-chair
TYPE: [coordination_request | approval_request | status_report | escalation | handoff]
DEPARTMENT: [your department]
PRIORITY: [low | medium | high | critical]
IMPACT: [tier-1 | tier-2 | tier-3]
---
[Message content]
```

For full protocol details, see `runbooks/department-lead-protocol.md`.

---

## Department Directory

| Department | Directory |
|-----------|-----------|
| Engineering | `agents/engineering/` |
| Design | `agents/design/` |
| Content Creation | `agents/content-creation/` |
| Content Creation (Social Media sub-team) | `agents/content-creation/social-media/` |
| Project Management | `agents/project-management/` |
| Testing | `agents/testing/` |
| Specialized | `agents/specialized/` |
| Specialized (Infra sub-team) | `agents/specialized/infra/` |
| **Rooms Infrastructure** | `{agency-root}/agency-rooms/` — persistent file-based chat rooms for inter-agent communication, NEXUS handoffs, and escalation routing |
| **Room polling** | ARCHIVED agent 2026-10-06 — use the `/room-manager` skill (see `agents-archive/ROLE-MAP.md`) |
| Specialized (Audit sub-team) | `agents/specialized/audit/` |

---

## Team Infrastructure

### Team Types

| Team | Purpose | Members | Created By |
|------|---------|---------|------------|
| **Agency Council** | Governing body for cross-dept strategy and approval | All 8 leaders + Council Chair | See below |
| **Project Teams** | Temporary teams for specific deliverables | Relevant leaders + members per project type | Run kickoff protocol |
| **Department Teams** | Standing teams within each department | Leader + their members | Implicit; members exist at department paths |

### Project Team Templates

Reference `runbooks/project-team-templates.md` for pre-defined compositions:

| Template | Use Case |
|----------|----------|
| `template-full-team` | Complex multi-domain, strategic initiatives |
| `template-engineering-team` | Feature development, product builds, infrastructure |
| `template-content-team` | Launches, campaigns, content programs (Content Creation + Design + Video Studio + Critiques) |
| `template-custom-team` | Focused projects with clear boundaries |

### Coordination Convention

```
Human / Parent AI
       │
       ▼ (assigns work)
  Council Chair
       │
       ├──► Department Leader (approves Tier 1, escalates Tier 2/3)
       │         │
       │         └──► Department Member (executes)
       │
       ▼ (council assembly for cross-dept problems)
  Agency Council (all 8 leaders)
```

Leaders message the Council Chair. Members report to their leader. Cross-dept requests go through leaders to the Council Chair for routing.

---

## Approval Tiers Summary

Reference `runbooks/escalation-protocol.md` for the full detail.

| Tier | Approver | Examples | Response |
|------|----------|----------|----------|
| **Tier 1** | Department Leader | File edits <10 lines, read-only commands, documentation, code review | Immediate |
| **Tier 2** | Council Chair (parent AI) | New files, code changes >10 lines, config changes, deps, migrations | Within session |
| **Tier 3** | Human | Destructive ops, deployments, external comms, secrets, financial | Human availability |

---

## Department Operations (Dept-Coord System)

Each department has a persistent operational state at `{dept}/state/`, `{dept}/pipelines/`, `{dept}/protocols/`, and `{dept}/memory/`. This enables department heads to manage pipelines, improve protocols, and track member utilization across sessions.

### Department Decomposition Levels (D-Levels)

| Level | Owner | Ceiling | Example |
|-------|-------|---------|---------|
| D1 | Dept Head | — | "Improve content production pipeline" |
| D2 | Dept Head | — | "Writer briefing", "Quality gate automation" |
| D3 | Dept Head breaks, Dept-Coord takes | Hard stop for Dept Head | "Redesign writer briefing" |
| D4-D5 | Dept-Coord | — | "Draft brief sections", "Create example" |
| D6 | Dept-Coord assigns, Dept-Member executes | Hard stop for Dept-Coord | "Write the template — one file" |

### Department State Structure

```
{dept}/
├── state/
│   ├── dept-state.md          # Live snapshot (max 20 lines) — read on every spawn
│   ├── member-roster.md       # Utilization + skill tracking
│   ├── active-coords.md       # Append-only DC status log
│   └── incoming/              # Inter-spawn tasks from PDs
├── pipelines/
│   ├── INDEX.md               # Pipeline registry (name, version, status)
│   └── {name}/pipeline.md     # Versioned pipeline definition
├── protocols/
│   ├── INDEX.md               # Protocol registry
│   └── {name}.md              # Versioned protocol definition
├── memory/
│   ├── decisions.md           # Dept-level decisions (append-only)
│   ├── lessons.md             # Dept-level lessons (append-only)
│   └── retros/                # Monthly retrospective records
└── scratch/
    ├── dept-scratch.md        # Active session scratch
    └── coords/                # DC-* scratch files
```

### Key Skills

| Skill | Purpose |
|-------|---------|
| `/dept-resume [slug]` | Read dept-state.md, spawn dept head with lean briefing |
| `/dept-wrap [slug]` | Write dept-state.md + member-roster.md at session end |
| `/dept-status [slug]` | Read-only status digest (no spawns) |

### Key Runbooks

| Runbook | Purpose |
|---------|---------|
| `core/runbooks/dept-coord-protocol.md` | Full operational manual for the dept-coord system |
| `core/runbooks/dept-boot-sequence.md` | Two-mode dept head startup (spawn + route) |
| `core/runbooks/protocol-registry.md` | Cross-department protocol index |

---

## How to Spawn the Agency Council

### Trigger Phrases

Any of these activate the full Agency Council:

> **"BOD"** / **"assemble"** / **"assemble the board"** / **"the board"** / **"the council"** / **"activate the agency council"**

Also: *"convene the council"*, *"call the board to order"*, *"full agency"*, *"all hands"*, *"agency-wide [project]"*.

For focused teams, the trigger phrases include project type:
- *"engineering team for [project]"*
- *"content team for [launch]"*
- *"content campaign"*

### Spawning Steps

```
1. Use TeamCreate to create a team named "agency-council"
2. Spawn leaders in TWO WAVES to avoid team config race conditions:
   Wave 1 (4 agents): engineering-lead, design-lead, content-creation-lead,
                       project-management-lead
   Wave 2 (4 agents): testing-lead, specialized-lead, critiques-lead,
                       video-studio-lead
   Wait for Wave 1 to join (~30s) before spawning Wave 2.
3. Each spawn: Load the leader's agent definition file and instruct them to
   join "agency-council" and send their intro to "team-lead"
4. You (parent AI) are the council chair
5. Send a welcome brief to all leaders explaining current priorities
6. Leaders operate per runbooks/department-lead-protocol.md
```

**Important:** Spawning more than 6 agents in parallel causes race-condition
writes to the team config file, breaking late-joiners. Always use two waves.

For a project-specific team, use the kickoff protocol in `runbooks/project-kickoff-protocol.md`.

---

---

## Project Scope Management

Every active project has a `scope.json` defining its boundaries. This is the contract between the Project Director and the parent AI.

### scope.json Schema

```json
{
  "id": "project-slug",
  "name": "Project Name",
  "directories": ["path/**"],
  "filePatterns": ["*.ext"],
  "excludedPaths": [],
  "departments": ["engineering", "design"],
  "financialImportance": "low | medium | high",
  "directorId": "project-slug-pd",
  "assistantId": null,
  "memberIds": []
}
```

### Scope Enforcement Rules

1. **PD actions within scope**: File edits, read-only ops, documentation — Tier 1 bypass, no approval needed.
2. **PD actions outside scope**: All changes to files/paths not in scope.json require parent AI approval (Tier 2).
3. **Shared infra / cross-project**: Always requires parent AI approval regardless of scope.
4. **Scope review cadence**: scope.json is reviewed quarterly or when project scope changes materially.
5. **Approvals directory**: Each project has a `/{project}/approvals/` directory for logging approval requests and outcomes.

### Project Directory Structure

Each project directory follows this memory structure:
```
{project}/
├── scope.json           # Director: boundaries and authority
├── approvals/           # Director: approval request log
└── memory/
    ├── sessions/        # All: session logs (append-only)
    ├── decisions.md    # Director: architectural decisions (append-only)
    ├── lessons/        # All: synced from root lessons
    └── status/         # PM: on-demand status summaries (append-only)
```

---

*Last updated: 2026-05-02*

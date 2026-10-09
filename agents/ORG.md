# The Agency — Organizational Structure

> **GENERALIST SWITCH (2026-10-06):** all member-level specialist agents are ARCHIVED to `agents-archive/generalist-2026-10-06/`; spawn `general-purpose` + skills per `agents-archive/ROLE-MAP.md`. **DEPARTMENT SUNSET (2026-10-08):** all department leads and department coordinators (15 agent files) are ARCHIVED to `agents-archive/dept-sunset-2026-10-08/` (pre-sunset copy of this file: `agents-archive/dept-sunset-2026-10-08/ORG.md.pre-sunset`). PDs, Coords, critiques, council seats and service agents stay registered.


<!-- load only when managing or onboarding agents -->

> **Canonical reference document.** This file defines the org chart, communication protocols, and team structure for The Agency. All other documentation (runbooks, READMEs, agent files) references this as the source of truth.

---

## Executive Summary

The Agency operates on a **PD -> Coord -> Exec** model. There is no department layer.

1. **Parent AI (Level 1 - Opus)** - Central orchestrator. Plans and routes; resolves conflicts, allocates resources, approves cross-project/shared-infra decisions. Weighted by task severity and project financial importance.
2. **Project Directors (Level 2 - Opus)** - One per project. Own project delivery and knowledge work (analysis, research, planning) and QA the Execs/Coords they spawn. A PD never implements.
3. **Coords (Level 3 - Sonnet[1m])** - Autonomous owners of L3 delivery tracks; decompose a PD task and spawn Execs. See `project-management/coord.md`, `project-management/mini-coord.md`, `project-management/pd-coordinator.md`.
4. **Execs (Level 4 - general-purpose)** - Task execution. The spawner picks the model and 1-3 skills per task (role-to-skills map: `agents-archive/ROLE-MAP.md`). Spawn template: `project-management/coord.md` "Exec spawn message".
5. **Critics** - `critique-*` and `sag-critique` (`critiques/`) are spawned directly by the PD or Coord (usually via `/cc-loop` or `quality-loop-router`); there is no critique lead.

### Authority Track

```
Parent AI (Opus)
     │
Project Director (Opus)          Critics (critique-*, spawned directly)
     │
Coord (Sonnet[1m])
     │
Exec (general-purpose + skills)
```

**Inter-spawn protocol:** PDs hand work to other PDs through `{project}/memory/inter-spawn-tasks/incoming/` (see the PD definitions and `runbooks/`). Conflicts between PDs escalate to the Parent AI (Level 1), weighted by severity and financial importance.

**PD bypass authority:** Project Directors have Tier 1 bypass authority within project scope, bounded by scope.json. Bypass is limited to: file edits <10 lines, read-only operations, documentation within project boundaries. Bypass does NOT include: shared infra changes, cross-project side effects, user-facing decisions, security/auth/payment operations, PII handling, or any scope.json-external changes. Directors keep a decision log in the project for audit.

**Status reporting:** On-demand only. No automated loops. This keeps parent AI context at O(projects + exceptions) rather than O(agents).

**Model tiering:** All agents tagged with `modelTier` in frontmatter. PDs = Opus. Coords = Sonnet[1m]. Execs = spawner's choice (default Sonnet). Planning/thinking = Opus. Menial tasks (scraping, research) = Haiku.

Standing exceptions: **All Project Directors -> Opus** (2026-07-25). Content-writing Execs run on Opus when output quality is the deliverable (spawner's choice); each `critique-*` file sets its own `model:`.

NOTE: `modelTier` is documentation only - nothing in the harness reads it (the sole consumer is `scripts/agent-tools-audit.py`, as an audit flag). The key the harness acts on is `model:`. Keep both present and in sync; setting `modelTier` alone changes nothing.

**Status loop policy:** Automated recurring loops are DISABLED. Use on-demand status checks only.

---

## Org Chart

```
THE AGENCY
│
├── PARENT AI (Council Chair)
│
├── PROJECT DIRECTORS (*-pd) ───── folders: `agents/<dept>/` (PD homes; the project-scaffolder writes each new PD into the folder that fits its project)
│   └── Coords (coord, mini-coord, pd-coordinator) -> general-purpose Execs + skills
│
├── CRITICS ───────────────────── critiques/: critique-design, critique-content, critique-marketing, critique-pedagogy,
│                                 critique-seo, critique-product, critique-security, critique-brand, critique-video,
│                                 critique-data, critique-code, critique-imageprompt, critique-social, sag-critique
│                                 (spawned directly by PD/Coord; routing table in critiques/INDEX.md)
│
├── COUNCIL ───────────────────── council/: council-fable, council-opus, council-sonnet, council-haiku (+ optional Codex seat)
│
└── SERVICE AGENTS ────────────── specialized/: Delegator, curator, codebase-search, save-state-runner,
                                  project-scaffolder, understand-* workers
```

Archived (nothing deleted): department leads and department coordinators (`agents-archive/dept-sunset-2026-10-08/`), member-level specialists (`agents-archive/generalist-2026-10-06/`), earlier departments (`agents-archive/MANIFEST.md`).

---

## Agency Council

The council is 4 independent tier seats (council-fable/opus/sonnet/haiku) plus an optional Codex seat (via the `codex` CLI), run in ONE wave; the caller synthesises. Source of truth: `{agency-root}/core/memory/agency-council.md`. Seat files: `agents/council/`.

---

## Folder Directory

| Folder | Directory |
|-----------|-----------|
| Engineering (PD home) | `engineering/` |
| Design (PD home) | `design/` |
| Content Creation (PD home) | `content-creation/` |
| Project Management (PD home + Coord defs) | `project-management/` |
| Testing (PD home) | `testing/` |
| Specialized (PD home + service agents) | `specialized/` |
| Critiques | `critiques/` |
| Council | `council/` |
| Video Studio (PD home) | `video-studio/` |
| **Rooms Infrastructure** | `{agency-root}/agency-rooms/` - persistent file-based chat rooms for inter-agent communication, NEXUS handoffs, and escalation routing |

Earlier archived departments are listed in `agents-archive/MANIFEST.md`.

---

## Team Infrastructure

### Team Types

| Team | Purpose | Members | Created By |
|------|---------|---------|------------|
| **Agency Council** | Cross-dept strategy and approval | 4 council seats (+ optional Codex seat) + caller | `{agency-root}/core/memory/agency-council.md` |
| **Project Teams** | Temporary teams for specific deliverables | PD + Coord + Execs (+ critics) | Run kickoff protocol |

### Project Team Templates

Reference `{agency-root}/runbooks/project-team-templates.md` for pre-defined compositions.

### Coordination Convention

```
Human / Parent AI
       │
       ▼ (assigns work)
  Project Director ──► Coord ──► Exec (executes)
       │
       └──► Critics (scored review, spawned directly)
```

Cross-project requests go PD -> Parent AI for routing.

---

## Approval Tiers Summary

Reference `{agency-root}/runbooks/escalation-protocol.md` for the full detail.

| Tier | Approver | Examples | Response |
|------|----------|----------|----------|
| **Tier 1** | Project Director (within scope.json) | File edits <10 lines, read-only commands, documentation, code review | Immediate |
| **Tier 2** | Council Chair (parent AI) | New files, code changes >10 lines, config changes, deps, migrations | Within session |
| **Tier 3** | Human | Destructive ops, deployments, external comms, secrets, financial | Human availability |

---

## Council Trigger Phrases

> **"BOD"** / **"assemble"** / **"assemble the board"** / **"the board"** / **"the council"** / **"convene the council"** / **"full agency"** / **"all hands"** activate the council per `{agency-root}/core/memory/agency-council.md` (4 seats + optional Codex seat, ONE wave, caller synthesises).

For a project-specific team, use the kickoff protocol in `{agency-root}/runbooks/project-kickoff-protocol.md`.

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

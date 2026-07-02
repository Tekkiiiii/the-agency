# Department-Coordinator (Dept-Coord) Architecture

The Dept-Coord system provides a structured execution hierarchy within each department. It separates long-running autonomous department work from short-burst session work.

## Overview

Each department has two parallel layers:

1. **Department Head** (Opus) — strategic owner of the department. Manages pipelines, protocols, member development, and cross-department handoffs. Lives in a background session. Activated by `/dept-resume`.

2. **Dept-Coord** — coordination agent spawned by the Department Head for specific operational work. Handles pipeline execution, protocol improvement, member task dispatch, and status aggregation. Reports back to the Department Head.

## Execution Levels (D1–D6)

```
D1  Department Head (Opus)
     Owns the department strategy, pipelines, protocols, member roster
     Spawns: Dept-Coord for operational tasks

D2  Dept-Coord
     Owns a specific operational task (e.g., run a pipeline, improve a protocol)
     Spawns: Dept Members (D4) for execution work

D3  Sub-Coord (optional)
     Used for complex D2 tasks with multiple parallel workstreams
     Spawns: Dept Members for execution

D4  Dept Member (Sonnet)
     Specialist execution: writes code, generates content, runs tests, etc.
     Reports back to Dept-Coord

D5  Atomic Executor (Sonnet)
     Single-file or single-function task
     Reports back to Dept Member

D6  Leaf Task
     Smallest indivisible unit of work
```

**Rule:** Each level stops at its own termination tier. Department Heads do not implement. Dept-Coords do not execute. Dept Members do not strategize.

## Department Head Responsibilities (D1)

- Reads `state/dept-state.md` on resume — this is the single carry-forward artifact
- Checks `state/incoming/` for inter-spawn task files from PDs
- Executes `next-focus` from dept-state.md
- Spawns Dept-Coord for tasks that require multiple steps or agent dispatch
- Writes updated `state/dept-state.md` on session end via `/dept-save-state`

## Dept-Coord Responsibilities (D2)

- Spawns from Department Head with a specific operational task
- Decomposes the task into D4-level work units
- Dispatches Dept Members (or Sub-Coords for complex branches)
- Aggregates results and reports back to Department Head
- Does NOT persist between sessions — stateless within a session

## State Files

Each department has a `state/` directory:

```
{dept}/
├── state/
│   ├── dept-state.md        ← single carry-forward artifact, written by dept-save-state
│   ├── active-coords.md     ← running coord log (append-only)
│   └── member-roster.md     ← members, utilization, active tasks
├── scratch/
│   ├── dept-scratch.md      ← active session scratch (deleted on save)
│   └── coords/
│       └── dc-{task}.md     ← per-coord scratch (deleted on completion)
├── memory/
│   └── lessons.md           ← department-level lessons
└── incoming/
    └── {pd-slug}-{task}.md  ← inter-spawn tasks from PDs
```

## Department Lifecycle (Three Skills)

### `/dept-resume [dept-slug|all]`

Reads `state/dept-state.md` directly (no subagents). Spawns dept heads with lean briefings (~400 tokens per spawn). All spawns happen in a single message (parallel).

The spawn prompt contains only:
- The verbatim dept-state.md content
- Paths to runbooks (boot-sequence, dept-coord-protocol)

The dept head agent definition contains everything else (roster, approval tiers, skills, protocols) — this keeps the spawn prompt minimal.

### `/dept-save-state [dept-slug|all]`

Writes session-end state. Called by the department head before stopping.

Steps:
1. Read current dept-scratch.md and coord scratch files
2. Write updated dept-state.md (12-field structured document)
3. Update member-roster.md utilization
4. Archive completed coord scratch files
5. Promote session lessons to memory/lessons.md
6. Output confirmation

### `/dept-status [dept-slug|all]`

Read-only. No subagents, no writes.

Reads `state/dept-state.md` and last 10 lines of `state/active-coords.md`. Returns a compact digest per department. Flags attention items (blockers, stale depts, BLOCKED coords).

## Inter-Spawn Protocol (PD → Department)

A Project Director can assign work to a Department Head without spawning it directly:

1. PD writes a task file to `{dept}/state/incoming/{pd-slug}-{task}.md`
2. When the Department Head is next resumed (via `/dept-resume`), it checks `incoming/` as part of boot sequence
3. Department Head processes the task, dispatches to Dept-Coord if needed
4. Reports back to the PD's project memory or via SendMessage

This async pattern avoids PD context bloat — the PD does not wait for department execution.

## Dept-Coord Agent File

Each department has a `{dept}-coord.md` agent definition at `agents/{dept}/{dept}-coord.md`.

The Dept-Coord agent knows:
- The department's member roster
- Which skills each member uses
- Pipeline and protocol definitions
- Escalation paths

## Boot Sequence

When a department head resumes:

1. Read `state/dept-state.md` (provided in spawn prompt)
2. Check `state/incoming/` for PD task files
3. Read `scratch/dept-scratch.md` if it exists (active session resuming)
4. Execute `next-focus` from dept-state.md
5. Spawn Dept-Coord for any queued tasks
6. On completion: `/dept-save-state {dept}`

Full boot sequence: `runbooks/dept-boot-sequence.md`

## Context Budget

The Dept-Coord system is designed to keep the parent AI context at O(departments + exceptions), not O(agents).

- `/dept-status all` returns a single table — no subagent spawns
- `/dept-resume all` passes lean briefings (~400 tokens per dept head)
- `dept-state.md` is synthesized at write-time (save-state) so read-time is near-zero
- Status is read from files on demand, not pushed via messages

## Example: Marketing Campaign Pipeline

```
Tekki: "Have marketing run a campaign for our Q3 launch"
↓
Parent AI writes incoming task to:
  agents/marketing/state/incoming/tekki-q3-campaign.md
↓
/dept-resume marketing
↓
Marketing Lead (Opus) resumes, reads incoming/tekki-q3-campaign.md
↓
Marketing Lead spawns Dept-Coord:
  "Run pipeline-content for Q3 launch: blog + 3 social posts + email"
↓
Dept-Coord dispatches:
  - Blog Writer Dept Member → /pipeline-content (blog)
  - Social Media Dept Member → /pipeline-content (social x3)
  - Email Campaign Writer → /pipeline-content (email)
↓
All members report back to Dept-Coord
↓
Dept-Coord aggregates, reports to Marketing Lead
↓
Marketing Lead writes results to project memory
↓
/dept-save-state marketing
```

## Adding a New Department

1. Create `agents/{dept-slug}/` directory with `INDEX.md` and member agent files
2. Create `agents/{dept-slug}/{dept-slug}-lead.md` (department head agent definition)
3. Create `agents/{dept-slug}/{dept-slug}-coord.md` (dept-coord agent definition)
4. Create `agents/{dept-slug}/state/` with empty `dept-state.md`, `active-coords.md`, `member-roster.md`
5. Add the department to `agents/INDEX.md` and `agents/ORG.md`
6. Update the Department Registry in `skills/dept-resume/SKILL.md`, `skills/dept-save-state/SKILL.md`, and `skills/dept-status/SKILL.md`

See `agents/CONTRIBUTING.md` for agent file format guidelines.

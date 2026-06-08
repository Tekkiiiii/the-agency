---
name: Task Decomposition Methodology
description: In-depth guide for PDs and Coords on HOW to break down tasks — DAG construction, layer computation, writes-to identification, tier classification, and the two-condition parallel rule.
type: runbook
owner: system-improvement
lastUpdated: 2026-06-08
lazyRead: true
---

# Task Decomposition Methodology

**LAZY-READ:** Load this file ONLY when actively decomposing tasks (PD generating dev-plan,
Coord generating L4-L6 structure). Never load in base agent context.

Referenced by: `pd-coordinator.md`, `coord.md`, `dept-coord-protocol.md`

---

## 1. Purpose

This document codifies HOW PDs and Coords break tasks down to the finest independent
units and arrange them for maximum safe parallelism. This is the methodology behind
every `dev-plan.md` and coord structure file.

The goal is not just speed — it is **correctness at speed**. Parallel execution is safe
only when tasks cannot interfere with each other. This document defines exactly when
interference is possible and how to detect it mechanically.

---

## 2. The Two-Condition Parallel Rule

**The only rule that governs parallelism:**

Two tasks T_A and T_B may run in parallel IFF BOTH conditions hold:

**Condition 1 — No dependency edge:**
T_B does not appear in T_A's `depends-on` list, and T_A does not appear in T_B's
`depends-on` list (transitively). If T_A must complete before T_B can start — for any
reason (output consumed, state set, contract established) — there is a dependency edge.
Serialize them.

**Condition 2 — No shared write-target:**
T_A's `writes-to[]` list and T_B's `writes-to[]` list are disjoint. No file, directory,
or shared resource appears in both. If two tasks write the same file — even different
sections of it — they MUST serialize (one writes, then the other reads the result).

**If either condition fails → serialize.** Both must hold for parallel execution.

**Why Condition 2 exists separately from Condition 1:**
A dependency edge is a semantic relationship (B consumes A's output). A shared write-
target is a mechanical relationship (both touch the same file). An agent may fail to
notice a semantic dependency but the file overlap is always visible. Condition 2 is the
safety net for missed dependencies.

---

## 3. DAG Construction

A task DAG (Directed Acyclic Graph) encodes:
- Tasks as nodes
- Dependency edges as directed arrows (T_A → T_B means "T_B depends on T_A")
- Write-target sets as node metadata

**Step 1: List all atomic tasks.** Start by listing every independent deliverable at the
finest grain you can identify. "Implement auth" is not atomic — "write src/auth/login.ts"
is. Err on the side of finer granularity. Small tasks can always be merged; large tasks
create serialization bottlenecks.

**Step 2: Declare writes-to[] for each task.** For every task, list every file or
directory it will write, create, or modify. Include:
- Source files it creates or edits
- Config files it modifies
- Memory files it writes (scratch, dev-plan status updates)
- Any shared state it mutates

Do NOT include files it reads but does not write. Reads are free to parallelize.

**Step 3: Declare depends-on[] for each task.** A task B depends on task A when:
- B consumes output produced by A (reads a file A creates or edits)
- B requires a state established by A (e.g., DB schema must exist before migration)
- B extends or refines work A does (e.g., middleware wraps routes A implements)

**Step 4: Check for write-target conflicts.** Scan all task pairs. For any two tasks
sharing a file in their writes-to[] list, add a dependency edge if none exists. Assign
one as the "first writer" and the other as the "second writer" — the second writer
implicitly depends on the first. Use a sensible order (setup before use, scaffolding
before content).

**Step 5: Compute topological layers.**
- Layer 1: all tasks with empty depends-on[] (no prerequisites at all).
- Layer N: all tasks whose all prerequisites are in layers 1..N-1.
- Two tasks in the same layer have no edges between them AND no shared write-targets
  (by construction — if they had shared write-targets, one would depend on the other).

If you cannot assign a layer without circular dependencies, you have a cycle — decompose
one of the tasks further to break the cycle.

---

## 4. Writes-to Identification

The writes-to[] list is the most error-prone part. Common misses:

**Direct writes (obvious):**
- `src/auth/login.ts` — creating or editing a source file
- `memory/dev-plan.md` — updating task status
- `memory/decisions.md` — recording a decision

**Indirect writes (easy to miss):**
- A task that "sets up a schema" also writes to `migrations/001_initial.sql`
- A task that "adds auth middleware" also touches `src/server.ts` (imports the middleware)
- A task that "creates QA report" writes to `memory/qa/qa-report-{timestamp}.md`
- A task that generates HTML output writes to an output directory

**Shared directories:** If T_A writes `memory/qa/` and T_B also writes `memory/qa/`,
they conflict — even if they produce different files in that directory (race condition
on directory creation/listing). Use file-level specificity for qa reports:
T_A writes `memory/qa/qa-l3-auth-{ts}.md`, T_B writes `memory/qa/qa-l3-ui-{ts}.md`.
Different timestamps = no conflict.

**Config files:** Any task that edits a shared config file (package.json, .env, etc.)
must be serialized with all other tasks that edit the same config.

---

## 5. Layer Computation Algorithm

Given the full task list with depends-on[] and writes-to[]:

```
function compute_layers(tasks):
  # Step 1: Add write-target dependency edges
  for each pair (T_A, T_B) where T_A.writes_to ∩ T_B.writes_to ≠ ∅:
    if no edge exists between T_A and T_B:
      # Determine order: setup/scaffold tasks precede implementation tasks
      # If ambiguous: alphabetical by task id (deterministic, not semantic)
      add edge: earlier_task → later_task

  # Step 2: Topological sort → assign layers
  layer = {}
  for each task T with no remaining prerequisites:
    layer[T] = 1

  repeat until all tasks assigned:
    for each unassigned task T:
      if all T.depends_on are assigned:
        layer[T] = max(layer[dep] for dep in T.depends_on) + 1

  return layer
```

In practice: PD/Coord computes this mentally or by inspection for typical project sizes
(< 30 tasks). For larger projects, work level by level:
1. What can start immediately? → Layer 1
2. What unblocks when Layer 1 is done? → Layer 2
3. Continue until all tasks assigned.

---

## 6. Tier Classification (TIER_A vs TIER_B)

When a Coord classifies Executor tasks for the APPROACH gate:

**TIER_A (low risk — APPROACH gate skipped):** Task meets ALL four conditions:
1. Single file — touches exactly one source or config file
2. No shared state — no other concurrent Executor writes the same file or related state
3. Task type matches a Relevant Skills table row with high confidence
4. Coord has high confidence in full scope — no ambiguity about what "done" looks like

Any doubt → TIER_B. TIER_A is not a shortcut for avoiding review — it is a precise
classification for tasks where the full APPROACH gate overhead exceeds its value.

**TIER_B (higher risk — full APPROACH gate required):** All other tasks. Includes:
- Multi-file changes (writes-to[] has 2+ entries)
- Shared state (another concurrent Exec also writes to related files)
- Ambiguous scope (what exactly constitutes "done" is not clear from the task description)
- Cross-L3 impact (task touches files owned by another Coord's L3)
- Any task involving schema, config, or shared infrastructure

A mis-classified TIER_A that goes wrong is caught at CHECKPOINT or BLOCKED, and
the re-run uses TIER_B treatment. The cost of misclassification is one extra round
trip, not a quality failure.

---

## 7. Two-Tier Structure Files

**Full-scale master dev-plan** (`{project}/memory/dev-plan.md`):
- PD-owned. Contains the complete project task DAG.
- All L3 Coord assignments + all L4-L6 sub-tasks (written back by each Coord).
- PD reads this on every session start to know global task status.
- Schema: see dev-plan.md template.

**Per-Coord scoped structure file** (`{project}/memory/agents/coords/coord-{name}-structure.md`):
- Coord reads this on spawn — contains ONLY the tasks assigned to this Coord.
- PD generates the scoped file from the master dev-plan before spawning each Coord.
- Coord does NOT read the full master (context cost). Coord reads only its slice.
- Write-back rule: when a Coord generates its L4-L6 breakdown, it appends those tasks
  to `{project}/memory/dev-plan.md` under its L3 section. This keeps the master current.

---

## 8. Phase Checkpoint Rule

Decomposition burns heavy context. Planning (decomposition) and deployment (execution)
should run in separate contexts wherever possible.

**Rule:** After PD completes dev-plan generation AND Coord writes its L4-L6 structure
back to the master, check context pressure. If context ≥ 70%, or if the decomposition
was complex (many tasks, many dependency edges), run /save-state then RESPAWN to
enter the deployment phase with a clean context window.

**Why:** A PD that generated a 30-task dev-plan has consumed significant context
reasoning about dependencies. Starting Coord spawning from that same context means
Coord completions and PD review overlap with residual decomposition context — risky
for quality and for hitting the context ceiling mid-execution.

**When to always checkpoint:**
- Any dev-plan with > 15 tasks
- Any dev-plan generated from scratch (first session on a project)
- After any session where context reached 60%+ during decomposition

**When checkpoint is optional:**
- Small update to an existing dev-plan (1-3 tasks added)
- Re-running a failed layer (most context is fresh)

---

## 9. Common Decomposition Mistakes

**Mistake 1: Tasks that are too large.**
"Implement the auth module" is an L3, not an L6. At L6, a task is one file, one function,
one component. If you cannot describe what "done" looks like in one sentence naming a
specific file or output, the task is too large.

**Mistake 2: Missing write-target declarations.**
"Add middleware" must declare writes-to: [src/middleware/auth.ts, src/server.ts].
The server.ts write is often missed. Missing it creates a false parallel with any task
that also touches server.ts.

**Mistake 3: Forgetting transitivity in dependencies.**
If T_C depends on T_B and T_B depends on T_A, then T_C is at layer 3 (not layer 2).
Transitivity matters for correct layer assignment.

**Mistake 4: Treating directories as write-targets.**
"Task A writes to src/auth/" is ambiguous — does it conflict with "Task B writes to
src/auth/register.ts"? The answer is no if A writes src/auth/login.ts and B writes
src/auth/register.ts. Be file-specific, not directory-vague.

**Mistake 5: Over-serializing.**
"To be safe, I'll run everything in sequence." This defeats the purpose of the dev-plan.
Trust the two-condition rule — if both conditions hold, parallel execution is safe.
The two conditions are designed to catch all interference cases.

---

## 10. Dev-Plan Schema Reference

```markdown
# dev-plan — {project}
# Generated: YYYY-MM-DD by PD-{slug}
# Updated: YYYY-MM-DD (append-only — never delete rows)
#
# PARALLEL RULE: Two tasks may run in parallel IFF:
#   (1) no dependency edge exists between them AND
#   (2) their writes-to[] sets do not overlap (no shared write-target)
# Both conditions MUST hold. Either violation → serialize.

## Tasks

| id  | description                    | depends-on  | writes-to                     | tier       | layer | status  |
|-----|-------------------------------|-------------|-------------------------------|------------|-------|---------|
| T01 | Short description              | []          | [path/to/file.ts]             | Exec       | 1     | pending |
| T02 | Short description              | [T01]       | [path/to/other.ts]            | Exec       | 2     | pending |
| T03 | Short description (complex)    | [T01]       | [path/to/complex/]            | Mini-Coord | 2     | pending |

## Parallel Layers (auto-derived from table above)

Layer 1 (parallel): T01
Layer 2 (parallel, after T01): T02, T03
```

**Field rules:**
- `id`: short stable identifier (T01, T02...) or semantic slug (auth-skeleton, login-endpoint)
- `description`: one line — what the task produces, not how
- `depends-on`: list of task ids whose outputs this task consumes. [] = no prerequisites
- `writes-to`: list of specific file paths this task WRITES. Reads not included
- `tier`: Exec (atomic) | Mini-Coord (sub-branches needed)
- `layer`: integer computed from depends-on + write-target conflicts
- `status`: pending | in-progress | done | blocked

**Append-only:** completed tasks stay in the table with status=done. Never delete rows.
PD/Coord adds new tasks as they are discovered during execution.

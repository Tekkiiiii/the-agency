---
name: Dept-Coord Protocol
description: Operational manual for the Dept-Coord system. Dept Head deploys Dept-Coords to own D3 tracks; Dept-Coords decompose D3→D6, spawn dept members, run QA gates, and report back.
type: runbook
owner: agency-council
lastUpdated: 2026-05-13
---

# Dept-Coord Protocol

## 1. Overview

The Dept-Coord (DC) system is the department-operations parallel of the PD-Coord system.

Where PD-Coord handles project delivery (shipping features, fixing bugs, deploying code), Dept-Coord handles department operations: running pipelines, improving protocols, developing members, and maintaining department standards.

The patterns are identical: scratch files, QA gates, ACK/NACK handshakes, curator for memory retrieval, and hard authority ceilings. The D-level decomposition maps directly to the L-level decomposition of PD-Coord.

| PD-Coord concept | Dept-Coord equivalent |
|---|---|
| Project Director (Opus) | Dept Head (Opus) |
| Coordinator (Sonnet) | Dept-Coord (Sonnet) |
| Task Executor (Sonnet) | Dept Member (Sonnet) |
| L1 → L6 decomposition | D1 → D6 decomposition |
| Project work | Dept-operational work |

---

## 2. The Chain

```
Dept Head (Opus)
  └── Dept-Coord — owns one D3 track (Sonnet)
        └── Dept Member — executes one D6 atomic task (Sonnet)
```

**Dept Head** owns the department initiative (D1). Decomposes to D2 areas and D3 tracks, then dispatches Dept-Coords.

**Dept-Coord** owns one D3 track. Decomposes to D4 components, D5 sub-tasks, and D6 atomics, then spawns Dept Members.

**Dept Member** owns one D6 atomic task. Executes and reports. Zero decomposition authority.

---

## 3. D-Level Decomposition

| Level | Name | Owned By | Description |
|---|---|---|---|
| D1 | Initiative | Dept Head | Full department operation (e.g. "Q2 content pipeline improvement") |
| D2 | Area | Dept Head | Major work area within the initiative |
| D3 | Track | Dept Head → DC | Independently assignable track within an area |
| D4 | Component | Dept-Coord | Major component of the track |
| D5 | Sub-task | Dept-Coord | Work unit within the component |
| D6 | Atomic | Dept-Coord → Member | Smallest independently executable task |

### Hard Ceilings

- **Dept Head stops at D3.** Does not decompose below D3 — that is the Dept-Coord's job.
- **Dept-Coord stops at D6.** Does not spawn another Dept-Coord. Only spawns downward to Dept Members.
- **Dept Member has zero decomposition.** Executes exactly what it receives. If a D6 task is too large, the DC must re-decompose and re-assign.

---

## 4. Naming Convention

```
DC-{dept-abbr}-{d3-name}-{pun}
```

Examples: `DC-cc-pipeline-Conductor`, `DC-eng-schema-Architect`, `DC-mkt-onboarding-Greeter`

### Dept Abbreviations

| Department | Abbreviation |
|---|---|
| content-creation | cc |
| engineering | eng |
| design | des |
| growth-design | gd |
| marketing | mkt |
| sales | sal |
| project-management | pm |
| product | prd |
| projects | prj |
| testing | tst |
| operations | ops |
| career | car |
| specialized | spc |
| spa | spa |

---

## 4a. Parallel-First Execution + Global Concurrency Budget

**N_global = 4** — total live agents across the Dept Head → Dept-Coord → Member tree.
Same constraint as the PD-Coord system. Dept Head manages the global count.

**Two-condition parallel rule** (identical in pd-coordinator.md, coord.md, dept-coord-protocol.md):
Two tasks T_A and T_B may run in parallel IFF BOTH conditions hold:
1. No dependency edge: neither task is in the other's `depends-on` list (transitively).
2. No shared write-target: T_A's `writes-to[]` and T_B's `writes-to[]` are disjoint.
Either violation → serialize. Both must hold.

**Dev-plan for department initiatives:** For D1 initiatives with 3+ D3 tracks, the
Dept Head generates a `~/.claude/agents/{dept}/state/dev-plan.md` before spawning
Dept-Coords. Same schema as project dev-plan.md. DC reads its scoped slice; writes
its D4-D6 tasks back to the master.

**Dev-plan-absent trigger (dept-resume):** When dept-resume starts a session and
`~/.claude/agents/{dept}/state/dev-plan.md` is absent for a multi-track initiative,
the spawned Dept Head generates it before dispatching Dept-Coords.

**Decomposition methodology:** For detailed guidance on DAG construction and the
two-condition rule, read: `~/.claude/agents/runbooks/task-decomposition-methodology.md`
LAZY-READ: load only when actively decomposing.

---

## 5. Dept-Coord Agent Lifecycle

```
1. Read the D3 task from Dept Head's spawn prompt.

2. Set up scratch at:
   ~/.claude/agents/{dept}/scratch/coords/dc-{name}-scratch.md
   — include ## Status and ## Children tables (see Section 7).

2a. STATUS_UPDATE IN_PROGRESS: send to the Dept Head via SendMessage immediately
    after scratch setup, before any decomposition.

3. Decompose D3 → D4 → D5 → D6 using the two-condition parallel rule.
   D6 = smallest independently executable unit: one protocol file, one analysis,
   one member interview, one pipeline step, one document section.
   Assign layers based on dependencies and write-target overlap.

4. For each D6 task, spawn the appropriate Dept Member using the Agent tool.
   Apply topological-layer spawning within N_global budget:
   Spawn tasks in the same dependency-layer in PARALLEL in a SINGLE message.
   Wait for each layer to complete before spawning the next layer.
   For simple D3s (<5 members, no intra-D3 dependencies): spawn all in parallel directly.

5. QA GATE — per-member review (MANDATORY):
   For EACH member report received:
   a. Review the member's output and any QA report included.
   b. IF health ≥ 70 AND no CRITICAL issues:
        → Send ACK to member: "ACK — looks good, die quietly"
        → Add to D3 digest
      ELSE:
        → Send NACK to member: "NACK — fix: [list of issues]"
        → Wait for member to fix → re-submit → back to step 5a
   c. On each child STATUS_UPDATE: update ## Status + ## Children in scratch.
   d. Forward to Dept Head: terminal states only (DONE / BLOCKED / ESCALATE).
        — Child DONE: update scratch State → QA_GATE, do NOT forward to Head yet.
        — Child BLOCKED or ESCALATE: forward to Dept Head immediately.

6. QA GATE — pre-Dept-Head (MANDATORY):
   After ALL members are ACKed:
   a. Review the combined D3 output for completeness and consistency.
   b. Spawn a qa-only member (Sonnet) to produce a formal health report if needed.
   c. IF health ≥ 70 AND no CRITICAL:
        → Proceed to step 7.
      ELSE:
        → Spawn fix members for CRITICAL/HIGH issues.
        → Re-run QA gate. Must pass before reporting.

7. Send STATUS_UPDATE DONE to Dept Head (before the D3 COMPLETE report).

8. Send D3 COMPLETE + QA report to Dept Head.

9. WAIT FOR DEPT HEAD ACK/NACK — do not stop until Dept Head replies:
   - ACK: "looks good, die quietly" → delete scratch, stop.
   - NACK: "fix: [issues]" → fix → re-QA → re-report.
```

---

## 6. QA Gates

QA gates apply at two levels: per-member and pre-dept-head.

**Pass criteria (both levels):**
- Health score ≥ 70
- Zero CRITICAL issues
- All HIGH issues have an assigned owner and resolution plan

**Fail action:** Do not advance. Spawn fix members for CRITICAL/HIGH. Log MED/LOW for the Dept Head's awareness. Re-run the gate.

---

## 7. Scratch Board Format

Path: `~/.claude/agents/{dept}/scratch/coords/dc-{name}-scratch.md`

```markdown
# DC-{name} Scratch — {dept} — {timestamp}

## Status
| Task | State | Health | Updated | Summary |
|------|-------|--------|---------|---------|
| {d3-task-name} | IN_PROGRESS | — | {HH:MM} | decomposing |

## Children
- Member-{task}-{pun}: QUEUED
- Member-{task}-{pun}: QUEUED

Started: {timestamp}
Working on: ...
Next step: ...
Blockers: ...
```

Update `State` on every transition. Update `## Children` on every child STATUS_UPDATE. The `Updated` column uses HH:MM GMT+7.

Scratch is deleted on D3 completion.

---

## 8. Status Updates

### STATUS_UPDATE — IN_PROGRESS (fires at scratch setup)
```
DC-{name}: STATUS_UPDATE
Task: {d3-task-name}
State: IN_PROGRESS
Health: —
Summary: decomposing {d3-task-name}
Blockers: none
```

### STATUS_UPDATE — QA_GATE (fires when all children are done, before pre-Head QA)
```
DC-{name}: STATUS_UPDATE
Task: {d3-task-name}
State: QA_GATE
Health: —
Summary: all members done, entering D3 QA
Blockers: none
```

### STATUS_UPDATE — DONE (fires before the D3 COMPLETE report)
```
DC-{name}: STATUS_UPDATE
Task: {d3-task-name}
State: DONE
Health: {0-100}
Summary: {1-line summary}
Blockers: none
```

---

## 9. D3 Completion Report

**Two-message sequence: STATUS_UPDATE DONE first, then D3 COMPLETE.**

Send to the Dept Head via SendMessage:

```
DC-{name}: D3 COMPLETE + QA GATE COMPLETE
Task: {d3-task-name}
Health Score: {0-100}
Issues: {n} (CRITICAL {n}, HIGH {n}, MED {n}, LOW {n})
Open CRITICAL/HIGH: {list with assigned owner}
Report: ~/.claude/agents/{dept}/qa/qa-d3-{name}-{timestamp}.md
Awaiting Dept Head ACK/NACK...
```

---

## 10. Escalation Protocol

### D3 scope exceeded (escalate to Dept Head)
If an action falls outside the D3 track — affects another track, changes a department protocol, or creates irreversible state:

```
DC-{name}: ESCALATE — {reason}
Needed: {specific action}
Scope: {what it affects}
Awaiting: {Dept Head name}
```

Do NOT act. Do NOT retry. Wait for approval.

### Dept scope exceeded (escalate to council-chair)
If the initiative itself expands beyond what the department head can approve (cross-department protocol change, budget, shared infrastructure):

Dept Head escalates to council-chair per the Approval Authority Matrix in `department-lead-protocol.md`.

---

## 11. Context Retrieval — Curator Agent

When a D3 task requires department context not provided in the spawn prompt:

```
Agent({
  subagent_type: "curator",
  model: "sonnet",
  description: "Curator — {topic}",
  prompt: "Project: {dept}-ops\nPath: ~/.claude/agents/{dept}/\nQuestion: {your question}"
})
```

Spawn in foreground. Include the curator's answer in member spawn prompts when relevant.

Curator does NOT appear in the ## Children table — it is a service, not a task owner.

If curator returns "No relevant knowledge found", proceed with best judgment and note the assumption in your scratch file.

---

## 12. Member Spawn Prompt Template

Use the Agent tool (never SendMessage) to spawn a Dept Member:

```
You are Member-{task}-{pun}, executing a D6 task for the {dept} department.

Department: {dept}
D3 Track: {d3-task-name}
Your task: {atomic-task-description}
Task type: {task-type}
Files to touch: {file list or "none specified"}
Constraints: {constraints from DC}

Your role: execute EXACTLY the task given. Zero decomposition authority.
If the task is too large or unclear, report BLOCKED immediately — do not guess.

Scratch file: ~/.claude/agents/{dept}/scratch/members/member-{id}-scratch.md
Set it up now. Delete it when done.

When done (or blocked, or escalating), send a SendMessage to "DC-{name}" with:
  - DONE: "[1-line summary] | Health: {0-100} | Issues: {n CRITICAL, n HIGH, n MED, n LOW}"
  - BLOCKED: "[reason] — [workaround attempted]"
  - ESCALATE: "[reason] — [specific action needed from DC]"

Context retrieval: if you need department context not in this prompt, spawn a curator:
Agent({
  subagent_type: "curator",
  model: "sonnet",
  description: "Curator — {topic}",
  prompt: "Project: {dept}-ops\nPath: ~/.claude/agents/{dept}/\nQuestion: {your question}"
})

Then stop. Do not wait for a reply.
```

---

## 13. Integration with PD-Coord

### Hard boundary

| Dept-Coord | PD-Coord |
|---|---|
| Department operations | Project delivery |
| Protocol improvement | Feature development |
| Member development | Code implementation |
| Pipeline management | Sprint execution |

Dept-Coord **never** touches project delivery tasks. PD-Coord **never** touches department-operational tasks. These domains do not overlap.

### Resource request (PD → Dept Head)

When a PD needs a dept member assigned to a project, the PD sends a `resource_request` to the Dept Head per `department-lead-protocol.md`. The Dept Head dispatches the member. This is unchanged — the DC system handles only intra-department work.

A Dept-Coord is **never** spawned for a resource-request flow. That is a direct Dept Head → Member dispatch.

---

## 14. PD ↔ Dept Head Inter-Spawn Protocol

Occasionally a PD's project work generates department-operational consequences (e.g. a PD discovers a protocol gap), or a department initiative surfaces project-scoped work.

### PD → Dept Head (PD needs dept ops action)

1. PD creates a briefing file at:
   `~/.claude/agents/{dept}/state/incoming/{slug}-{YYYY-MM-DD}.md`
2. File format:
   ```
   From: PD-{slug}
   Date: {YYYY-MM-DD}
   Subject: {brief description}
   Priority: [low | medium | high]
   ---
   {context and request}
   Expected outcome: {what the dept head should produce}
   Decision log destination: {project}/memory/decisions/{slug}-dept-action.md
   ```
3. Dept Head checks `incoming/` on boot (see dept-boot-sequence.md Mode 1, Step 3).
4. Dept Head processes, acts (potentially spawning a DC), and writes outcome to both:
   - The department decision log: `~/.claude/agents/{dept}/memory/decisions/`
   - The PD's decision log destination specified in the briefing

### Dept Head → PD (dept initiative needs project-scoped action)

1. Dept Head creates a briefing file at:
   `{project}/memory/inter-spawn-tasks/incoming/{slug}-{YYYY-MM-DD}.md`
   following the existing PD inter-spawn protocol format.
2. PD picks it up on next boot or on receiving a SendMessage notification.
3. PD acts within project scope and writes outcome to both:
   - The project decision log: `{project}/memory/decisions/`
   - The dept head's decision log: `~/.claude/agents/{dept}/memory/decisions/`

### Authority boundary (non-negotiable)

- Dept Head cannot direct PD on project timeline, scope, or task sequencing.
- PD cannot direct Dept Head on department standards, protocols, or member assessment.
- When in conflict: both parties document positions → escalate to council-chair per `department-lead-protocol.md`.

---

## 15. Protocol/Pipeline Creation Checklist (MANDATORY)

When creating or updating a protocol or pipeline, ALL steps must be completed before the task is marked done. This ensures every related dept head and agent knows about the change.

### New Protocol

1. Create `{dept}/protocols/{name}.md` with YAML frontmatter (name, version, status, owner, cross-dept, last-updated)
2. Add row to `{dept}/protocols/INDEX.md`
3. **If cross-dept:**
   a. Add row to `runbooks/protocol-registry.md` (global registry)
   b. For each partner dept: add protocol reference to their `{partner-dept}-lead.md` — include the file path and a one-line description of what the partner needs to know
   c. Create the counterpart protocol file in the partner dept's `protocols/` dir if the partner has a distinct role (e.g., Marketing sends briefs, Content Creation receives them — each side gets its own file)
   d. Both dept heads must sign off before the protocol is marked `active`
4. Update the owner dept's `{dept}-lead.md` with a reference to the new protocol

### Updated Protocol

1. Bump version in the protocol's YAML frontmatter
2. Add entry to `CHANGELOG.md` (if pipeline) or version history table (if protocol)
3. Update `{dept}/protocols/INDEX.md` with new version
4. **If cross-dept:** update `runbooks/protocol-registry.md` with new version
5. **If cross-dept:** notify partner dept heads — update their lead files if the change affects how they interact with the protocol

### New Pipeline

1. Create `{dept}/pipelines/{name}/pipeline.md` with YAML frontmatter
2. Create `{dept}/pipelines/{name}/CHANGELOG.md`
3. Create `{dept}/pipelines/{name}/proposals/` directory
4. Add row to `{dept}/pipelines/INDEX.md`
5. Update the owner dept's `{dept}-lead.md` with a reference to the new pipeline

### Why This Matters

Without these steps, dept heads spawn into sessions with no knowledge of protocols that affect their work. The dept-lead.md file is the dept head's primary context on spawn — if a protocol isn't referenced there, the dept head doesn't know it exists.

---

## References

- Coord agent definition: `~/.claude/agents/project-management/coord.md`
- Dept boot sequence: `~/.claude/agents/runbooks/dept-boot-sequence.md`
- Dept lead protocol: `~/.claude/agents/runbooks/department-lead-protocol.md`
- Protocol registry: `~/.claude/agents/runbooks/protocol-registry.md`
- Dept state format: `~/.claude/agents/{dept}/state/dept-state.md`

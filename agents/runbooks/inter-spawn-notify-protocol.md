# Inter-Spawn Notify Protocol

**Status:** CANONICAL — Single Source of Truth
**Supersedes:** any inline SendMessage instructions in individual PD identity files
**Date:** 2026-06-02

---

## The Hard Rule

> **When a spawned PD completes an inter-spawn task, it writes a completion record
> to the caller's filesystem. It does NOT send a SendMessage to the caller PD.**

Background headless agents do not have active sessions. A SendMessage sent from a
spawned PD to its caller PD will land in the parent session (the user's main Claude
window) or be lost — the caller PD's session is already closed by the time the
spawned PD finishes. Neither party acts on it. File-only is the only reliable mechanism.

This rule applies regardless of who is calling: PD → PD, Dept Head → PD, or any
agent that spawns another agent to do work and needs to know when it is done.

---

## When SendMessage IS Legitimate

SendMessage is correct for:
- A PD reporting a digest/status to `"team-lead"` (the user's active main session)
- A Coord reporting to its spawning PD, when both are live in the same foreground session
- Any two agents that are verifiably alive in the same session simultaneously

SendMessage is WRONG for:
- A background spawned PD notifying its background caller PD
- Any handoff where the receiver's session may have already closed
- Inter-spawn task completion notification of any kind

---

## Canonical Flow

### Phase 1 — Caller PD Creates the Task

```
1. Write briefing:
   {target-project}/memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md

2. Write delegation tracking:
   {caller-project}/memory/tasks/ongoing/delegated-{task-id}.md

3. Spawn target PD (run_in_background: true for headless, false for showcase mode)

4. Do NOT SendMessage to the target PD. The file IS the notification.
   The target PD will find it on boot via pd-resume.
```

Full spawn protocol: `~/.claude/skills/pd-spawn/SKILL.md`

### Phase 2 — Spawned (Target) PD Does the Work

```
1. pd-resume reads: next-session.md + incoming/*.md (per 2026-06-02 pd-resume fix)
   → incoming tasks are injected into the spawn briefing automatically

2. Spawned PD reads its identity file + the incoming briefing
3. Updates briefing status to IN_PROGRESS
4. Does work exclusively in its own project directory
5. Appends completion record to caller's delegation task file:

   ## Completion — {ISO timestamp} UTC
   **Status:** DONE — [1-sentence summary of what was delivered]

6. Moves briefing from incoming/ to completed/
7. Runs /save-state → stops
```

The spawned PD NEVER sends a SendMessage to the caller PD.

### Phase 3 — Caller PD Learns of Completion

```
On next /pd-resume {caller-slug}:
  1. pd-resume reads delegated-{task-id}.md
  2. Sees the Completion section → moves file to tasks/completed/
  3. Reports to user: "✅ {task-id} complete — [summary]"
```

No SendMessage is needed. The delegation file is polled on every resume.

---

## File Layout

```
Caller project:
  memory/tasks/ongoing/delegated-{task-id}.md      ← created by caller, written by spawned
  memory/tasks/completed/delegated-{task-id}.md    ← moved here by caller on detection

Target project:
  memory/inter-spawn-tasks/incoming/inter-spawn-{task-id}.md    ← briefing (pending)
  memory/inter-spawn-tasks/completed/inter-spawn-{task-id}.md   ← briefing (done)
```

---

## Dept Head → PD Variant

When a Dept Head creates a task for a PD:

1. Dept Head writes briefing to `{project}/memory/inter-spawn-tasks/incoming/{slug}-{YYYY-MM-DD}.md`
2. PD picks it up on next boot — pd-resume reads incoming/ automatically (per 2026-06-02 fix)
3. No SendMessage from Dept Head to PD
4. PD writes outcome to project + dept decision logs as specified in the briefing

---

## Smoke Test: system-improvement ↔ the-agency

Scenario: PD-system-improvement delegates a task to PD-the-agency.

Step | Who | Action | File
-----|-----|--------|-----
1 | system-improvement-pd | Write briefing | `~/projects/the-agency/memory/inter-spawn-tasks/incoming/inter-spawn-20260602-the-agency-N.md`
2 | system-improvement-pd | Write delegation | `~/.claude/projects/system-improvement/memory/tasks/ongoing/delegated-20260602-the-agency-N.md`
3 | system-improvement-pd | Spawn the-agency-pd (background) | —
4 | the-agency-pd (on boot) | pd-resume reads incoming/ → sees briefing | —
5 | the-agency-pd | Update status to IN_PROGRESS, do work | —
6 | the-agency-pd | Append Completion to delegation file | `~/.claude/projects/system-improvement/memory/tasks/ongoing/delegated-20260602-the-agency-N.md`
7 | the-agency-pd | Move briefing to completed/ | `~/projects/the-agency/memory/inter-spawn-tasks/completed/...`
8 | the-agency-pd | /save-state → stop | —
9 | system-improvement-pd (next session) | pd-resume detects Completion section | moves to tasks/completed/, reports to user

No SendMessage at any step.

---

## References

- Decision: `~/.claude/projects/system-improvement/memory/decisions/2026-06-02-inter-spawn-notify.md`
- Caller implementation: `~/.claude/skills/pd-spawn/SKILL.md` (Steps 3–5b)
- PD identity template: PD Spawner Protocol sections in `agents/specialized/*-pd.md`
- The constraint in context: `dept-coord-protocol.md` §14 Dept Head → PD

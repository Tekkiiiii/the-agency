---
name: Checkpoint Handshake Protocol
description: Scratch-board poll handshake for the Exec/Member-facing APPROACH and CHECKPOINT gates. Replaces the old upward-SendMessage-and-wait pattern, which can deadlock because upward name-addressed SendMessage does not resolve.
type: runbook
owner: agency-council
lastUpdated: 2026-07-29
version: 1.0.0
---

# Checkpoint Handshake Protocol

## Why this exists

Upward name-addressed SendMessage does not resolve — the team roster is flat, so a
message from a child agent to a punny name like "Coord-{l3-name}-{pun}" or "DC-{name}"
misroutes to main, not the intended parent. This is a permanent harness limitation, not
a bug to work around case-by-case.

The QA gate survives this: the Exec/Member's completion report arrives as its FINAL task
result (a working channel — that's what the spawner receives when the child finishes),
and the Coord/DC's NACK travels DOWNWARD via the child's `agentId` (also working). Do
NOT apply this protocol to the QA gate — it doesn't need it.

The APPROACH gate (pre-work approval) and the CHECKPOINT gate (50% check-in) are
different: both require an INTERIM upward message — sent mid-task, before the Exec's
final result — and then a wait for a reply. That interim upward channel does not exist.
An Exec that tries it (SendMessage-and-wait) deadlocks waiting for a reply that can never
arrive. This protocol replaces that wait with a file-based poll handshake. The file is
the single source of truth in both directions.

## Precondition — mandatory, do not regress this

**Execs/Members using this protocol MUST be spawned in the BACKGROUND** (the Agent
tool's default — `run_in_background: true`, or simply omit the parameter). Background
spawning is what keeps the Coord/DC alive and free to poll the checkpoint file while its
children work. If a Coord/DC spawns an Exec/Member with `run_in_background: false`, the
Coord/DC blocks until that child finishes — it cannot poll, and this handshake becomes
structurally impossible again (back to the original deadlock risk). Never
foreground-spawn a child that will use this protocol.

## The file — one rolling file per Exec/Member

Project-scoped tree (PD → Coord → Exec, and Coord → Mini-Coord → Exec):
```
{project}/memory/agents/execs/exec-{subtask}-{pun}-checkpoint.md
```

Dept-scoped tree (Dept Head → Dept-Coord → Member):
```
{agency-root}/agents/{dept}/scratch/members/member-{id}-{pun}-checkpoint.md
```

This is a SEPARATE file from the Exec/Member's own working scratch file
(`exec-{id}-{pun}-scratch.md` / `member-{id}-scratch.md`) — the checkpoint file exists
only for this handshake. It is a SINGLE rolling file reused across both gates: the
APPROACH request/reply is written first; when the CHECKPOINT gate fires later in the
same task, the Exec overwrites `## Request` and `## Reply` in the same file with the new
request. There is no history to preserve here — the scratch file already has that.

## Format

```markdown
# Exec-{subtask}-{pun} Checkpoint — {project} — {timestamp}

## Request
Type: APPROACH | CHECKPOINT
Task: {task-name}
Plan: {2-4 bullets — files to touch, changes, what you won't do}      (APPROACH only)
Assumptions: {...or "none"}                                            (APPROACH only)
Risks: {...or "none"}                                                  (APPROACH only)
Done so far: {1-2 sentences}                                           (CHECKPOINT only)
Remaining: {1-2 sentences}                                             (CHECKPOINT only)
Issues: {any blockers or course-correction needs, or "none"}           (CHECKPOINT only)
Status: AWAITING

## Reply
```

The Exec writes `## Reply` as an empty heading up front, in the SAME write that creates
the request — this lets both sides poll for the literal string `Status: REPLIED` rather
than needing to detect whether content exists under a heading.

## Exec/Member side

1. Write the checkpoint file with `## Request` filled in, `## Reply` present but empty,
   `Status: AWAITING`.
2. Poll the SAME file, bounded:
   ```bash
   # Bash tool: pass timeout: 330000 on this call. The DEFAULT is 120s, which would
   # kill this loop around iteration 8 and return a tool error instead of a clean
   # timeout — the proceed-and-mark-UNREVIEWED branch below would never run.
   for i in $(seq 1 20); do
     grep -q '^Status: REPLIED' "{checkpoint-file}" && break
     sleep 15
   done
   grep -q '^Status: REPLIED' "{checkpoint-file}" \
     && echo CHECKPOINT_REPLIED || echo CHECKPOINT_TIMEOUT
   ```
   ~20 iterations x 15s = a 5-minute ceiling. Tune the numbers if you have a specific
   reason; keep the loop bounded — never poll unbounded.
   Branch on the emitted signal, not on the exit code — the loop always exits 0.
   `CHECKPOINT_REPLIED` → step 3. `CHECKPOINT_TIMEOUT` → step 4. If the call returns a
   tool timeout error instead of either signal, you forgot the `timeout` parameter;
   treat it as `CHECKPOINT_TIMEOUT` and take step 4.
3. **On `CHECKPOINT_REPLIED`:** read the `## Reply` block, act on it, continue the Lifecycle.
4. **On `CHECKPOINT_TIMEOUT`** (loop exhausted without `Status: REPLIED`): PROCEED with your existing
   plan rather than deadlocking — but mark the gate as unreviewed in your final
   completion report:
   - APPROACH timeout → include `APPROACH_UNREVIEWED` in your completion report
   - CHECKPOINT timeout → include `CHECKPOINT_UNREVIEWED` in your completion report
   The unreviewed marker is mandatory paperwork, not optional — a silent proceed with no
   marker deletes the gate while keeping none of its value. Do NOT re-poll indefinitely —
   one bounded wait, then move on.
5. The Coord/DC MAY also send a downward SendMessage (via your `agentId`) as a wake-up
   nudge — that direction works. Correctness never depends on the message; the file is
   authoritative. If the message arrives before you finish polling, still read the
   `## Reply` block before acting (the message is a nudge, not the reply content).

## Coord/Dept-Coord side

1. Between spawn waves and while awaiting Exec/Member completions, poll for outstanding
   requests:
   ```bash
   grep -l '^Status: AWAITING' {project}/memory/agents/execs/*-checkpoint.md 2>/dev/null
   ```
   (dept-scoped: `{agency-root}/agents/{dept}/scratch/members/*-checkpoint.md`)
   Do this at every natural pause — after each spawn batch, before/after each completion
   you process — and at minimum once per turn while any Exec/Member is in flight. Do not
   let an AWAITING request sit unpolled indefinitely.
2. For each file with `Status: AWAITING`, read `## Request` and decide:
   - APPROACH: plan correct → `ACK_APPROACH — proceed`
     plan has issues → `REVISE_APPROACH — {specific feedback}`
   - CHECKPOINT: on track → `ACK_CONTINUE`
     needs correction → `COURSE_CORRECT — {specific instructions}`
3. Write the decision under `## Reply` in the SAME file, then change `Status: AWAITING`
   to `Status: REPLIED`.
4. Optionally SendMessage the child (via its `agentId` from spawn) as a wake-up nudge —
   a courtesy, never required for correctness.
5. This poll+reply is a file read/write — it does NOT count as, and must never be
   written as, a final task result. It is interim work, same status as scratch-board
   progress updates.

## Timeout handling at the QA gate — mandatory, do not fudge

If an Exec/Member's completion report includes `APPROACH_UNREVIEWED` or
`CHECKPOINT_UNREVIEWED`:
- Treat it as higher-risk than a normally-gated Exec/Member at the QA gate. Hold it to
  the stricter QA threshold for its task type (do not fast-ACK it even if the reported
  health score clears the normal bar).
- Actually review the diff/output yourself before ACKing — the approval step it should
  have gone through never happened.
- A silent proceed-on-timeout with no marker, or a fast-ACK of an unreviewed Exec at the
  QA gate, both defeat the purpose of this protocol — they delete the gate while leaving
  the paperwork. Deadlock (the old failure mode) is equally unacceptable. This
  stricter-QA-on-timeout path is the honest middle: the gate degrades gracefully under
  the flat-roster constraint instead of disappearing silently.

## What this does NOT change

- The QA gate (Coord/DC review of the Exec/Member's final completion report, and the
  ACK/NACK that follows) is unaffected — leave it exactly as documented in coord.md /
  dept-coord-protocol.md. Do not apply this file-poll mechanism there.
- TIER_A tasks still skip the APPROACH gate entirely (one-sentence "starting" fire-and-
  forget notice, no checkpoint file, no poll). CHECKPOINT is still mandatory for all
  tiers, TIER_A included.
- The LITE tier removes both gates outright (`core/agents/coord-lite.md`,
  `task-executor-lite.md`), so this protocol does not apply there. If either gate is
  ever re-enabled in lite, it must adopt this handshake — never the old
  SendMessage-and-wait pattern.

## References

- Coord: `{agency-root}/agents/project-management/coord.md` §6b/6c
- Mini-Coord: `{agency-root}/agents/project-management/mini-coord.md` §6b/6c
- Task-Executor: `{agency-root}/agents/specialized/task-executor.md` §2b/3a
- Dept-Coord Protocol: `{agency-root}/runbooks/dept-coord-protocol.md` §4/§4c

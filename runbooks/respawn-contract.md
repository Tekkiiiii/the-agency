# RESPAWN_REQUEST Contract (full detail — moved from CLAUDE.md 2026-07-02)

When a background PD emits `RESPAWN_REQUEST {slug}`, the parent immediately runs
`/pd-resume {slug}` to respawn its deployment phase — do NOT wait for a human
turn or just relay it. Unactioned, it strands the PD's remaining work (the "PD
did 1 item and stopped" stall). Treat as a same-turn continuation, not a
notification. After respawning: `rm ~/.claude/state/respawn-queue/{slug}`.

The chat message is the fast path but NOT the guarantee — no hook fires on
background-agent completion, so the parent can miss it. The guarantee is the
**durable flag**: the PD writes `~/.claude/state/respawn-queue/{slug}` when it
crosses the boundary, and the queue is drained deterministically at three
points: (1) `respawn-drain.sh` on every SessionStart, (2) the hourly in-session
heartbeat cron, (3) a headless `pd-heartbeat` launchd agent every hour. There is no
parent-armed wake-up tick (killed 2026-10-08).
A stranded PD is always picked up within an hour even if no session sees the
message.

## Context thresholds and monitoring (subagents)

Decision 2026-10-19: a spawned PD, Coord, Mini-Coord or Exec is a subagent (agentId != main)
and runs on ABSOLUTE tokens, not % of window. Only the main session keeps 70/75/80 % of its window.

| Context (tokens) | Action |
|------------------|--------|
| < 200k | Normal operation |
| 200k–249k | WARN: keep work small, finish the current exchange, prepare for respawn |
| 250k–299k | FINISH CURRENT TASK: no new L3s / Exec spawns, prepare for respawn |
| ≥ 300k | MANDATORY: PD `/respawn-self`; Coord `/save-state` then `/coord-respawn-self`; Exec write the final report and stop |

The `agent-ctx` mod (`mods/agent-ctx/`) measures every agent loop separately (K = floor(tokens/1000)).
At 200k or 250k it appends one line to that agent's next tool result; at >= 300k the STOP line
rides EVERY tool result until the agent ends (nothing is denied, the agent must obey):

```
CONTEXT_PCT_ALERT: {K}k tokens (subagent cap 300k) — WARNING (200k). Complete current task, keep it small.
CONTEXT_PCT_ALERT: {K}k tokens (subagent cap 300k) — FINISH CURRENT TASK (250k). No new work; wrap up and report.
CONTEXT_PCT_ALERT: {K}k tokens (subagent cap 300k) — STOP (300k). MANDATORY: Coord run /save-state and /coord-respawn-self; Exec write your final report now and stop.
```

The MAIN session keeps the % path (70%, 75%, 80% of its window), unchanged:

```
CONTEXT_PCT_ALERT: 77% — WARNING THRESHOLD (75%). Complete current task. No new L3s.
CONTEXT_PCT_ALERT: 82% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.
```

# Controller view of child context (PD / Coord)

A controller sees each child's fill without asking. The `agent-ctx` mod appends a trailing
line to the Agent tool result and to every SendMessage reply:

```
CHILD_CTX: <label> <K>k/300k (<pct>%)
```

K = floor(tokens/1000); pct = floor(tokens*100/300000). `<label>` = the child's name when it
has one, else its spawn description (trailing `[task:...]` tag removed), else the raw agentId.
No line is emitted when the child's fill record has no numeric tokens (never NaN).

Also a push alert: once per child per crossing of 250k / 300k (re-armed if the child's tokens
drop, e.g. after its compaction), a line rides the parent's NEXT tool result, whatever the tool:

```
CHILD_CTX_ALERT: <label> <K>k/300k — finish current task
CHILD_CTX_ALERT: <label> <K>k/300k — must stop, request report now
```

A child the mod cannot resolve produces no line (fail open, never a wrong name).

| Line | Parent action |
|------|---------------|
| `CHILD_CTX` | Informational. Track the child's fill; give no new work to a child past 250k. |
| `CHILD_CTX_ALERT ... finish current task` (250k) | SendMessage the child (via its agentId): "finish and report". |
| `CHILD_CTX_ALERT ... must stop, request report now` (300k) | Coord/PD requests the child's report now, then respawns the role (fresh Exec/Coord with the remaining scope) if work remains. |

Verify from the line, not from the child's own report.

---

## Respawn Procedure & Hard Limits (PD Level)

Moved verbatim from `agents/project-management/pd-coordinator.md` (2026-07-07
token-efficiency pass). The Thresholds table and Context Check Gate stay
in-def in pd-coordinator.md — only the procedure/limits tail moved here.

At ≥ 300k context: invoke `/respawn-self` skill immediately.
At ≥ 250k: complete current Coord ACK/NACK, then invoke `/respawn-self` before starting new L3.

```
Skill({ skill: "respawn-self" })
```

### Hard Limits

- Max 3 respawns per project per 24h (enforced by /respawn-self counter check)
- If RESPAWN_BLOCKED (counter hit): `/save-state` and stop — notify root, manual restart needed
- BLOCKED on respawn is NOT a failure — it is a safety stop. Document and hand off cleanly

## Respawn Procedure & Hard Limits (Coord Level)

Moved verbatim from `agents/project-management/coord.md` (2026-07-07
token-efficiency pass). The Thresholds table and Compaction retention policy
stay in-def in coord.md — only the procedure/limits tail moved here.

### Respawn Procedure (Coord Level)

At ≥ 300k context (or ≥ 250k at a clean boundary): finish current APPROACH or CHECKPOINT gate exchange, then:
```
Skill({ skill: "coord-respawn-self" })
```

Coord MUST notify PD before stopping. PD handles spawning a fresh Coord continuation.

### Hard Limits (Coord Level)

- Max 3 respawns per Coord per 24h (enforced by /coord-respawn-self counter)
- If RESPAWN_BLOCKED: escalate to PD immediately — do not continue, do not drop work

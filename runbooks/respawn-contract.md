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
heartbeat cron, (3) `com.tekki.pd-heartbeat.plist` headless every hour. A
stranded PD is always picked up within an hour even if no session sees the
message.

## Respawn Procedure & Hard Limits (PD Level)

Moved verbatim from `agents/project-management/pd-coordinator.md` (2026-07-07
token-efficiency pass). The Thresholds table and Context Check Gate stay
in-def in pd-coordinator.md — only the procedure/limits tail moved here.

At ≥ 80% context: invoke `/respawn-self` skill immediately.
At ≥ 75%: complete current Coord ACK/NACK, then invoke `/respawn-self` before starting new L3.

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

At ≥ 80% context: finish current APPROACH or CHECKPOINT gate exchange, then:
```
Skill({ skill: "coord-respawn-self" })
```

Coord MUST notify PD before stopping. PD handles spawning a fresh Coord continuation.

### Hard Limits (Coord Level)

- Max 3 respawns per Coord per 24h (enforced by /coord-respawn-self counter)
- If RESPAWN_BLOCKED: escalate to PD immediately — do not continue, do not drop work

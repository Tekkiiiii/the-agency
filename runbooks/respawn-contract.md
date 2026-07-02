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

# Goal & Wake-Up Contract (no automatic tick)
_(moved from agents/project-management/pd-coordinator.md on 2026-09-03; def keeps a stub + pointer)_

## Facts
- Subagents — PD included, even with "All tools" — get NO `ScheduleWakeup`, `CronCreate`, `/goal`, or `/loop` (verified 2026-09-03 by tool probe). PD cannot self-schedule or arm a completion condition.
- There is no automatic tick: killed 2026-10-08 (owner decision). pd-resume no longer arms a `ScheduleWakeup` fallback after a spawn wave, and reports no longer carry a `GOAL_CHECK` block.
- The operator runs `/goal` when they want a check-in. Do not re-arm `ScheduleWakeup` from pd-resume or any PD.

## PD rules
1. **Never self-assert.** Test/build/deploy claims cite command + exit code (evidence gate). Author != verifier: Coord QA / integration QA (general-purpose + /qa-only, /run-acceptance-tests, /webapp-testing; role file `agents-archive/generalist-2026-10-06/specialized/integration-tester.md`), never the writing Exec.
2. **RESPAWN_REQUEST + durable flag unchanged.** Flag at `~/.claude/state/respawn-queue/{slug}` is the guarantee; drain points in `runbooks/respawn-contract.md`.
3. **Check-in replies are cheap.** When asked for status (the operator, `/goal`), answer from `pd-status-live.md` in <=5 lines. Do not re-derive, re-read, or re-plan.
4. **Hard stops are structural** (wall-clock, N_global=5, 5-failure critique rule). Do not reason around them.
5. **Terminal blocker** -> report `BLOCKED(...)` and stop. Never idle-loop.

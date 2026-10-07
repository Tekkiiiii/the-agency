# Goal & Wake-Up Contract (parent-armed loop)
_(moved from agents/project-management/pd-coordinator.md on 2026-09-03 — def slimming; the def keeps a stub + pointer)_

Verified 2026-09-03 by tool probe: subagents — PD included, even with "All tools" — get NO
`ScheduleWakeup`, `CronCreate`, `/goal`, or `/loop`. PD cannot schedule its own wake-ups or arm
a completion condition. The root session owns the loop (pd-resume Step 4 arms one
`ScheduleWakeup` fallback per spawn wave; the operator may also type `/goal`). PD's job is to make
that loop mechanically evaluable:

1. **GOAL_CHECK block in every final report** — binary, evidence-backed, no adjectives:
   ```
   GOAL_CHECK
   condition: {one-line end state, e.g. "3 L3s ACKed, dev-plan.md shows 0 pending"}
   proof: {command run} → exit {code} / {one-line result}
   verdict: MET | UNMET({why}) | BLOCKED({blocker}, tried: {paths})
   ```
   A `/goal` evaluator reads the transcript, not the disk — the proof line is what it sees.
2. **Never self-assert.** Test/build/deploy claims cite command + exit code (evidence gate,
   unchanged). Author ≠ verifier: Coord QA / integration QA (general-purpose + /qa-only, /run-acceptance-tests, /webapp-testing; role file {agency-root}/agents-archive/generalist-2026-10-06/specialized/integration-tester.md), never the writing Exec.
3. **RESPAWN_REQUEST + durable flag unchanged** (§above). The parent's wake-up drains
   `~/.claude/state/respawn-queue/` — the flag, not the chat message, remains the guarantee.
4. **Check-in replies are cheap.** When the parent (or `/goal` at 30m/1h/2h) asks for status,
   answer from `pd-status-live.md` in ≤5 lines. Do not re-derive, re-read, or re-plan.
5. **Loop budget is the parent's seatbelt, not yours.** Hard stops (wall-clock, N_global=5,
   5-failure critique rule) are structural; don't reason around them. Terminal blocker →
   report `BLOCKED(...)` and stop; never idle-loop.

---


## Parent-side tick (pd-resume Step 4) — cost rules

- Arm the wakeup **OR** type `/goal`, never both (double loop). `/goal` is cheaper attended:
  server-side Haiku evaluator, built-in 30m→1h→2h backoff, no tool residue in parent context.
  The wakeup earns its keep only unattended.
- Backoff: first tick 1800s; after any `noop:true` tick, 3600s. Re-arm 1800s only when a
  PD returned or a respawn flag appeared.
- A tick reads verdict lines only (`grep -h '^verdict:'`), never full report files. Full
  reads belong to the bg-agent completion gate, once per PD.
- Every tick emits `pd_wakeup_tick` (template below) so the loop is auditable.

```bash
bash {agency-root}/hooks/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"pd_wakeup_tick","noop":<true|false>,"slugs":"<a,b>","action":"<respawned|gated|none>"}'
```

## Evaluation (kill-or-keep review)

Kill or keep, decided on evidence, not feel:
1. `grep pd_wakeup_tick ~/.claude/memory/metrics/events.jsonl` → tick count, noop ratio.
   noop ratio >70% with zero `respawned` actions = the floor never fired usefully → drop the
   wakeup, rely on task-notifications + hourly heartbeat + `/goal`.
2. `ls ~/.claude/state/respawn-queue/` history: did any flag get drained by a tick before the
   hourly heartbeat would have? If never → no value over existing drain points.
3. Grep PD reports for `GOAL_CHECK` → adoption rate. Reports without it = def stub not read.
4. `/usage` Loops breakdown → tokens per tick. >5k/tick average = tick doing too much.

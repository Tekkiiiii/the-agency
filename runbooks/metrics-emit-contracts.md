# Metrics Emit Contracts

Full bash templates for all emit-metric events. The parent AI fires these at decision points — NOT subagents.
Event **names** and **triggers** stay inline in CLAUDE.md. This file provides the verbatim JSON templates for copy-paste.

SSOT: `~/.claude/memory/metrics/emit-metric.sh` — fire-and-forget, non-blocking.

---

## Event 1 — curator_skip

**Trigger:** After deciding to skip Curator (context-sufficiency skip).

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"curator_skip","reason":"context-sufficiency","skip_reason_excerpt":"<1-line reason agent judged context sufficient — what specific info in the prompt made Curator unnecessary>"}'
```

F17 note: `skip_reason_excerpt` enables audit of over-skipping. Skip rate flagged for review at **80%** (raised from 65% by F24 audit 2026-06-23); excerpt lets reviewers assess whether skips were justified.

F24 audit (2026-06-23): 23 skips / 10 spawns = 70% skip rate. Of the 5 auditable skips (post-F17, have excerpt), 5/5 were JUSTIFIED — each cited ground truth already verbatim in the spawn prompt (resolved paths, decisions in next-session, fully-injected briefs). 18 skips predate F17 (no excerpt, unauditable). Conclusion: not over-skipping — the high rate reflects rich verbatim context injection working as designed, not Curator being wrongly bypassed. Action: raised review threshold 65%→80% (option a); did NOT tighten skip language (option b). Re-audit at next f18 review (2026-07-17) when more F17-instrumented excerpts have accrued.

---

## Event 2 — curator_spawn

**Trigger:** After spawning Curator for an investigation.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"curator_spawn","reason":"investigation"}'
```

---

## Event 3 — delegator_cache_hit

**Trigger:** Cache hit in `~/.claude/memory/delegator-cache.md` — Delegator spawn skipped.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"delegator_cache_hit","route":"<route>","project":"<slug>","matched_pattern":"<first-8-words-of-matched-cache-key>"}'
```

F15 note: `matched_pattern` enables cache diagnostic — which patterns hit vs. miss.

---

## Event 4 — delegator_spawn

**Trigger:** Cache miss — Delegator spawned. Emit AFTER Delegator returns its route.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"delegator_spawn","route":"<route>","project":"<slug>","miss_pattern":"<first-8-words-of-task-pattern-that-missed>"}'
```

After emitting: append `(task-pattern → route)` entry to `~/.claude/memory/delegator-cache.md`.

---

## Event 5 — generalist_ban_violation

**Trigger:** BEFORE spawning `general-purpose` or `claude` as `subagent_type` outside the 3 allowed conditions.
Emit, then STOP and spawn Delegator instead. Do NOT proceed with the generalist spawn.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"generalist_ban_violation","subagent_type":"general-purpose","context":"<one-word reason>"}'
```

---

## Event 6 — bg_agent_verified

**Trigger:** After verifying all deliverables claimed by a background agent (PD, Coord, or any `run_in_background:true` spawn).

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"bg_agent_verified","agent":"<name>","files_checked":<n>,"all_present":<true|false>}'
```

Verification steps: for EVERY claimed file, run `ls -la {path}` and `wc -l {path}`.
If file missing or 0 bytes: mark BLOCKED, not DONE.

---

## Event 7 — tier_checked (F16)

**Trigger:** Every time the Autonomy Tier Gate runs (fast-path or full JSON lookup),
BEFORE the gated action executes. Full gate protocol: `runbooks/autonomy-tier-gate.md`.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"tier_checked","action_type":"<action_type>","tier":"<auto_ack|agent_gated|operator_gated>","path":"fast_path|full_lookup"}'
```

Never skip the emission to save time — it's the only audit trail that proves the gate ran before an action executed.

---

## Event 7 — eval_run

**Trigger:** ONLY an actual live run of the `~/.claude/evals/` cold-recall
agent-behavior harness (`evals/config.json` defines this exact schema;
`evals/cases.jsonl` holds the 25 doctrine/protocol cases). This is a manual
or Gardener-triggered pass — there is no automated scheduler.

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"eval_run","case_id":"<eval-NNN>","dimension":"success|trajectory|cost|safety|composite","verdict":"PASS|FAIL|Unknown","failure_class":"tool-execution|data-grounding|reasoning|none","cost_usd":<n>,"project":"<slug>"}'
```

F25 correction (2026-07-29): a 2026-07-29 audit misattributed this event's
only live site to `skills/ship/SKILL.md` — that was a grep false positive on
the unrelated substring `eval_runner` (a Ruby test-suite convention in gstack
docs, nothing to do with this metric). The true and only definition site is
`evals/config.json`. **`eval_run` DOES measure recall-evals** — specifically
the agent-behavior cold-recall harness — but it is a **different harness**
from `{project}/memory/qa/recall-evals.md` (the memory-fact recall eval set
used by `mem-scorecard.py`'s D1/D2 checks, which never touches
`events.jsonl` at all). The two systems share vocabulary ("cold-recall",
"eval pass") but are unrelated; do not read a gap in one as a gap in the
other. Last real harness run: 2026-06-14 (26 events). The two July 2026-07-07
result files in `evals/results/` were manual doctrine-audit passes (diffing
doctrine text against case expectations), not live harness executions — that
methodology genuinely does not touch `emit-metric.sh`, so their absence from
`events.jsonl` is expected, not a gap.

---

## Event Reference — what each event measures, what should trigger it

Kills the false-alarm class where a silent event is indistinguishable from a
dead one. Add a row here whenever a new event is introduced.

| Event | Measures | Fires when | Silence is OK when |
|---|---|---|---|
| `curator_skip` | Lookup-first compliance (skip side) | A direct lookup (graph/Pinecone/file) answered a project-knowledge question instead of spawning Curator | Never fully OK — see F25 note above; a long gap during active lookup-heavy work is drift, not health |
| `curator_spawn` | Lookup-first compliance (spawn side) | Curator was spawned for multi-source synthesis | No project-knowledge investigations happened |
| `delegator_cache_hit` | Routing lookup-first (cache side) | `delegator-cache.md` exact match used | No ambiguous routing decisions happened |
| `delegator_spawn` | Routing lookup-first (spawn side) | Delegator spawned for ambiguous/cross-domain routing | No ambiguous routing decisions happened |
| `generalist_ban_violation` | Generalist-spawn ban compliance | Caught self about to use `general-purpose`/`claude` outside the 3 allowed conditions | No such near-miss occurred (ideally always the case) |
| `bg_agent_verified` | Background-agent completion-gate compliance | Verified all deliverables of a `run_in_background:true` spawn | No background agents returned |
| `save_state` / `save_state_complete` | save-state script execution | `save-state.py` ran (either mode — script cannot distinguish INLINE vs SUBAGENT) | No save-state ran (unlikely — fires constantly in normal use) |
| `save_state_spawn` | SUBAGENT-mode save-state usage specifically | Caller is about to spawn a `save-state-runner` (`/save-state all` or crash recovery) | Only INLINE saves happened this window — genuinely healthy if no `all` runs or recoveries occurred |
| `eval_run` | Cold-recall agent-behavior harness (`~/.claude/evals/`) — doctrine/protocol compliance grading | A live harness run executed a case and graded a dimension | No live harness run was triggered (manual/Gardener-only cadence — long gaps are normal unless a Wave-2 gate is pending) |
| `tier_a` / `tier_b` | Coord Exec-tier classification compliance | A Coord classified a subtask before spawning an Exec | No Coord spawned any Exec in the window — **verify via Coord scratch-file mtimes before trusting this**, not just the metric's own silence (F25: 2026-07-29 audit found Coords ran 2026-07-27/28 and spawned Execs without emitting either tier event — real drift, not silence-is-fine) |
| `coord_fanout` | PD→Coord fan-out width | A PD spawned a wave of Coords | No PD spawned a Coord wave |
| `scorecard_check` / `scorecard_run_start` / `scorecard_run_end` | `mem-scorecard.py` execution | The memory scorecard script ran | Scorecard not invoked this window |
| `mem_find` | `mem-find.sh` usage | A memory lookup used the mem-find helper | No memory searches via that helper |
| `canary_session_check` | Session-start canary/bloat check | `canary-session-check.sh` ran | Script not invoked |
| `gardener_run` | `mem-gardener.sh` execution | Gardener maintenance pass ran | Gardener not scheduled/triggered this window |
| `write_evidence` | Write-tool evidence hook | Any Write tool call, hook-captured | Effectively never silent in active sessions — a gap flags the hook itself, not behavior |
| `startup_bloat_flag` | Session-start context bloat detection | `canary-session-check.sh` detected bloat | No bloat detected (healthy) |

## Quick Reference

| Event | When |
|-------|------|
| `curator_skip` | decided NOT to spawn Curator (context-sufficiency) |
| `curator_spawn` | spawned Curator for investigation |
| `delegator_cache_hit` | skipped Delegator — cache hit |
| `delegator_spawn` | spawned Delegator — cache miss |
| `generalist_ban_violation` | caught self about to use general-purpose/claude illegally |
| `bg_agent_verified` | verified background agent deliverables |
| `tier_checked` | Autonomy Tier Gate ran before a write/deploy/send/mutate action |

See also: [Mandatory agents](../memory/lessons/agent-orchestration.md)

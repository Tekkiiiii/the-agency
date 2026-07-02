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

## Quick Reference

| Event | When |
|-------|------|
| `curator_skip` | decided NOT to spawn Curator (context-sufficiency) |
| `curator_spawn` | spawned Curator for investigation |
| `delegator_cache_hit` | skipped Delegator — cache hit |
| `delegator_spawn` | spawned Delegator — cache miss |
| `generalist_ban_violation` | caught self about to use general-purpose/claude illegally |
| `bg_agent_verified` | verified background agent deliverables |

See also: [Mandatory agents](../memory/lessons/agent-orchestration.md)

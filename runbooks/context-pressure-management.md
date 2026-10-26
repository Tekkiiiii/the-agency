# Context Pressure Management

Thresholds and behavior when context window pressure builds. Loaded on demand via the `/context-pressure` skill (CLAUDE.md On-demand table):
"when context >60%, see this runbook; thresholds: 60% → suggest compact, 75% main session → save-state. Subagents use absolute tokens (table below)."

---

## Thresholds

| Context % | Action |
|-----------|--------|
| >60% (statusline turns yellow) | Proactively suggest `/compact` before starting a new major task |
| 75% in the MAIN session | Complete current task and run `/save-state` |
| Subagent (any agentId != main) | ABSOLUTE tokens, not %: 200k warn, 250k finish current task / no new work, 300k mandatory (Coord: `/save-state` + `/coord-respawn-self`; PD: `/respawn-self`; Exec: write report and stop). From 300k a STOP line rides every tool result until the agent ends (no denies). |

Main session keeps 70/75/80 % of its window unchanged. Controllers (PD/Coord) see
`CHILD_CTX: <label> <K>k/300k (<pct>%)` trailing the Agent tool result and SendMessage
replies, plus a `CHILD_CTX_ALERT` line on the parent's next tool result when a live child crosses 250k/300k. Spec: `respawn-contract.md`.

---

## Decision record: subagent context cap (2026-10-19)

Requested by the maintainer: subagents at most 300k, preferably under 250k. Every subagent resolved to a
`[1m]` model, so the %-of-window alerts first fired at 700k and respawn at 800k.

- **Chosen: A** — `agent-ctx` mod, subagent branch on absolute tokens (200k/250k/300k) plus a STOP
  line on every tool result from 300k. Soft (the agent must obey the line); smallest diff; main untouched.
- **Rejected: B** — strip `[1m]` from subagent models in `hooks/lib/model-pin.py` so the harness
  compacts at 200k. Mid-Exec auto-compaction loses working state, 200k is below the preferred
  250k ceiling, and compaction-vs-error behaviour of a 200k id is unverified.
- **Revisit trigger:** A proves ignored, i.e. spawn-ledger `spawn_end` tokens > 350k after A landed.
  Then consider B (or A+B).

---

## When to Compact

Compact at phase transitions:
- research → planning
- planning → implementation
- After a failed approach

**Do NOT compact mid-implementation** — losing variable names and file paths is costly.

---

## Compaction Retention Policy (P2-3)

Compaction preserves:
1. **Primers** — first messages defining rules (always retained)
2. **Semantic middle summary** — synthesized summary of the middle context
3. **Recents** — last 20 messages (always retained)

Tool results are cleared first. File paths and URLs must survive in the summary.

**Rollback:** revert threshold to 70% if sessions lose critical context after compaction.

---

## Context Window Anchor

- Window size: 1,000,000 tokens (enabled via `settings.json CLAUDE_CODE_DISABLE_1M_CONTEXT=0`)
- Always compute the MAIN session's context % against 1M, NEVER 200k. Subagents are not measured as a % of window: they use absolute tokens (200k/250k/300k, table above)
- Never claim "no 1M credits" — window is permanently anchored

---

## Compute % reference

The statusline shows context %. Yellow = >60%, red = >80%. Act before red.
Claude Max window anchored by real local `claude -p` invocation via launchd plist.
curl/API calls do NOT anchor the 5h window.

See also: [agent-orchestration.md](../memory/lessons/agent-orchestration.md) for PD session lifecycle.

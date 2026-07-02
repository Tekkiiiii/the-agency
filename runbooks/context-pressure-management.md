# Context Pressure Management

Thresholds and behavior when context window pressure builds. Inline in CLAUDE.md:
"when context >60%, see this runbook; thresholds: 60% → suggest compact, 75% PD → save-state."

---

## Thresholds

| Context % | Action |
|-----------|--------|
| >60% (statusline turns yellow) | Proactively suggest `/compact` before starting a new major task |
| 75% in a PD session | Complete current task and run `/save-state` |

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
- Always compute context % against 1M, NEVER 200k
- Never claim "no 1M credits" — window is permanently anchored

---

## Compute % reference

The statusline shows context %. Yellow = >60%, red = >80%. Act before red.
Claude Max window anchored by real local `claude -p` invocation via launchd plist.
curl/API calls do NOT anchor the 5h window.

See also: [agent-orchestration.md](../memory/lessons/agent-orchestration.md) for PD session lifecycle.

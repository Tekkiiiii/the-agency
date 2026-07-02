# Background Agent Completion Gate (F11-enhanced)

**Rule (inline in CLAUDE.md):** When a background agent (PD, Coord, any `run_in_background:true` spawn) returns,
the parent AI MUST verify claimed deliverables before accepting the result as DONE.

This file contains the verification protocol and emit template.

---

## Problem

PostToolUse hooks fire only for synchronous Agent tool completions. All PDs spawn with `run_in_background:true` — the `artifact-verify.sh` hook never fires for them. This means background PD deliverables (HTML reports, QA digests, plan files) can be fabricated without triggering any automated check.

---

## Verification Steps (mandatory — applies to parent AI and PDs)

1. For EVERY file the returning agent claims to have created or modified:
   ```bash
   ls -la {full-absolute-path}
   wc -l {full-absolute-path}
   ```
2. If the file is missing OR has size 0: mark the item BLOCKED, not DONE. Do not accept the agent's completion claim.
3. If all files exist and are non-empty: proceed to ACK.

---

## Scope

**Applies to** deliverables in:
- `outputs/` directories
- `plans/` directories
- `reports/` directories
- Any `*.html` file
- Any file the agent explicitly named as a deliverable in its completion message

**Does NOT apply to:**
- Intermediate scratch files
- Log files
- Memory files (heartbeat, decisions, next-session) — these are write-and-forget, not deliverables

---

## Emit After Verification

Fire after completing verification (fire-and-forget, non-blocking):

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"bg_agent_verified","agent":"<name>","files_checked":<n>,"all_present":<true|false>}'
```

---

## Quick Checklist

- [ ] Agent returned with completion claim
- [ ] Listed every named deliverable
- [ ] `ls -la` each deliverable (exists + non-zero size)
- [ ] `wc -l` each deliverable (non-empty)
- [ ] If any missing or empty: mark BLOCKED
- [ ] If all present: emit `bg_agent_verified` and proceed to ACK

See also: [metrics-emit-contracts.md](metrics-emit-contracts.md) for full emit template reference.

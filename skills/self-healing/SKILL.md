---
name: self-healing
description: "Use when a script, build or command fails, a stack trace appears, or the user says \"it's broken\", \"this isn't working\", \"I'm getting an error\", \"fix this\". Runs a root-cause loop (triage, two attempts, then escalates to superpowers-systematic-debugging); never patches without investigation."
---

# Self-Healing Workflow Skill

## Core Philosophy

Quick wins for superficial issues (missing deps, typos, wrong paths).
If the issue persists after 2 attempts, escalate to `superpowers-systematic-debugging`.
Never apply patches without investigating root cause — triage first, then escalate.

## Diagnostic Loop
```
Error encountered
      ↓
1. Read full error message carefully
2. Identify error type (see categories below)
3. Attempt 1 fix strategy
4. Re-run / re-test
5. If still failing → try one more strategy (attempt 2)
6. After 2 failed attempts → invoke `superpowers-systematic-debugging`
   - Summarize what was tried and what happened
   - Pass the root cause hypothesis forward
```

## Error Categories & Fix Strategies

### Dependency / Import Errors
1. Check if package is installed (`pip list`, `npm list`)
2. Install missing package with correct version
3. Check for name conflicts or deprecated packages

### Permission / Path Errors
1. Verify file/directory exists
2. Check read/write permissions
3. Use absolute paths instead of relative

### Type / Runtime Errors
1. Add defensive type checks
2. Log intermediate values to trace the issue
3. Add null/undefined guards

### Network / API Errors
1. Check if service is reachable
2. Verify credentials and headers
3. Add retry logic with exponential backoff
4. Check rate limits

### Logic / Output Errors
1. Add debug logging at each step
2. Test with minimal input to isolate the issue
3. Compare actual vs expected output explicitly

## Self-Repair Rules
- Always show what the error was and what fix was attempted
- Explain *why* the fix should work
- After fixing, verify the fix didn't break anything else
- If using workarounds, flag them as technical debt

## Escalation to Systematic Debugging

If 2 attempts don't resolve the issue, stop self-healing and invoke:
- `superpowers-systematic-debugging` — for bugs, test failures, technical issues

When escalating, provide:
1. What was tried and why it failed
2. Root cause hypothesis (if any)
3. The original error message

Do NOT continue guessing — escalate after 2 attempts.
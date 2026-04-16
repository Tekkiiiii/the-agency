---
name: investigate
description: >
  Systematic root-cause debugging — follows a disciplined approach to find
  the actual cause of a bug, not just the symptom. The Iron Law: no fixes
  without root cause. The 5-phase system: replicate (get the exact error
  on command), decompose (isolate which component/narrow range of code),
  trace (follow data flow through the system), verify (prove the cause is
  the cause), fix (apply the minimal correct fix). Triggers when: bug
  report, error in logs, test failing, CI breaking, or any time something
  is broken and needs to be fixed. Key capability: disciplined process that
  prevents "symptom treatment" — fixes that address the symptom while the
  real bug stays hidden. Also for: debugging flaky tests, performance
  regressions, and intermittent failures. Not for: new feature development
  (that's /plan-eng-review territory).
---

# /investigate — Root-Cause Debugging

Systematic root-cause debugging. The Iron Law: no fixes without root cause.

## The Iron Law

**No fixes without root cause.**

Every time you fix the symptom and not the cause:
- The real bug stays hidden
- It resurfaces in a different form
- You waste time chasing shadows

Stop. Decompose. Find the cause. Fix that.

## When to Activate

Trigger `/investigate` when:
- Bug report received
- Error in logs
- Test failing
- CI breaking
- Any time something is broken

## Five-Phase System

### Phase 1: Replicate

**Get the exact error on a command.**

Don't assume. Don't infer. See it.

```bash
# Run the failing command and capture output
$COMMAND 2>&1 | tee /tmp/investigate-output.txt
```

**Capture:**
- Exact command that failed
- Exact error message
- Exit code
- Environment (OS, versions, config)
- Input that triggered the failure

**If the error is in logs:**
```bash
grep -n "ERROR\|Exception\|Failed" {logfile} | tail -20
```

**If CI is failing:**
```bash
gh run view --log-failed 2>/dev/null | tail -50
```

The output from this phase is: **the exact error, the exact command, the exact input**.

### Phase 2: Decompose

**Isolate which component or narrow range of code is responsible.**

Questions to answer:
1. Is this in my code or a dependency?
2. Is this in the frontend, backend, or database layer?
3. What's the narrowest range of code that exhibits this bug?

**Techniques:**

**Binary search through the codebase:**
```bash
git log --oneline -50 | grep -i "{error_term}"  # find related commits
git bisect start --term-.good=working --term.bad=broken
```

**Isolate the failing component:**
Comment out or bypass downstream dependencies until the error disappears.

**Reduce to a minimal case:**
Strip the input down to the smallest thing that still fails.
- If an API call fails → test the query directly
- If a UI bug → test the component in isolation
- If a perf issue → profile the specific function

**Output from this phase:** A narrow hypothesis: "The bug is in `src/auth/login.ts`, specifically in the token validation logic."

### Phase 3: Trace

**Follow the data flow through the system.**

If the bug is in `src/auth/login.ts`:

```bash
# Trace the function call
$B goto {url}/login
$B js "
  // Intercept the problematic call
  const orig = window.fetch;
  window.fetch = async (...args) => {
    console.log('FETCH:', args[0], args[1]);
    return orig(...args);
  };
"
```

**Trace variables:**
```bash
$B js "Object.keys(window).filter(k => k.includes('token')).forEach(k => console.log(k, window[k]))"
```

**Trace data flow:**
1. Where does the bad input enter the system?
2. What transformations does it go through?
3. Where does it produce the bad output?
4. What assumptions does each step make?

For each assumption, test:
```bash
# Does this assumption hold?
node -e "assumption check code"
```

**Output from this phase:** Proof of the root cause with evidence: variable values, function call traces, assumption checks.

### Phase 4: Verify

**Prove the cause is the cause.**

Before fixing, prove the causal link:
1. The cause exists (show the bad value/state)
2. If the cause is removed, the bug disappears
3. If the cause is reintroduced, the bug reappears

**Techniques:**

**Add a deliberate trigger:**
```bash
# Insert a log statement in the suspected code
echo "DEBUG: variable = $variable" >> suspicious_code.py
# Run again
$COMMAND
# Verify the log line appears
```

**Instrument the code:**
```bash
node --inspect-brk $COMMAND  # attach debugger
```

**Isolate and test:**
```bash
# Create minimal reproduction
cat > /tmp/repro.js << 'EOF'
// minimal repro of the bug
EOF
node /tmp/repro.js
```

**Output from this phase:**
```
ROOT CAUSE VERIFIED:
- Evidence: {the specific variable/value/state}
- Causal link: {proved by: intervention that removed the bug}
- Scope: {what this fix will and won't address}
```

If you can't verify, go back to Phase 2 and decompose further.

### Phase 5: Fix

**Apply the minimal correct fix.**

Minimal: Fix the cause, not the symptom. Don't add defensive code around the real problem — fix the root cause directly.

Correct: The fix addresses the verified root cause. Not a workaround — a solution.

**Apply the fix:**
```bash
# Edit the minimal code that fixes the root cause
```

**Verify the fix works:**
```bash
$COMMAND  # should succeed now
```

**Regression check:**
```bash
# Run existing tests — the fix shouldn't break anything
bun test 2>&1 | tail -20
```

**Output from this phase:**
```
FIX APPLIED:
File:    src/auth/login.ts:42
Change:  Added null check for token before validation
Evidence: login now succeeds with null token (graceful rejection)

REGRESSION: all tests pass
```

## Important Rules

- **The Iron Law is non-negotiable.** No symptom treatment. Ever.
- **Replicate first.** If you can't see the error, you can't find the cause.
- **Decompose ruthlessly.** The bug is usually in a narrow band of code.
- **Trace the data, not the control flow.** Find where bad input enters the system.
- **Verify before fixing.** Prove the cause is the cause.
- **Minimal fix.** Don't add defensive walls around a broken abstraction — fix the abstraction.
- **When stuck, decompose more.** If you can't find the cause, the component boundary is too wide.
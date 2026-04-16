---
name: plan-ceo-review
description: >
  CEO-level plan review — evaluates whether a plan is worth building at all.
  Asks: Should we do this? Are we solving the right problem? Is the scope
  right? Is the cost justified? Four modes: PROPOSE (new initiative),
  REDUCE (scope cut), HOLD (pause and re-evaluate), and ELIMINATE (kill it).
  Outputs: gap analysis, revised scope, cost estimate, go/no-go verdict.
  Trigger when: starting a new initiative, reviewing a plan before committing
  resources, cutting scope on an existing project, or evaluating whether to
  continue. Also for: pre-mortem analysis, big-ticket purchase decisions,
  and strategic alignment checks. Not for: day-to-day execution planning
  (use plan-eng-review for that).
---

# /plan-ceo-review — CEO-Level Plan Review

Reviews a plan at the strategy level: should we do this, are we solving
the right problem, is the scope right, and is the cost justified?

## When to Activate

Trigger `/plan-ceo-review` when:
- Starting a new initiative
- Reviewing a plan before committing resources
- Cutting scope on an existing project
- Evaluating whether to continue a stalled effort
- Pre-mortem analysis before a big bet

## Four Modes

| Mode | Trigger | Purpose |
|------|---------|---------|
| **PROPOSE** | New initiative | Should we do this? |
| **REDUCE** | Scope cut | Can we do less and still win? |
| **HOLD** | Pause | Should we stop and re-evaluate? |
| **ELIMINATE** | Kill it | Should this die? |

Ask the user which mode applies, or detect from context:
- "new initiative" / "start something" → PROPOSE
- "cut scope" / "scale back" → REDUCE
- "pause" / "re-evaluate" → HOLD
- "kill" / "scrap" / "cancel" → ELIMINATE

## Instructions

### Step 1: Load the Plan

Find and read the plan file:
```bash
ls -t ~/.claude/plans/*.md 2>/dev/null | head -1
```

If the user provided a specific plan path, use that instead.

Extract:
- What the plan claims to do
- What problem it solves
- What success looks like
- What resources it requires

### Step 2: Problem Validation

Ask the five forcing questions:

**1. What problem does this solve?**
If the answer is "we want to add feature X" — that's a solution looking for
a problem. The real question is: what user pain, business risk, or market
opportunity does this address?

**2. Who is the customer?**
Internal tooling: who benefits directly?
External product: what segment, what job-to-be-done?

**3. How does success look different from today?**
Quantify if possible. "Reduce deploy time from 45 min to 5 min." "Increase
signups by 20%." Vague success metrics are a red flag.

**4. What is the cost of not doing this?**
Status quo has a cost too. Compare: "If we don't do this in 6 months,
where are we? What did we miss?"

**5. What are we not doing because we're doing this?**
Every choice is a trade-off. What's the opportunity cost?

### Step 3: Gap Analysis

Assess the plan for:
- **Problem-solution fit**: Does the proposed solution actually solve the
  stated problem?
- **Scope creep**: Are there deliverables that don't serve the core problem?
- **Missing alternatives**: Is there a simpler or cheaper way to achieve
  the same outcome?
- **Risks unstated**: What could go wrong that isn't mentioned?
- **Dependencies**: What does this depend on? Are those dependencies solid?

### Step 4: Cost Estimate

Break down the cost in human time and CC+gstack time:

| Phase | Human | CC+gstack |
|-------|-------|-----------|
| Research | | |
| Design | | |
| Build | | |
| Test | | |
| Deploy | | |
| **Total** | | |

Compare against the benefit. Is this worth it?

### Step 5: Mode-Specific Output

**PROPOSE mode:**
```
CEO REVIEW — PROPOSE
════════════════════
Problem:       {stated problem}
Validated:     {yes|no|partially} — {why}
Customer:     {who}
Success:      {metric or "unclear"}
Cost:         {human weeks} / {CC+gstack hours}
Opportunity:  {what we're not doing}
Alternatives:  {simpler options considered or not}

GAP ANALYSIS:
- {gap 1}
- {gap 2}

REVISED SCOPE:
1. {must have}
2. {should have}
3. {nice to have}

VERDICT: GO | CONDITIONAL GO | NO-GO
```

**REDUCE mode:**
```
CEO REVIEW — REDUCE
════════════════════
Current scope: {what's proposed}
Proposed cuts: {what can be removed}
Core value:   {what must be preserved}

PATH TO 50% CUT:
1. {cut 1} — saves {time}
2. {cut 2} — saves {time}
3. {cut 3} — saves {time}

REMAINING SCOPE:
{minimum viable scope}

VERDICT: PROCEED WITH CUTS | REJECT CUTS | KILL INSTEAD
```

**HOLD mode:**
```
CEO REVIEW — HOLD
════════════════════
Initiative:   {name}
Why running:  {original reason}
Current state: {what's happened so far}
Why now:     {why we're questioning it}

RE-EVALUATION CRITERIA:
1. {criterion} — {still valid|changed|unclear}
2. {criterion} — {still valid|changed|unclear}
3. {criterion} — {still valid|changed|unclear}

DECISION FRAMEWORK:
- Resume if: {conditions}
- Kill if: {conditions}
- Delay if: {conditions}

VERDICT: RESUME | HOLD | ELIMINATE
```

**ELIMINATE mode:**
```
CEO REVIEW — ELIMINATE
════════════════════
Initiative:   {name}
Investment:  {time/money spent so far}
Why dying:   {reason for elimination}

LESSONS TO CAPTURE:
- {lesson 1}
- {lesson 2}

WHAT TO SALVAGE:
- {any reusable components, research, docs}

VERDICT: ELIMINATE | REDUCE INSTEAD | RESCUE
```

### Step 6: Persist Result

Log the review result:
```bash
~/.claude/skills/gstack/bin/gstack-review-log \
  '{"skill":"plan-ceo-review","status":"STATUS","mode":"MODE","scope_proposed":N,"scope_accepted":N,"scope_deferred":N,"commit":"SHA"}'
```

## Important Rules

- **Challenge the problem first.** Don't accept "we need X" at face value.
  Ask why X would solve it and what would break if we didn't do it.
- **Quantify when possible.** "Reduce deploy time" is a metric. "Improve UX"
  is not — yet.
- **Opportunity cost is real.** Every yes is a no to something else.
  Name what that is.
- **Mode drives tone.** PROPOSE is optimistic but rigorous. ELIMINATE is
  merciful, not mean.
- **This is not eng review.** Don't evaluate implementation details. That's
  plan-eng-review's job.

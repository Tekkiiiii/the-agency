---
name: autoplan
description: >
  Auto-review pipeline — runs CEO review, design review, and engineering review
  in sequence on a plan. Stops at each review gate to let the human decide what
  to address before continuing. Outputs a multi-round review report showing all
  three scores, unresolved decisions, and cross-review insights. Trigger when:
  "run autoplan", "full review", "review the plan", or any time you want
  comprehensive review coverage without running each skill manually. Also for:
  pre-ship checklist (all three reviews before /ship), and periodic health
  checks on active projects.
---

# /autoplan — Auto-Review Pipeline

Runs CEO, design, and engineering reviews in sequence, stopping at each gate
for human decisions.

## When to Activate

Trigger `/autoplan` when:
- "Run autoplan" or "full review"
- Pre-ship checklist (all reviews before /ship)
- Periodic health check on active projects

## Three-Round Review Pipeline

| Round | Review | Stops At Gate? | Skill |
|-------|--------|----------------|-------|
| 1 | CEO / Strategy | YES — decisions | `/plan-ceo-review` |
| 2 | Design / UX | YES — decisions | `/plan-design-review` |
| 3 | Engineering | YES — decisions | `/plan-eng-review` |

Each review is blocking for the next — you must pass the gate before proceeding.

## Instructions

### Pre-flight: Load the Plan

```bash
ls -t ~/.claude/plans/*.md 2>/dev/null | head -1
```

If a specific plan path was provided, use that. Extract the plan name and key claims.

### Round 1: CEO Review (`/plan-ceo-review`)

Run the CEO-level review. Stop at the verdict.

**Gate question:**
- VERDICT GO / CONDITIONAL GO → proceed to Round 2
- VERDICT NO-GO → STOP. Present the NO-GO rationale and what needs to change.

**Capture:**
- Mode used (PROPOSE / REDUCE / HOLD / ELIMINATE)
- Scope accepted vs. proposed
- Critical gaps surfaced
- Verdict

### Round 2: Design Review (`/plan-design-review`)

Run the design audit. Stop at the scorecard.

**Gate question:**
- Overall score ≥ 7 (Grade B or better) → proceed
- Overall score 5-6 (Grade C) → ask: "Design score is C. Proceed with eng review or fix design first?"
- Overall score < 5 (Grade D or F) → STOP. Major design problems before engineering resources are spent.

**Capture:**
- Overall score and grade
- Critical design gaps (below 5)
- Design recommendations

### Round 3: Engineering Review (`/plan-eng-review`)

Run the engineering review. Stop at the revised plan.

**Gate question:**
- Unresolved blockers = 0 → proceed
- Unresolved blockers > 0 → ask: "N critical engineering blockers remain. Proceed or resolve first?"

**Capture:**
- Architecture assessment
- Technical gaps
- Risks
- Test strategy
- Outside voice recommendations

### Cross-Review Insights

After all three rounds complete, identify cross-review patterns:

**Pattern: CEO says GO but Design says C or worse**
→ The scope may be too ambitious for the design maturity. Suggest cutting scope.

**Pattern: Design says A but Eng finds critical gaps**
→ The design wasn't validated against implementation reality. Get eng input earlier next time.

**Pattern: Eng says solid but CEO has concerns**
→ Engineering feasibility isn't the problem — the value proposition needs work.

**Pattern: All three say GO**
→ Green light. The plan is ready to implement.

### Final Report

```
AUTOPLAN REPORT — {plan name}
════════════════════════════════

ROUND 1: CEO REVIEW
Mode:     {PROPOSE|REDUCE|HOLD|ELIMINATE}
Verdict:  {GO|CONDITIONAL|NO-GO}
Scope:    {accepted}/{proposed}
Rationale: {one-line summary}

ROUND 2: DESIGN REVIEW
Score:   {overall}/10 (Grade {letter})
Gate:    {PASS|CONDITIONAL|FAIL}
Critical gaps: {list or "none"}

ROUND 3: ENGINEERING REVIEW
Blockers: {N} remaining
Gate:     {PASS|BLOCKED}
Technical gaps: {list or "none"}

CROSS-REVIEW INSIGHTS:
{patterns identified}

OVERALL VERDICT:
- CEO:  {GO|CONDITIONAL|NO-GO}
- Design: {PASS|CONDITIONAL|FAIL} (score: {N}/10)
- Eng:   {PASS|BLOCKED}

NEXT ACTIONS:
1. {priority 1}
2. {priority 2}
3. {priority 3}

STATUS: READY TO BUILD | NEEDS REVISION | STOPPED
```

## Gate Behavior

| Gate | Condition | Action |
|------|-----------|--------|
| CEO | NO-GO | Stop — pitch needs work |
| CEO | CONDITIONAL | Proceed, address conditions |
| Design | Score < 5 | Stop — redesign needed |
| Design | Score 5-6 | Ask — proceed or fix first? |
| Eng | Blockers > 0 | Ask — proceed or resolve first? |
| Eng | Blockers = 0 | Full clearance |

## Important Rules

- **Each gate is real.** Don't skip ahead because "it's probably fine."
- **Round 1 gates everything.** If CEO says NO-GO, the plan isn't ready — design and eng reviews are premature.
- **Cross-review insights are where the value is.** The real benefit of autoplan is seeing how the three reviews interact.
- **Document unresolved items.** Every decision deferred or blocked is a risk.
- **Verdict comes at the end.** Autoplan doesn't stop at the first red — it runs all three rounds and shows the full picture.

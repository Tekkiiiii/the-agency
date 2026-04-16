---
name: plan-eng-review
description: >
  Engineering manager-level plan review — evaluates whether a plan is
  buildable, testable, and shippable. Asks: Is this actually possible? Are
  we missing something? Is the test strategy sound? What could bite us?
  Outputs: technical gaps, risks, suggested test strategy, revised plan,
  outside voice options (Codex, CSO, tech-writer). Required before shipping.
  Trigger when: reviewing any plan with implementation work, before
  /ship runs, or when an eng decision needs a second opinion. Also for:
  architecture reviews, API contract design, database schema changes, and
  security-sensitive implementations.
---

# /plan-eng-review — Engineering Manager Plan Review

Reviews a plan at the engineering level: is it buildable, testable, and
shippable? Required before any implementation begins.

## When to Activate

Trigger `/plan-eng-review` when:
- Reviewing any plan with implementation work
- Before `/ship` runs
- An engineering decision needs a second opinion
- Starting a complex feature with architectural implications

## Prerequisites

Read the plan file:
```bash
cat ~/.claude/plans/{plan-name}.md
```

Identify:
- What is being built
- What files are affected
- What the proposed test strategy is (if any)

## Instructions

### Step 1: Buildability Check

Assess each component in the plan:

**Architecture:**
- Is the overall approach sound given the tech stack?
- Are there simpler alternatives that achieve the same result?
- Is the system design extensible for the likely future requirements?

**Dependencies:**
- Does this depend on work not yet started (blocked phases)?
- Are there third-party services, APIs, or libraries that could become unavailable?
- Are there internal services this depends on that might not be ready?

**Scale assumptions:**
- What load/volume assumptions are baked in?
- What happens when those assumptions break?
- Is there a graceful degradation path?

**Security:**
- Does this introduce new attack surface?
- Does this handle sensitive data?
- Are there authentication/authorization implications?

### Step 2: Test Strategy Review

Assess the proposed test approach:

**Unit tests:**
- What are the critical paths that need unit tests?
- Are there edge cases that should be covered?
- What's the mocking strategy for dependencies?

**Integration tests:**
- How do components talk to each other?
- What integration points need to be verified?
- Are there any contracts between services?

**E2E tests:**
- What user flows need E2E coverage?
- What's the right abstraction level — too granular or too coarse?
- Are there any tests that will be flaky by nature?

**Missing tests:**
- What would fail silently without tests?
- What edge cases are likely to regress?

### Step 3: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {risk 1} | H/M/L | H/M/L | {mitigation} |

Flag risks as:
- **BLOCKER**: Cannot proceed without resolving this
- **WARNING**: Proceed with caution, have a plan B
- **NOTE**: Be aware, unlikely to block

### Step 4: Technical Gaps

Identify missing details in the plan:
- Unspecified error handling
- Missing API contracts
- Undefined data schemas
- Unclear deployment strategy
- Gaps in logging/monitoring

For each gap:
```
GAP: {description}
WHY IT MATTERS: {consequence of leaving this undefined}
RECOMMENDATION: {how to resolve}
```

### Step 5: Revised Plan

Produce a revised version of the plan with:
- Resolved gaps filled in
- Test strategy explicitly documented
- Risks acknowledged and mitigated
- Blockers surfaced clearly

Format as a diff against the original:
```
## Engineering Review — Revised Plan

### Changes from Original:
1. {change 1}
2. {change 2}

### Unresolved Blockers:
- {blocker 1}
- {blocker 2}

### Risks Accepted:
- {risk 1} — accepted because {reason}
```

### Step 6: Outside Voice Options

Recommend additional reviews:

| Review | When to Use | Skill |
|--------|-------------|-------|
| **Codex review** | Complex logic, unfamiliar patterns | `/codex review` |
| **Security audit** | New auth flows, data handling, external APIs | `/cso` |
| **Tech writer** | User-facing documentation, API references | `/tech-writer` |
| **Design review** | UI changes, UX flows | `/plan-design-review` |

### Step 7: Persist Result

```bash
~/.claude/skills/gstack/bin/gstack-review-log \
  '{"skill":"plan-eng-review","status":"clean|issues_found","unresolved":N,"critical_gaps":N,"issues_found":N,"mode":"full|quick","commit":"SHA"}'
```

## Eng Review Checklist

Use this checklist for every review:

- [ ] Architecture sound and simplest viable approach
- [ ] Dependencies identified and available
- [ ] Error handling documented for all failure modes
- [ ] Data schemas defined (input/output for each component)
- [ ] Security implications reviewed
- [ ] Test strategy covers happy path and critical edge cases
- [ ] Logging and monitoring for production observability
- [ ] Deployment strategy clear
- [ ] Rollback plan exists
- [ ] API contracts between services documented
- [ ] Performance assumptions stated and testable
- [ ] No hardcoded secrets or config
- [ ] Rate limiting considered for public endpoints
- [ ] Backward compatibility for breaking changes

## Important Rules

- **This is REQUIRED before shipping.** No `/ship` without an eng review.
- **Be specific.** "This could be a problem" is not actionable. "This will
  fail when the user uploads >1GB because the stream is not chunked" is.
- **Accept risks consciously.** Every plan has risks. Flag them, mitigate
  where possible, and accept explicitly where not.
- **Test strategy is part of the plan.** If the plan doesn't say how
  something is tested, that's a gap.
- **Outside voice is a strength, not a weakness.** Recommend Codex or CSO
  when the plan touches unfamiliar territory.

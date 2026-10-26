# Handoff Protocol

A handoff is a structured transfer of work from one agent to another.

## When to Handoff

- Task is complete → hand off for review
- Task is blocked → hand off to resolver
- Phase complete → hand off to next phase owner
- Session ending → hand off to next session's agent

## Handoff Checklist

Before sending:
- [ ] Context written
- [ ] Session log updated
- [ ] Task notes updated
- [ ] Acceptance criteria clear
- [ ] Questions anticipated and answered

Before accepting:
- [ ] Read full handoff document
- [ ] Questions answered
- [ ] Acceptance criteria understood
- [ ] Dependencies checked
- [ ] Task assigned to self

## Anti-patterns

**Bad handoff:**
> "Done, here's the code"

**Good handoff:**
> "Built auth module. User/role model done, JWT tokens done, refresh token rotation untested. Watch for clock skew on token expiry. Questions in doc."

## Quality Gate Before Handoff

Every handoff must pass the NEXUS gate:
1. Does the receiver have enough context to continue without asking me?
2. Is the work verifiable by the receiver?
3. Are blockers surfaced, not hidden?
4. Is the next step clear?

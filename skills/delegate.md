---
name: delegate
description: Hand off to a specialized subagent
category: coordination
trigger: "/delegate" | task needs specific expertise
---

# Delegate

Use this skill to hand off work to a specialist agent.

## When to use

- Task needs specific expertise (security audit, design, etc.)
- Task is complex enough to warrant its own agent
- You have a clear brief ready

## When NOT to use

- Task is simple → do it yourself
- No clear brief → write the brief first, then delegate
- Specialist not available → do it yourself

## Delegation Checklist

Before delegating:

- [ ] Clear task description written
- [ ] Acceptance criteria defined
- [ ] Context provided (SPEC, existing code)
- [ ] Resource constraints noted
- [ ] Questions anticipated

## Brief Template

```markdown
# Delegation: {task name}

## Context
{background and why this matters}

## Task
{what exactly needs to be done}

## Acceptance criteria
1. {criterion}
2. {criterion}

## Resources
- {relevant files, docs, skills}

## Questions to answer
1. {question}

## Escalate if
{conditions that warrant escalation}
```

## After Delegation

- Monitor via task store (status updates)
- Review completed work against acceptance criteria
- Gate: passed or failed
- If failed: brief specialist on what's wrong, send back

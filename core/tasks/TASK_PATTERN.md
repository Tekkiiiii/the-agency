# Task Patterns

## Breaking Down a Task

1. Write a SPEC.md before any code
2. Create sub-tasks in the task store
3. Assign each sub-task to a worker
4. Workers report back on completion
5. Integrate and gate

## Gate Pattern

```
[SPEC] → [impl] → [TEST] → [GATE: evidence?] → [done]
                                      ↓
                              [rework] if failed
```

Evidence requirements for gates:
- Code: tests pass, lints clean
- Docs: renders correctly, links work
- Design: meets acceptance criteria
- Integration: all components work together

## Retry Pattern

Max 3 retries per task. On each retry:
1. Increment `retry_count`
2. Note the failure reason in `notes`
3. If `retry_count >= max_retries` → status = `failed`

## Handoff Pattern

When transferring to another agent:
1. Write current state to session log
2. Update task `notes` with what's done and what's next
3. Notify receiving agent with full context
4. Update `assigned_agent` to new agent name

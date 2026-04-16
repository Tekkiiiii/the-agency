---
name: swarm
description: Spawn parallel agents for independent workstreams
category: coordination
trigger: "/swarm" | parallel workstreams identified
---

# Swarm

Use this skill when you have multiple independent workstreams that can run simultaneously.

## When to use

- Features that don't depend on each other
- Writing tests while building
- Multiple files that can be changed in parallel
- Research + implementation happening simultaneously

## When NOT to use

- Workstreams have dependencies → use `delegate` instead
- Only one thing to do → do it yourself
- Need sequential gates → do in order

## How to use

1. Identify independent workstreams
2. Spawn one agent per workstream with full context
3. Collect results as they complete
4. Integrate and gate

## Spawning Parallel Agents

```javascript
// In Claude Code, spawn agents:
Agent({
  prompt: "Context: {describe workstream}\n\nTask: {specific goal}",
  description: "workstream-name"
})
```

Run agents in parallel using multiple Agent calls in one message.

## Integration After Swarm

When all agents report back:
1. Collect their session logs
2. Check for conflicts
3. Integrate into the main project
4. Gate the completed work
5. Update STATE.md

## Anti-patterns

**Bad**: "Let's build everything in parallel"
**Good**: "Auth module and UI can be built in parallel. DB schema must come first."

**Rule**: If A depends on B, they can't swarm. A waits for B.

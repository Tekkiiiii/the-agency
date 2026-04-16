# Skills Guide

Skills are reusable workflows that agents invoke to handle common tasks.

## Available Skills

| Skill | What it does | When to use |
|---|---|---|
| `save-state` | Persists session to memory files | End of every session |
| `recall` | Reads project state from memory | Start of every session |
| `swarm` | Spawns parallel agents for independent tasks | Multiple workstreams available |
| `delegate` | Hands off to a specialized subagent | Task needs a specific expert |
| `self-healing` | Diagnoses and fixes broken workflows | Something isn't working |
| `design-review` | Audits UI/UX for consistency | Before shipping UI work |
| `backend` | Designs and builds APIs, DB schemas | Backend work needed |
| `frontend` | Builds React/web interfaces | Frontend work needed |
| `tech-writer` | Writes developer docs | Documentation needed |
| `security` | Security audit of code | Before production deploy |

## Installing Skills

```bash
agency skill install save-state
agency skill install recall
```

## Creating Custom Skills

See [Developer Guide](DEVELOPER.md#adding-a-skill)

## Skill Invocation

In Claude Code, type `/skill-name` to invoke:

```
/save-state my-project
/deploy-to-vercel
/security audit
```

## Built-in Skills

Some skills are built into Claude Code and available everywhere:
- `/save` — save current state
- `/recall` — recall project state
- `/help` — built-in help

## Skill Priority

If multiple skills match, the most specific one wins.

Skills loaded from `~/.agency/skills/` override built-in skills.

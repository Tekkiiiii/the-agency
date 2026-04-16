# Skills Index

Skills are reusable workflows. Invoke them in Claude Code with `/skill-name`.

## Core Skills (always available)

| Skill | Description | Category |
|-------|-------------|----------|
| `save-state` | Persist session to memory files | memory |
| `recall` | Load project state from memory | memory |
| `pd-resume` | Resume all PDs at session start | memory |
| `project-status` | Maintain PROJECT.md conventions | memory |
| `swarm` | Spawn parallel agents for independent work | coordination |
| `delegate` | Hand off to a specialized subagent | coordination |
| `self-healing` | Diagnose and fix broken workflows | ops |
| `investigate` | Systematic root-cause debugging | ops |
| `guard` | Safety mode — destructive warnings + edit freeze | ops |

## Planning Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `autoplan` | Auto-review pipeline (CEO → design → eng) | planning |
| `plan-ceo-review` | CEO/founder-mode plan review | planning |
| `plan-eng-review` | Engineering plan review | planning |
| `plan-design-review` | Designer's-eye plan review | planning |
| `office-hours` | YC-style product framing | planning |
| `retro` | Weekly engineering retrospective | planning |

## Execution Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `ship` | Automated ship: merge → test → review → PR | execution |
| `land-and-deploy` | Merge PR → deploy → canary verify | execution |
| `setup-deploy` | Configure deploy platform | execution |
| `canary` | Post-deploy monitoring loop | execution |
| `qa` | Iterative QA testing and bug fixing | execution |
| `qa-only` | Report-only QA (no fixes) | execution |

## Quality & Review Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `design-review` | Visual QA and design audit | quality |
| `codex` | OpenAI Codex second opinion | quality |
| `cso` | Security audit (OWASP Top 10) | quality |
| `document-release` | Post-ship documentation update | quality |

## Engineering Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `backend` | Design APIs, DB schemas, server logic | engineering |
| `frontend` | Build React/web interfaces | engineering |
| `tech-writer` | Write developer documentation | engineering |
| `github-deploy` | Deploy via GitHub Actions | deployment |
| `vercel-deploy` | Deploy to Vercel | deployment |
| `railway-deploy` | Deploy to Railway | deployment |
| `supabase-deploy` | Deploy to Supabase | deployment |

## Coordination Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `room-manager` | Poll agency rooms, route escalations | coordination |
| `swarm` | Spawn parallel agents | coordination |
| `delegate` | Hand off to a specialist | coordination |

## Using Skills

In Claude Code, invoke any skill with:

```
/skill-name
```

Or combine with context:

```
/autoplan
/pd-resume all
/ship
```

## Creating a Skill

See `core/agents/` for the full developer guide.

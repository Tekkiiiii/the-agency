# Skills Index

Skills are reusable workflows. Invoke them in Claude Code with `/skill-name`.

## Memory & Session Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `save-state` | Freeze session to memory files — writes logs, heartbeat, next-session brief, Pinecone upsert | memory |
| `recall` | Load project briefing from save-state files — outputs 6-field summary | memory |
| `pd-resume` | Resume one or all PDs at session start — parallel recall + spawn | memory |
| `wrap` | Freeze inbox task session — archive completed/abandoned, write session logs | memory |
| `unwrap` | Resume inbox tasks — briefing + spawn task workers | memory |
| `project-status` | Maintain machine-readable PROJECT.md status snapshots | memory |

## Coordination Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `swarm` | Portfolio-wide PD dispatch — parallel one-shot status/blocker/priority check | coordination |
| `delegate` | Snapshot context and hand off to a specialized subagent end-to-end | coordination |
| `pd-spawn` | Spawn another PD to do work on your behalf — inter-PD task protocol | coordination |
| `task-handoff` | Tier-A agent handoff — task store as the coordination layer, not conversation | coordination |
| `task-store` | SQLite-backed task store for multi-agent pipeline state tracking | coordination |
| `room-manager` | Poll agency rooms, route escalations, fan out PD statuses, send digests | coordination |
| `room-manager-digest` | Generate 12-hour dept head digests from rolling.md feeds | coordination |

## Planning Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `autoplan` | Auto-review pipeline (CEO → design → eng) | planning |
| `plan-ceo-review` | CEO/founder-mode plan review | planning |
| `plan-eng-review` | Engineering plan review | planning |
| `plan-design-review` | Designer's-eye plan review | planning |
| `office-hours` | YC-style product framing | planning |
| `retro` | Structured retrospective — git history, patterns, wins/losses, velocity | planning |
| `project-expansion-scout` | Autonomous strategic growth agent — scan projects for expansion, BOD approval | planning |

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

## Ops Skills

| Skill | Description | Category |
|-------|-------------|----------|
| `self-healing` | Diagnose and fix broken workflows — structured diagnostic loop, escalation after 2 attempts | ops |
| `investigate` | Systematic root-cause debugging | ops |
| `guard` | Safety mode — destructive warnings + edit freeze | ops |

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

## Using Skills

In Claude Code, invoke any skill with:

```
/skill-name
```

Or combine with context:

```
/autoplan
/pd-resume all
/pd-resume [slug]
/save-state
/save-state [slug]
/save-state all
/swarm
/swarm-blocker
/unwrap all
/wrap
```

## Creating a Skill

See `core/agents/` for the full developer guide.

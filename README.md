# The Agency

**Claude Code, fixed for everyone.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)
![Cloud: Zero dependencies](https://img.shields.io/badge/Cloud-Zero%20Dependencies-green)
![QA: Gates on every handoff](https://img.shields.io/badge/QA-Gates%20%2B%20Health%20Scores-red)

Out of the box, Claude Code forgets everything when a session ends. Long tasks stall halfway, or come back marked "done" with nothing to prove it. And every new session burns tokens rebuilding context it already had. The Agency fixes those pains with plain files installed to `~/.claude/`:

- **Memory that survives sessions.** `/save-state` before you close, `/recall` when you come back. Open tasks, decisions, and blockers return with it.
- **Agents that finish what they start.** A Project Director breaks the work down, hands it to specialists, and owns it until it is delivered.
- **QA gates before "done".** No handoff is accepted without a health-score pass and evidence.
- **Token-lean routing.** Cheap lookups before expensive agent spawns, and the right model for each job: Opus plans, Sonnet executes, Haiku does bulk work.

Skills and agents as plain files. No cloud, no extra API keys.

```bash
agency init                   # full quality gates
```

---

## Install in 60 Seconds

```bash
# Clone anywhere except ~/.claude (that folder already exists if you use Claude Code)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency

# macOS / Linux
bash install.sh

# Windows (PowerShell)
.\install.ps1
```

That's it. The skills and agents are synced into your Claude Code config directory (`~/.claude/` by default), and the `agency` command is added to your PATH. Open Claude Code and they're ready. The installer prints a `Sync root:` line naming the directory it used. Keep the clone: `agency upgrade` pulls it and re-syncs.

```bash
agency onboard                        # Interactive setup wizard (start here)
agency new my-app "Build a task manager"
# In Claude Code: /recall my-app
```

**Already cloned but haven't set up?** Run this from inside the repo:

```bash
node cli/bin/agency.js init      # installs skills, agents, CLI link
agency onboard                   # guided tour + first project
```

The PD loads and asks what to build. You supervise; it executes.

**Stuck? `agency upgrade` failing? Don't have the repo?** Run this one-liner from anywhere:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

It finds your existing clone (checks your agency root, then `~/.claude/` and `~/the-agency/`), pulls the latest, and recovers from broken states. If you don't have the repo yet, it clones it to `~/the-agency/` (never into `~/.claude/`, which already exists if you use Claude Code) and tells you to run the installer. If `~/the-agency/` already holds something else, it leaves it alone and prints the `git clone` command for a different folder.

---

## What The Agency Does

Four things make it different from a conversation with an AI:

**1. Memory that persists.** You run `/save-state` before you close Claude Code. Tomorrow you run `/recall`. The agent picks up exactly where it left off — open tasks, decisions made, what was blocked, what shipped. No re-explaining. No context collapse.

**2. A real team structure.** Work routes PD → Coord → Exec. A Project Director owns the project, a Coord owns one gated task, and an Exec is a `general-purpose` agent with one to three named skills. Critics (`critique-*`) review the result. The right route is picked for you.

**3. Autonomous coordination.** You give direction to a Project Director. The PD decomposes the work, assigns it to specialists, runs the tasks in parallel, checks the output at every handoff, and reports back. You don't coordinate. You supervise.

**4. Intelligent model routing.** Agents carry a model assignment. Planning and orchestration work goes to Opus. Execution work goes to Sonnet. High-volume research and scraping goes to Haiku. You get the right model for every task without thinking about it.

---

## See It In Action

### Scenario A: Work that survives the night

```
You:  /recall my-saas-app
PD:   Phase 2 in progress. Auth complete. Dashboard 60% done.
      2 blockers logged. Continuing now.

// 3 hours of work happens — you check in occasionally

You:  /save-state
PD:   State saved. Next session: finish dashboard, start billing.

// You close your laptop. Come back tomorrow.

You:  /recall my-saas-app
PD:   Dashboard complete. Billing ready to start. 
      Spawning payment specialist now.
```

You didn't explain anything the second day. The agent remembered.

- **4-tier autonomous chain**: PD → Coord → Mini-Coord → Exec (general-purpose + Skills) decomposes any project to atomic units. Mini-Coords keep drilling L6→L7→L8 without escalating to PD.
- **QA gates on every handoff**: No work gets ACK'd without a health-score pass. Gate: score ≥ 70 + zero CRITICALs. Example: 70 = tests pass but docs missing; 90+ = ship-ready.
- **Explicit ACK/NACK protocol**: An agent's report lands when it stops. If it is not re-spawned, that is the ACK. A NACK spawns a fresh continuation agent with the fix list, and the rework loops back through QA. Consent for a permission-gated action is a file the main session writes under `{project}/memory/tasks/revisions/acks/`, never chat prose.
- **Hook lifecycle system**: shell scripts across 4 lifecycle events (SessionStart, PreToolUse, PostToolUse, Stop) — security gating, secret scanning, config protection, stall and crash detection, cost tracking. Profile-aware (`standard` / `strict` / `minimal`). See [docs/HOOKS.md](docs/HOOKS.md).
- **Production-ready skills**: Memory, execution, QA, engineering, deployment, design, content, video, and more — all invoked via `/skill-name`.
- **SQLite task store — nothing leaves your machine**: Task pipeline, gates, retries, blocking in `~/.claude/`. No servers. No API keys.
- **Session persistence**: `/save-state` and `/recall` make Claude Code fully resume-capable. Come back days later; the PD shows you exactly where it left off.
- **Inter-PD Protocol** — PDs coordinate via filesystem, not messaging. Delegation through `inter-spawn-tasks/` directories with completion tracking.
- **Delegator Agent** — routing-as-a-service. When the right route is not obvious, an agent spawns the Delegator; it reads the agency catalog and returns the route. Worker roles run as `general-purpose` plus 1-3 skills. No hardcoded selection hierarchies.
- **Direct memory lookups** — project knowledge is looked up in order: your memory files (`MEMORY.md` index, project memory), then a shared-memory MCP server if you run one, then NotebookLM for research topics. A question that spans several sources is one read-only `general-purpose` spawn. No retrieval agent sits in between.
- **PD → Coord → Exec routing** — a Project Director decomposes, a Coord owns one task, an Exec (`general-purpose` plus 1-3 named skills) does the work, and critics review it. Quality gates sit on every handoff.
- **Agency Council** — one seat per Claude model tier plus an optional Codex seat, asked the same question in one wave. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#agency-council).
- **PD Boot Sequence** — lazy-loading spawn targeting <500 tokens. Per-project PD-BRIEFING.md for instant routing.
- **Status Loop Prohibition** — no automated ping loops. On-demand status via append-only `pd-status-live.md`.
- **Project Scope Management** — `scope.json` per project with 3-tier authority model (PD self-approve → parent AI → human).

## Works With

The Agency runs natively in Claude Code: agents load from `~/.claude/agents/`.

---
## Contributing

Two ways to extend the system:

**New agents** — the roster is structural only (PD, Coord, critics, council seats, service agents); domain work is a general-purpose agent plus skills, so most contributions are skills. If you do need a structural agent, follow the frontmatter of the existing files in `agents/` and see [docs/DEVELOPER.md](docs/DEVELOPER.md).

**New skills** — create a markdown file in `skills/`, register it in `skills/INDEX.md`, and invoke it with `/skill-name`. Skills are reusable workflows: a skill can call other skills, spawn agents, or chain multi-stage pipelines. Contributors also add an overlay entry for the new skill (`python3 scripts/skill-route-overlay-add.py <name> [--domain D --hint H]`); CI's skill-router menu gate fails without it. Users who enable the optional skill router need an entry for their own skills too, to make them routable. See [docs/DEVELOPER.md](docs/DEVELOPER.md) for the full guide.

---
## Docs

| Guide | What it covers |
|-------|----------------|
| [User Guide](docs/GUIDE.md) | Install, quick start, and an end-to-end walkthrough from clone to shipped feature |
| [Setup](docs/SETUP.md) | Prerequisites, upgrades, optional integrations, troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | The agent chain, QA gates, memory, NEXUS, routing, model tiers, council, scope |
| [Skills](docs/SKILLS.md) | Skill catalog by domain, pipelines, the optional skill router, the effort policy |
| [Hooks](docs/HOOKS.md) | Every lifecycle hook, profiles, settings wiring, helper scripts |
| [Mods](docs/MODS.md) | The five optional Claude Code mods |
| [Developer Guide](docs/DEVELOPER.md) | Repo layout, adding skills and agents, removing shipped files, testing |
| [Install Layout](docs/INSTALL-LAYOUT.md) | What each installer deploys and where the root comes from |

---

## Credits

Not everything here was made by one person. The memory design is inspired by Andrej Karpathy's LLM Wiki, the token-saving mode builds on the caveman and ponytail plugins, and many skills started as other people's open-source work. [CREDITS.md](CREDITS.md) names each source, its author and licence, and what we use it for.

---

**GitHub:** [https://github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency)

**License:** MIT — use it however you want.

**Credits:** the early agent catalog and its tooling derive from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT).

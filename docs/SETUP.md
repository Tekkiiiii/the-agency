# Quick Setup

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Node.js 18+ (for agency CLI)
- Git

## 1. Clone the repo

```bash
git clone https://github.com/the-agency/the-agency.git
cd the-agency
```

## 2. Install

```bash
agency init
```

Creates directories, installs all skills + agent templates, sets up the task store,
and links the `agency` CLI to your PATH.

## 3. Get oriented (optional)

```bash
agency onboard
```

Guided introduction — walks you through creating your first project and agent.
Requires `agency init` to have been run first.

## 4. Start a project

```bash
agency new my-project "Build a task manager app"
```

This creates the project structure and registers it with the agency. Skip this step
if you used `agency onboard` — it already created a project for you.

## 5. Spawn your first agent

In Claude Code:

```
/recall my-project
```

Or start fresh:

```
I'm starting a new project. Use the agency system.
Project: my-project
Goal: Build a task manager app with React and Supabase.
```

## 6. Install individual skills (optional)

`agency init` installs all bundled skills automatically. Use `agency skill install`
only if you want to install a skill that was added after your initial setup:

```bash
agency skill install save-state   # install a specific skill by name
agency skill list                 # see what is installed
```

Running `agency init` again re-syncs all skills without losing existing ones.

## 7. Create PD-BRIEFING.md for each project

For each project, create a per-project routing doc using the template in
`core/runbooks/pd-boot-sequence.md`. Place it at:

```
{project-root}/.claude/PD-BRIEFING.md
```

This file is the first thing a PD reads on spawn (~500 tokens) and contains
pre-written routing entries so the PD can delegate without loading the full agent catalog.

## 8. Initialize agency-rooms

```bash
mkdir -p ~/.claude/agency-rooms/project-oversight/handoffs
mkdir -p ~/.claude/agency-rooms/project-oversight/context
touch ~/.claude/agency-rooms/project-oversight/messages.mdl
touch ~/.claude/agency-rooms/project-oversight/context/shared.md
touch ~/.claude/agency-rooms/project-oversight/context/rolling.md
```

Create a room for each active project and department as needed. See `docs/ROOMS.md`
for the full directory structure and setup instructions.

## 9. Enable graphify knowledge-graph MCP (optional)

graphify builds a per-project knowledge graph that the Curator agent queries for project context.
It is optional but strongly recommended — without it, Curator falls back to raw file reads.

```bash
bash ~/.claude/scripts/setup-graphify.sh
```

Or, if you cloned the-agency to `~/.claude/`:

```bash
bash ~/.claude/scripts/setup-graphify.sh
```

**Package name gotcha:** the PyPI package is `graphifyy` (double-y). `uv tool install graphify`
(single-y) fails silently. The script handles this correctly — do not install manually.

The script is idempotent — safe to run again after upgrades:

```bash
bash ~/.claude/scripts/setup-graphify.sh --upgrade   # also bumps graphifyy to latest
```

After running, restart your Claude Code session. Graph data populates automatically via
`/save-state` Step 11b (per-project graph build + merge into unified).

## 10. Bootstrap a new machine (optional)

For full machine setup — all uv tools, CLI tools, and MCP servers in one pass:

```bash
bash ~/.claude/scripts/bootstrap-machine.sh
```

This covers three layers:

- **Layer 1 (uv tools):** graphifyy, notebooklm-mcp-cli, blue, browser-harness, nano-pdf
- **Layer 2 (CLI tools):** gws, lightpanda, markitdown, hermes
- **Layer 3 (MCP servers):** graphify, notebooklm-mcp, railway-mcp-server, stitch

All registered with `-s user` scope so they load from any working directory.

Pass `--upgrade` to also upgrade installed tools. Pass `--dry-run` to preview
without making changes.

After running, complete the **manual auth checklist** printed at the end of the
script (nlm login, gws auth login, railway login — these require OAuth flows that
cannot be scripted).

## 11. Context Window Budget (MCP-heavy setups)

MCP tool schemas are the dominant session-startup cost in MCP-heavy setups — many
servers × many tools each adds up to a large fixed token overhead before any real
work happens.

Claude Code's fix is **MCP tool search** (deferred schema loading): only tool names
and server instructions load at session start; full schemas fetch on demand via a
ToolSearch call. Enabled by default — but silently disabled by any `ANTHROPIC_BASE_URL`
proxy setting, unless you explicitly set `ENABLE_TOOL_SEARCH` in the `env` block of
`~/.claude/settings.json`:

```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "true"
  }
}
```

Recognized values:

| Value | Behavior |
|-------|----------|
| unset | Deferred by default, but has proxy/platform fallbacks that can silently disable it |
| `true` | Always defer — forces the beta header through proxies |
| `auto` / `auto:N` | Threshold mode — upfront load only if schemas fit within N% of the context window (default 10%) |
| `false` | Always upfront |

Caveats:

- Tool search requires `tool_reference`-capable models — Haiku models don't support it.
- Disabled by default on Google Cloud Agent Platform.
- Claude Code truncates tool descriptions and MCP server instructions at 2KB each —
  keep custom MCP server descriptions lean.
- `claude.ai` connectors can only be disabled all-or-nothing below managed-settings
  scope (`disableClaudeAiConnectors: true` kills all of them at once — there's no
  per-connector user-level denial), and they only load when subscription auth is
  active in the first place (not with API-key/Bedrock/Vertex auth).

Scope MCP servers to the project directories that actually use them, not the
home/root directory every session starts in — home-scoped servers load their full
schema in every single session regardless of relevance.

Advisory: if your setup ever routes through a result-compressing/rewriting proxy,
be aware such proxies have been observed to occasionally mangle or drop tool-result
data in addition to disabling tool search — verify carefully if debugging looks
weird under a proxy.

## What you get

```
~/.claude/
├── task-store.db        # Your task pipeline
├── projects/           # Project states
├── sessions/           # Session logs
├── lessons/           # Lessons learned
└── skills/             # Your skills
```

## First project in 5 minutes

1. `agency new my-project "My first project"`
2. In Claude Code: `/recall my-project`
3. Tell the PD what to build
4. PD creates tasks, spawns specialists
5. Specialists report back, PD gates completed work
6. `/save-state` at end of session

## Troubleshooting

**agency: command not found**
```bash
npm install -g @the-agency/cli
```

**Task store locked**
```bash
sqlite3 ~/.claude/task-store.db "PRAGMA busy_timeout=5000;"
```

**Skills not loading**
Check `~/.claude/skills/INDEX.md` exists. If not, run `agency init` again.

## Next Steps

- [Architecture](ARCHITECTURE.md) — understand how it all fits together
- [Skills Guide](SKILLS.md) — how to install and use skills
- [Developer Guide](DEVELOPER.md) — extending the system

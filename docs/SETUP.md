# Quick Setup

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Node.js 18+ (for agency CLI)
- Git

## 1. Clone the repo

Clone it **next to** your Claude Code config, not into it. `~/.claude` already exists
for anyone who has used Claude Code, so `git clone ... ~/.claude` fails there.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency
```

## 2. Install

```bash
bash install.sh      # macOS / Linux
.\install.ps1        # Windows (PowerShell)
```

The installer syncs skills, agents, hooks and core docs from the clone into your Claude
Code root and links the `agency` CLI to your PATH. The root is `$AGENCY_HOME` if set,
else `$CLAUDE_CONFIG_DIR`, else `~/.claude`; the installer prints a `Sync root:` line
saying which one it picked, so check it names your real config directory. Skills,
agents and memory the agency does not ship are left alone, and the agency hooks are merged into
`settings.json` without touching hooks you already have (a backup is written next to
it). Keep the clone: `agency upgrade` pulls it and re-syncs.

No bash or PowerShell? `node cli/bin/agency.js init` does the same sync from Node.

### Mods

After the sync, the installer wires the five Claude Code mods in `mods/` (context band, agent context alerts, loop guard, spawn ledger, voice compact). It copies each to `{root}/mods/<name>/` and adds it to `env.CLAUDE_CODE_PLUGIN_DIRS` in your user `settings.json`, after whatever value you already had. A mod whose name one of your entries already provides is skipped (yours wins), and so is a `{root}/mods/<name>/` that exists and is not ours. Mods need Claude Code 2.1.287 or newer; with an older version, or no `claude` command, the step is skipped with one line (`Mods: skipped (needs Claude Code 2.1.287+, found <v|none>). After updating: agency mods sync`). `install.sh` also installs `hooks/lib/*.py` and `*.json` (`model-pin.py`, `exec-model-map.json`, `claude_pricing.py`), which the `spawn-ledger` mod calls. Restart Claude Code afterwards.

- Opt out of the automatic step: `AGENCY_NO_MODS=1 bash install.sh` (same variable for `install.ps1`, `agency init` and `agency upgrade`).
- `agency mods sync` wires them later (ignores `AGENCY_NO_MODS`), `agency mods status` shows what is wired, `agency mods remove` removes exactly our entries and the folders we copied and restores your own value.
- The shell hooks `loop-detector` and `artifact-verify` stay wired next to the `loop-guard` and `spawn-ledger` mods for now, so you can see duplicate warnings; [mods/README.md](../mods/README.md) explains how to run one of each pair.

### Retired files

The sync only adds and updates files, so a skill, agent, runbook or core doc that the repo later deleted would stay on your disk forever. The installers, `agency init` and `agency upgrade` therefore also prune them, using `retired-manifest.json` (every path the repo once shipped and removed, with the checksum of every version it shipped):

- An installed retired file that is byte-for-byte a shipped version is deleted, and its folder if that leaves it empty.
- A retired file you edited is listed under "You changed these". Then it is archived to `{root}/archive/agency-retired-<YYYY-MM-DD>/` or deleted, per `--retired=archive|delete|ask` (`install.ps1`: `-Retired`; or the `AGENCY_RETIRED` environment variable). The default is `ask` on a terminal and `archive` without one (`curl | bash`, CI, an agent), so an edited file is never deleted unless you say `delete`. The note is also written to `{root}/logs/agency-retired.log`.
- A path that is not in the manifest is never touched, so your own skills and agents are safe.
- It refuses the repo checkout itself and skips a root that is a git work tree; `agency prune --force` applies it there anyway.

The summary line reads `Retired files: N removed, M archived (modified)`. Preview or run it on demand:

```bash
agency prune --dry-run                 # show what would be removed or archived
agency prune --retired=delete          # also delete edited files, no prompt
agency prune --force                   # apply to a root that is a git work tree
```

### Upgrade

```bash
agency upgrade
```

Pulls the clone, then repeats the sync, the hooks merge, the mods step and the retired-files prune above. The same opt-outs apply: `AGENCY_NO_MODS=1` and `--retired=` / `AGENCY_RETIRED`.

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

Create a room for each active project as needed. See `docs/ROOMS.md`
for the full directory structure and setup instructions.

## 9. Enable graphify knowledge-graph MCP (optional)

graphify builds a per-project knowledge graph that the Curator agent queries for project context.
It is optional but strongly recommended — without it, Curator falls back to raw file reads.

```bash
bash ~/.claude/scripts/setup-graphify.sh
```

The installer copies `scripts/` into your root, so this path works wherever you
cloned the repo. With a custom root, use `$AGENCY_HOME/scripts/setup-graphify.sh`.

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
4. PD creates tasks, spawns Coords and Execs (workers are `general-purpose` + skills)
5. Their reports land as each agent stops, and the PD gates completed work
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

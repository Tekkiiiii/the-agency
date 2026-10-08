# Agency CLI

The command-line tool for interacting with The Agency system.

## Installation

```bash
npm install -g @the-agency/cli
```

Or use without installing:

```bash
npx @the-agency/cli init
```

## Commands

### `agency init`

Initialize the agency system. Creates `~/.claude/`.

```bash
agency init
```

### `agency new <project> "<description>"`

Create a new project.

```bash
agency new my-app "Build a task manager"
```

### `agency status`

Show all projects and their current state.

```bash
agency status
```

### `agency tasks <project>`

List tasks for a project.

```bash
agency tasks my-app
```

### `agency task <id> --gate passed`

Gate a task.

```bash
agency task abc123 --gate passed
```

### `agency skill install <name>`

Install a skill.

```bash
agency skill install save-state
```

### `agency skill list`

List available skills.

```bash
agency skill list
```

### `agency upgrade`

Upgrade the agency system. Preserves all user data. After syncing the hook
scripts it also wires any new or changed hooks into `settings.json` (same merge
as `agency hooks sync`) and tells you to restart Claude Code when something
changed. Set `AGENCY_NO_HOOKS=1` to skip the wiring.

```bash
agency upgrade
```

### `agency hooks sync` / `agency hooks remove`

Wire the hooks listed in `hooks/hooks.json` into `<agency-root>/settings.json`,
or unwire them. Your own hooks and every other key in `settings.json` are left
as they are; only entries the agency owns are added, updated or removed. Before
any change the previous file is copied to `settings.json.bak-YYYYMMDD-HHMMSS`
next to it. Running it again when nothing changed writes nothing. Restart
Claude Code afterwards. See `docs/HOOKS.md`.

```bash
agency hooks sync
agency hooks remove
```

`agency hooks sync` works even with `AGENCY_NO_HOOKS=1` set (that variable only
turns off the automatic wiring in the installers, `agency init` and
`agency upgrade`). Without the `agency` command on PATH:

```bash
node <repo>/cli/lib/hooks-merge.js sync --root "<agency-root>"
```

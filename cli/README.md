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

Initialize the agency system. Creates `~/.agency/`.

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

Upgrade the agency system. Preserves all user data.

```bash
agency upgrade
```

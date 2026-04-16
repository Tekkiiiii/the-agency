---
name: guard
description: >
  Safety mode for risky operations — sets up guardrails before running
  dangerous commands: confirmation hooks, dry-run by default, abort on
  signals, and careful logging. Trigger when: about to run a destructive
  command (rm -rf, git push --force, database migration, service restart),
  operating in production, or any time the user wants an extra safety layer.
  Also for: setting up safety defaults for a whole session (guard mode stays
  active until explicitly disabled), and pre-flight checks before risky
  deploys. Not for: routine development work — use only when the stakes are high.
---

# /guard — Safety Mode for Risky Operations

Safety mode that sets up guardrails before dangerous operations.

## When to Activate

Trigger `/guard` when:
- About to run destructive commands (rm -rf, git push --force, database migration)
- Operating in production
- Running a risky deploy
- User wants an extra safety layer

Also available as a prefix: `/guard <command>` — wraps a single command in safety mode.

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **One-shot** | `/guard <cmd>` | Wraps single command, then exits |
| **Session** | `/guard` (no command) | Activates session guard mode |

## One-Shot Mode

Wrap a single dangerous command:
```
/guard rm -rf node_modules/
```

The skill will:
1. Show exactly what will be executed
2. Explain the risk
3. Require explicit confirmation before running
4. Offer a dry-run alternative if available
5. Log the execution

### Confirmation Prompt

```
⚠️ SAFETY GATE — DESTRUCTIVE COMMAND
═══════════════════════════════════

Command:   rm -rf node_modules/
Risk:      DELETES node_modules/ directory — cannot be undone
Recovery: Run npm install to restore

Type CONFIRM to proceed: _
```

## Session Guard Mode

When run without a command, activates session guard mode:
- All destructive commands require explicit confirmation
- Dry-run is shown before execution by default
- All operations are logged to `.gstack/guard-log.jsonl`
- Safety hooks fire before any `rm`, `git push --force`, `docker rm`, etc.

### Safety Hooks

**Before any shell command, check:**
- Does the command contain `rm -rf` or `rm -fr`?
- Does it contain `git push --force`?
- Does it target a production system?
- Does it modify a database directly?

If any match:
1. Stop execution
2. Show what was about to run
3. Ask for confirmation
4. Log the decision

### Guard Status

```
GUARD MODE: ACTIVE
═══════════════════════════
Destructive commands: CONFIRM required
Dry-run by default:  ON
Logging:             .gstack/guard-log.jsonl
Hooks active:        rm, rm -rf, git push --force, docker rm

To disable: /guard --off
To run without guard: run the command directly
```

## Pre-Flight Checks

Before any flagged command, run these checks:

**For git operations:**
```bash
git status
git log --oneline -3
git branch
```

Show the user exactly what will change before any destructive operation.

**For rm operations:**
```bash
ls {path}  # confirm what's about to be deleted
du -sh {path}  # show size
```

**For deploy operations:**
```bash
git log --oneline -5
gh run list --limit 3
```

## Dry Run Mode

By default, show what WOULD happen without doing it:

```bash
# Instead of:
rm -rf node_modules/

# Show:
echo "Would execute: rm -rf node_modules/"
echo "Would delete:"
ls node_modules/ 2>/dev/null || echo "(directory exists)"
echo "Recovery: npm install"
```

## Logging

All guard-mode operations are logged:
```json
{"ts":"ISO","command":"rm -rf node_modules/","confirmed":true,"dry_run":false,"session":"session-id"}
```

## Disabling Guard Mode

```
/guard --off
```

Disables all safety hooks for the current session. Only use when you're
certain the next commands are safe and you need to work without friction.

## Important Rules

- **Confirm before destruction.** Never auto-proceed on destructive commands.
- **Explain the risk.** Tell the user why this is flagged and what the recovery path is.
- **Dry-run first.** Show what will happen before it happens.
- **Log everything.** The guard log is the safety net.
- **Guard mode is a seatbelt, not a cage.** Disable it when you need to move fast and you're certain it's safe.
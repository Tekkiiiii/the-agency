# Hook System

The Agency ships a lifecycle hook system that runs shell scripts at key Claude Code events. Hooks are installed at `~/.claude/hooks/` and wired into `~/.claude/settings.json` by `agency init`.

This is a significant security and observability upgrade over a bare Claude Code install: 2 → 11 hooks across 4 lifecycle events.

---

## Hook Map

| Script | Event | Trigger | Purpose |
|--------|-------|---------|---------|
| `startup-sync.sh` | SessionStart | always | Auto-pull `~/.claude` config from GitHub on session open |
| `check-settings-secrets.sh` | SessionStart | always | Warn if `settings.json` has plaintext tokens in MCP env blocks |
| `check-session-state.sh` | SessionStart | always | Detect unclean prior exit (crash / Ctrl+C) |
| `gate-guard.sh` | PreToolUse | Edit, Write | Gate writes to sensitive files (settings, agents, hooks, SKILL.md) |
| `spawn-gate.sh` | PreToolUse | Agent | Enforce Delegator-first dispatch — block non-allowlisted subagent_type spawns that lack Delegator consultation |
| `secret-scanner.sh` | PreToolUse | Bash | Scan shell commands for credential-looking patterns |
| `config-protection.sh` | PreToolUse | Edit, Write | Block modification of existing linter/formatter configs |
| `track-edits.sh` | PostToolUse | Edit, Write | Buffer edited file paths for batch checking at session end |
| `loop-detector.sh` | PostToolUse | all tools | Detect stall loops — 5 identical tool calls in a row triggers warning + stall marker |
| `session-end.sh` | Stop | always | Mark session as cleanly ended (idempotent) |
| `batch-check.sh` | Stop | always | Run typecheck + shellcheck on files edited this session |
| `cost-tracker.sh` | Stop | always | Compute token usage and estimated cost; append to `~/.claude/metrics/costs.jsonl` |

---

## Settings Wiring

After `agency init`, your `~/.claude/settings.json` contains:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash ~/.claude/hooks/gate-guard.sh" },
          { "type": "command", "command": "bash ~/.claude/hooks/config-protection.sh" }
        ]
      },
      {
        "matcher": "Agent",
        "hooks": [
          { "type": "command", "command": "~/.agency/hooks/spawn-gate.sh" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "bash ~/.claude/hooks/secret-scanner.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash ~/.claude/hooks/track-edits.sh" }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "bash ~/.claude/hooks/loop-detector.sh" }
        ]
      }
    ],
    "SessionStart": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/startup-sync.sh" }] },
      { "matcher": "", "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/check-settings-secrets.sh" }] },
      { "matcher": "", "hooks": [{ "type": "command", "command": "bash ~/.claude/hooks/check-session-state.sh" }] }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/session-end.sh && bash ~/.claude/hooks/batch-check.sh && bash ~/.claude/hooks/cost-tracker.sh"
          }
        ]
      }
    ]
  }
}
```

---

## Profile System

Each hook reads `~/.claude/.hook-profile` at runtime. The profile controls behavior without touching `settings.json`.

| Profile | Behavior |
|---------|----------|
| `standard` (default) | Gate-guard and secret-scanner issue warnings (`"permissionDecision":"ask"`) |
| `strict` | Gate-guard and secret-scanner block writes (`"permissionDecision":"deny"`) |
| `minimal` | Gate-guard, secret-scanner, config-protection, and batch-check are all disabled |

To switch profiles:

```bash
echo "strict" > ~/.claude/.hook-profile     # block on any warning
echo "minimal" > ~/.claude/.hook-profile    # disable all safety hooks
echo "standard" > ~/.claude/.hook-profile   # restore default
```

The template `hooks/.hook-profile.template` ships `standard` as the default.

---

## Hook Details

### startup-sync.sh (SessionStart)

Runs `git fetch` on `~/.claude`, then fast-forward pulls if the remote is ahead. On divergence (local commits ahead of remote), stashes local changes, pulls, and pops the stash. Non-destructive. 5-second timeout.

**Effect:** Every new Claude Code session automatically picks up the latest agents, skills, and hooks from your remote.

### check-settings-secrets.sh (SessionStart)

Scans `mcpServers.*.env` values in `settings.json` for JWT-shaped tokens (≥50-char `eyJ…` strings) and long hex strings (≥48 chars). Prints a warning to stderr if any are found. Non-blocking.

### check-session-state.sh (SessionStart)

Reads `~/.claude/session-state.json`. If `was_clean` is `false`, the prior session ended without hitting the Stop hook (crash or Ctrl+C). Prints a notice suggesting `/recall` or `/save-state`. Sets `was_clean = false` for the current session; the Stop hook sets it back to `true`.

### gate-guard.sh (PreToolUse: Edit, Write)

Checks the target file path against four categories:
- `settings.json` / `settings.local.json`
- Agent definitions (`agents/*.md`)
- Hook scripts (`hooks/*.sh`)
- Skill entry points (`SKILL.md`)

Also scans write content for JWT/API key patterns. Returns `permissionDecision: ask` (standard) or `deny` (strict) with a message. Returns `{}` (pass-through) if no match.

### spawn-gate.sh (PreToolUse: Agent)

Enforces the Delegator-first dispatch rule. Every Agent tool call is intercepted; the hook decides whether the spawn is pre-approved or must demonstrate Delegator consultation.

**Allowlisted subagent_type values (exact match — pass through immediately):**

- `curator`
- `Delegator`
- `codebase-search`
- `Explore`
- `Plan`
- `general-purpose`
- `statusline-setup`
- `pd-coordinator`
- `coord`
- `mini-coord`
- `task-executor`

**PD spawn prefix detection:** If the agent `prompt` starts with `You are PD-`, the spawn is unconditionally allowed. This covers PD boot sequences triggered by `/pd-spawn` and `/pd-resume`.

**DELEGATOR ROUTING compliance marker:** If the prompt contains the string `DELEGATOR ROUTING`, the hook treats the spawn as compliant and passes through. The Delegator writes this block into the calling agent's context; well-behaved agents copy it into the downstream prompt.

**Block behavior:** Any spawn that does not match the allowlist, lacks the PD prefix, and contains no `DELEGATOR ROUTING` marker receives `permissionDecision: deny` with a message explaining the required workflow:

1. Spawn `Delegator` with a task description and project context.
2. Wait for its routing recommendation.
3. Include the recommendation block in the downstream agent prompt.

The deny message also lists all pre-approved subagent_type values and references `~/.agency/memory/agency-dispatch.md` Step 1.5 for the full allowlist.

Respects the `.hook-profile` system: in `minimal` profile, the hook exits immediately with `{}` (all spawns allowed).

### secret-scanner.sh (PreToolUse: Bash)

Scans the bash command string for known credential patterns: JWTs, GitHub tokens, Slack tokens, Google OAuth tokens, AWS access keys, and inline `API_KEY=…` assignments. Returns `ask` or `deny` with a tagged message.

### config-protection.sh (PreToolUse: Edit, Write)

If the target file is an existing linter/formatter config (ESLint, Prettier, Biome, Ruff, Shellcheck, Stylelint, Markdownlint), returns `deny`. Creation of new config files is allowed. The rule: fix the code, not the linter.

### track-edits.sh (PostToolUse: Edit, Write)

Appends the file path of every edited file to `~/.claude/.edit-buffer.txt`. This buffer is consumed by `batch-check.sh` at session end and cleared after reading.

### session-end.sh (Stop)

Writes `{"last_stop": "<timestamp>", "was_clean": true}` to `~/.claude/session-state.json`. Idempotent.

### batch-check.sh (Stop)

Reads `~/.claude/.edit-buffer.txt`, deduplicates, then:
- For TypeScript files: finds the nearest `tsconfig.json` and runs `tsc --noEmit --skipLibCheck`
- For shell scripts: runs `shellcheck -S warning` if shellcheck is on PATH

Clears the buffer after running. Skipped in `minimal` profile.

### loop-detector.sh (PostToolUse: all tools)

Tracks the last 10 tool calls in `~/.claude/.tool-call-tracker.jsonl`. If 5 identical tool+input signatures appear consecutively, prints a stall warning to stderr visible to the running agent and writes a `stall_detected` marker to `session-state.json`.

The warning instructs the agent to:
1. Restate its objective in one sentence
2. Verify the actual world state (read the file, check git status)
3. Try a different approach
4. If still blocked, `/save-state` and stop

Skipped in `minimal` profile. Clears the tracker file after detecting a stall to give one fresh chance.

**Effect:** Prevents runaway infinite loops from exhausting context or budget without any useful progress.

### cost-tracker.sh (Stop)

Reads the session transcript JSONL, sums token usage by type (input, output, cache_write, cache_read), maps to the correct model tier (haiku/sonnet/opus), computes estimated USD cost, and appends one JSONL row to `~/.claude/metrics/costs.jsonl`. Prints a summary line to stderr.

Cost rates used (per 1M tokens):

| Tier | Input | Output | Cache Write | Cache Read |
|------|-------|--------|-------------|------------|
| Haiku | $0.80 | $4.00 | $1.00 | $0.08 |
| Sonnet | $3.00 | $15.00 | $3.75 | $0.30 |
| Opus | $15.00 | $75.00 | $18.75 | $1.50 |

---

## Extending the Hook System

To add a new hook:

1. Write the script to `hooks/{name}.sh`
2. Add it to `~/.claude/settings.json` under the correct event
3. Make it profile-aware if it blocks or warns:
   ```bash
   PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
   if [ "$PROFILE" = "minimal" ]; then echo '{}'; exit 0; fi
   ```
4. Return `{}` for pass-through, or a JSON object with `permissionDecision` and `message` for PreToolUse hooks

To disable a single hook without removing it from settings, use the `minimal` profile or comment out the command in `settings.json`.

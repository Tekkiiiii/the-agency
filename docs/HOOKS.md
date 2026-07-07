# Hook System

The Agency ships a lifecycle hook system that runs shell scripts at key Claude Code events. Hooks are installed at `~/.claude/hooks/` and wired into `~/.claude/settings.json` by `agency init`.

This is a significant security and observability upgrade over a bare Claude Code install: 2 → 18 hooks across 5 lifecycle events, plus a statusLine badge hook and a set of shared helper scripts under `hooks/lib/` (sourced by other hooks, not registered as hooks themselves — see [Helper Scripts](#helper-scripts-hookslib) below).

---

## Hook Map

| Script | Event | Trigger | Purpose |
|--------|-------|---------|---------|
| `fable-on-opus.sh` | UserPromptSubmit | always (self-gates on model) | Inject Fable-style operating-discipline guidance (`hooks/fable/*.md`) when the active model is Opus-line |
| `startup-sync.sh` | SessionStart | always | Auto-pull `~/.claude` config from GitHub on session open |
| `check-settings-secrets.sh` | SessionStart | always | Warn if `settings.json` has plaintext tokens in MCP env blocks |
| `check-session-state.sh` | SessionStart | always | Detect unclean prior exit (crash / Ctrl+C) |
| `gate-guard.sh` | PreToolUse | Edit, Write | Gate writes to sensitive files (settings, agents, hooks, SKILL.md) |
| `spawn-gate.sh` | PreToolUse | Agent | Enforce Delegator-first dispatch — block non-allowlisted subagent_type spawns that lack Delegator/hardcoded-routing marker; also emits a `generalist_ban_violation` metric for banned `general-purpose`/`claude` spawns |
| `spawn-logger.sh` | PreToolUse | Agent | Log a `spawn_start` event for every agent spawn; injects a `[[CLAUDE_SPAWN_META]]` lineage marker into the child prompt |
| `secret-scanner.sh` | PreToolUse | Bash | Scan shell commands for credential-looking patterns |
| `config-protection.sh` | PreToolUse | Edit, Write | Block modification of existing linter/formatter configs |
| `track-edits.sh` | PostToolUse | Edit, Write | Buffer edited file paths for batch checking at session end |
| `write-evidence.sh` | PostToolUse | Write, Edit | Log a `write_evidence` event (path + byte count) for deliverable-shaped paths — paper trail against fabricated completions |
| `loop-detector.sh` | PostToolUse | all tools | Detect stall loops — 5 identical tool calls in a row triggers warning + stall marker |
| `artifact-verify.sh` | PostToolUse | Agent | Scan a completed agent's output for "done/complete" claims and verify the deliverable file paths it cites actually exist on disk |
| `spawn-completion.sh` | PostToolUse | Agent | Log a `spawn_end` event for every agent spawn completion (outcome, tokens, tool uses, duration) |
| `bg-job-warn.sh` | PostToolUse | Bash (`run_in_background`) | Track fire-and-forget background jobs; warn immediately when a render/build command is backgrounded |
| `session-end.sh` | Stop | always | Mark session as cleanly ended (idempotent) |
| `batch-check.sh` | Stop | always | Run typecheck + shellcheck on files edited this session |
| `cost-tracker.sh` | Stop | always | Compute token usage and estimated cost; append to `~/.claude/metrics/costs.jsonl` |
| `caveman-statusline.sh` | StatusLine | always | Render the `[CAVEMAN]` mode badge (+ optional token-savings suffix) in the terminal status line — wired via the `statusLine` settings key, not `hooks` |
| `emit-metric.sh` | — (utility) | called by other hooks / agents | Append one JSON event line (with a `ts` timestamp) to the shared metrics log; not itself registered under a lifecycle event |

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
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "bash ~/.claude/hooks/fable-on-opus.sh" }
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

### fable-on-opus.sh (UserPromptSubmit)

Reads the incoming prompt payload from stdin (`session_id`, `transcript_path`, `model`, `prompt`) and determines the active model in order: the hook's own `.model` field, then the last assistant-model entry in the transcript JSONL, then the `model` key in `settings.json`. If the resolved model is not Opus-line, it clears any per-session marker files for that session and exits — a no-op on every other model tier.

On an Opus-line model:

- **Once per session:** injects `hooks/fable/core.md` (the reasoning-engine + behavioral-layer discipline) via a per-session marker file in `$TMPDIR` (`fable-core-<session_id>`) so it's added exactly once, not on every prompt.
- **Keyword-routed, once each per session:** scans the prompt text against a keyword profile per task-type module (`visual`, `content`, `delegation`, `research`, `coding`, `planning`, `systems`, `security`, `efficiency`) and injects the matching module(s) from `hooks/fable/`. A prompt can match zero, one, or several modules.
- **Otherwise:** emits a one-line reminder that core discipline is already loaded and names the on-demand modules available in `hooks/fable/`.

Output is a `hookSpecificOutput.additionalContext` JSON block (the standard `UserPromptSubmit` hook contract) — never blocks the prompt. Requires `jq`; portable for macOS's bundled `/bin/bash` 3.2 (no bash-4-only syntax).

**Playbook inventory (`hooks/fable/`):**

| File | Covers |
|------|--------|
| `core.md` | Reasoning engine (intent reconstruction, hypothesis-first investigation, risk-ordered decomposition, epistemic ledger, blast-radius simulation) + behavioral layer (outcome-first replies, calibrated completion claims, one sharp question, pre-send checklist) |
| `visual.md` | UI, pages, slides, charts, images — render-and-judge discipline, hierarchy, design tokens, accessibility as correctness |
| `content.md` | Articles, posts, emails, scripts, teaching material — reader-first drafting, point-before-prose, slop removal |
| `coding.md` | Implementation, bugfixes, refactors, tests — read-before-write, root-cause fixes, leave-a-check-behind |
| `planning.md` | Implementation plans, proposals, roadmaps — plan from the end state, sequence by risk retirement |
| `delegation.md` | Spawning, briefing, verifying agents — self-contained briefings, independent decomposition, verify like an outsider |
| `research.md` | Comparisons, evaluations, investigations — source weighting, triangulation, confidence-leveled synthesis |
| `systems.md` | Workflows, pipelines, recurring problems — structure over instance, blast radius, leverage points |
| `security.md` | Auth, secrets, untrusted input, attacker modeling, operator hygiene (own credentials/environment/data) |
| `efficiency.md` | Bottlenecks, cost, tokens, performance — measure first, optimize the bottleneck, price every optimization |

Each module is self-contained; `core.md` is the only one injected unconditionally.

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

Enforces the Delegator-first dispatch rule. Every Agent tool call is intercepted; the hook decides whether the spawn is pre-approved or must demonstrate Delegator consultation (or a hardcoded-routing marker).

**Allowlisted subagent_type values (exact match — pass through immediately):**

- `pd-coordinator`
- `coord`
- `mini-coord`
- `task-executor`
- `curator`
- `codebase-search`
- `Delegator`
- `Explore`
- `Plan`
- `statusline-setup`

Note: `general-purpose` is **deliberately NOT** on this exact-match allowlist (the script comments this explicitly) — it is the most commonly misused spawn type, so it must still pass one of the marker checks below instead of being unconditionally waved through.

**PD spawn prefix detection:** If the agent `prompt` starts with `You are PD-`, the spawn is unconditionally allowed. This covers PD boot sequences triggered by `/pd-spawn` and `/pd-resume`.

**Routing markers (either satisfies the gate):**

- **`DELEGATOR ROUTING`** — the Delegator writes this block into the calling agent's context; well-behaved agents copy it into the downstream prompt.
- **`HARDCODED ROUTING:`** — a single-domain, unambiguous routing decision made without spawning the Delegator (e.g. `HARDCODED ROUTING: docs-sync-task → task-executor`). Intended for cases where the agent choice is obvious from the task type alone.

**Skill-spawn allowlist:** Prompts matching known mechanical skill-ownership patterns also pass through without a marker — e.g. prompts starting with `You own the save-state ritual`, `You own the cc-loop ritual`, `You are {name}, resuming work`, `You are resuming work on inbox task`, or containing the literal string `SKILL SPAWN:`. These cover structured skill subagents (save-state, pd-spawn, unwrap, etc.) that are spawned by skills rather than dispatched ad hoc by the parent AI.

**generalist_ban_violation metric emission (added post-eval-048):** Before the block/ask branch below runs, if `subagent_type` is exactly `general-purpose` or `claude`, the hook mechanically calls `hooks/emit-metric.sh` with `{"event":"generalist_ban_violation","subagent_type":"<type>"}` — resolving the script path relative to its own directory and guarding the call with `|| true` so it is non-blocking and best-effort (a missing/failing `emit-metric.sh` never delays or fails the gate). This fires regardless of whether the spawn is ultimately allowed by a marker further down — it is a mechanical tripwire on the banned-type check itself, not on the final deny decision.

**Block behavior:** Any spawn that does not match the allowlist, lacks the PD prefix, and contains no routing/skill marker receives `permissionDecision: ask` with a message explaining the two valid paths (hardcoded routing vs. Delegator routing) and listing all pre-approved subagent_type values. The message also references `{agency-root}/memory/agency-dispatch.md` Step 1.5 for the full routing protocol.

Respects the `.hook-profile` system: in `minimal` profile, the hook exits immediately with `{}` (all spawns allowed). Note this hook reads its profile flag from `~/.agency/.hook-profile` — other hooks in this set (e.g. `spawn-completion.sh`, `spawn-logger.sh`) read `~/.claude/.hook-profile` instead; verify which path applies to your install when troubleshooting profile behavior.

### spawn-logger.sh (PreToolUse: Agent)

Writes a `spawn_start` JSONL entry for every Agent tool call, then injects a `[[CLAUDE_SPAWN_META: spawn_id=X parent_id=Y]]` marker into the outgoing prompt so the child agent can read its own lineage (env-var propagation is unreliable across Claude Code sub-agent boundaries).

Resolves the target log file by longest-prefix-matching the current working directory against the Active Projects table in `~/.claude/memory/medium-term.md` (falls back to `~/.claude/logs/spawns.jsonl` if no project matches or the table doesn't exist). Any existing `[[CLAUDE_SPAWN_META: ...]]` marker already in the prompt is stripped before the new one is appended, so markers never stack across generations.

Respects the `.hook-profile` system: in `minimal` profile, exits immediately with `{}`. On any internal error, returns `{}` (pass-through, unmodified prompt) — spawns are never blocked by this hook.

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

### write-evidence.sh (PostToolUse: Write, Edit)

Logs a paper trail for deliverable writes. On every Write/Edit whose target path contains `/outputs/`, `/plans/`, `/reports/`, or `/qa/`, or ends in `.html`, `.htm`, `.pdf`, `.docx`, `.pptx`, or `.xlsx`, it stats the file post-write and appends a `write_evidence` entry (path, byte count, `exists` flag) to `~/.claude/logs/write-evidence.jsonl`. It also fire-and-forgets the same event to `~/.claude/memory/metrics/emit-metric.sh` (if present) so it's queryable alongside other metrics events.

**Effect:** pairs with `artifact-verify.sh` — if an agent claims a deliverable is DONE, there must be a corresponding `write_evidence` entry with non-zero bytes, or the fabrication guard has grounds to flag the claim.

Any internal error is silent; the hook never blocks a write.

### loop-detector.sh (PostToolUse: all tools)

Tracks the last 10 tool calls in `~/.claude/.tool-call-tracker.jsonl`. If 5 identical tool+input signatures appear consecutively, prints a stall warning to stderr visible to the running agent and writes a `stall_detected` marker to `session-state.json`.

The warning instructs the agent to:
1. Restate its objective in one sentence
2. Verify the actual world state (read the file, check git status)
3. Try a different approach
4. If still blocked, `/save-state` and stop

Skipped in `minimal` profile. Clears the tracker file after detecting a stall to give one fresh chance.

**Effect:** Prevents runaway infinite loops from exhausting context or budget without any useful progress.

### artifact-verify.sh (PostToolUse: Agent)

Harness-level backstop against fabricated "build complete" claims. After every Agent tool call returns, scans the completed agent's output text for a completion signal (`DONE`, `COMPLETE`, `BUILD COMPLETE`, `SUCCESS`, `FINISHED`, `SHIPPED`, etc.). If found, it extracts candidate deliverable file paths from the text (absolute paths, `~/`-relative paths, or paths near `out/`/`output/`/`dist/`/`build/`, matching extensions like `.mp4`, `.pdf`, `.html`, `.png`, `.zip`, `.json`, `.csv`, and similar) and runs `os.path.isfile()` on each resolvable one.

If any claimed file is missing on disk, it prints an `ARTIFACT_MISSING WARNING` to stderr (visible to the calling agent, listing both missing and found paths) instructing the agent not to relay the completion to the user, and logs a structured `ARTIFACT_MISSING` entry to `~/.claude/logs/artifact-verify.jsonl`. It fires even when the agent ignores prompt-level "verify before reporting done" instructions.

Any internal error is silent; the hook never blocks the agent.

### spawn-completion.sh (PostToolUse: Agent)

Appends a `spawn_end` JSONL entry for every completed agent spawn. Resolves the project-scoped log file via `hooks/lib/resolve-project.sh` (falls back to `~/.claude/logs/spawns.jsonl`), then matches the completion back to its `spawn_start` entry by `tool_use_id` (walking the log file backwards to find the corresponding `spawn-logger.sh` entry).

Parses the agent's output for an outcome (`DONE`, `BLOCKED`, `ESCALATE`, `KILLED`, or `UNKNOWN` — matched against markers like `STATUS: BLOCKED` or `— ESCALATE`) and for usage figures (tokens, tool uses, duration) from an `<usage>...</usage>` block in the response, with JSON-based fallbacks if that block is absent.

Respects the `.hook-profile` system: in `minimal` profile, exits immediately without logging. Any internal error is silent.

### bg-job-warn.sh (PostToolUse: Bash, `run_in_background`)

Tracks fire-and-forget background Bash jobs. On every Bash tool call made with `run_in_background: true`, appends an entry (command, description, extracted background job ID, `resolved: false`) to `~/.claude/.pending-bg-jobs.jsonl`.

If the backgrounded command matches a render/build signal (`render`, `ffmpeg`, `bun run`, `npm run build`, `make `, `cargo build`, `go build`), it immediately prints a warning to stderr instructing the agent that it **must** await the job and `test -f` the output before reporting DONE — it must not proceed to a summary until the artifact is verified on disk.

Any internal error is silent; the hook never blocks the Bash call.

### cost-tracker.sh (Stop)

Reads the session transcript JSONL, sums token usage by type (input, output, cache_write, cache_read), maps to the correct model tier (haiku/sonnet/opus), computes estimated USD cost, and appends one JSONL row to `~/.claude/metrics/costs.jsonl`. Prints a summary line to stderr.

Cost rates used (per 1M tokens):

| Tier | Input | Output | Cache Write | Cache Read |
|------|-------|--------|-------------|------------|
| Haiku | $0.80 | $4.00 | $1.00 | $0.08 |
| Sonnet | $3.00 | $15.00 | $3.75 | $0.30 |
| Opus | $15.00 | $75.00 | $18.75 | $1.50 |

### caveman-statusline.sh (StatusLine)

Not a lifecycle hook — wired via the `statusLine` key in `settings.json` (`"statusLine": {"type":"command","command":"bash .../caveman-statusline.sh"}`), not the `hooks` key. Runs on every statusline render (effectively every turn).

Reads the caveman-mode flag file (`~/.claude/.caveman-active` by default, respecting `$CLAUDE_CONFIG_DIR`) and renders a colored `[CAVEMAN]` badge, or `[CAVEMAN:<MODE>]` for a specific mode (`lite`, `full`, `ultra`, `wenyan-*`, `commit`, `review`, `compress`). Refuses to read the flag (or the optional token-savings suffix file) if either is a symlink, hard-caps reads at 64 bytes, and strips any byte outside `[a-z0-9-]` before rendering — hardening against a local attacker planting ANSI-escape or OSC-hyperlink injection payloads in either file. Unrecognized mode values render nothing rather than echoing attacker-controlled bytes.

Optionally appends a pre-rendered token-savings suffix (from `~/.claude/.caveman-statusline-suffix`, written by `/caveman-stats`) unless `CAVEMAN_STATUSLINE_SAVINGS=0` is set.

### emit-metric.sh (utility — not a registered lifecycle hook)

A shared one-line utility, not itself wired into `settings.json`. Other hooks (`spawn-gate.sh`, `write-evidence.sh`) and agents call it directly: `emit-metric.sh '{"event":"...", ...}'`. It appends the given JSON payload — with a `ts` (UTC ISO-8601) field added automatically — as one line to `~/.claude/memory/metrics/events.jsonl`.

Always exits 0 and never raises; if the input is missing or unparseable, it's a silent no-op.

`hooks/fable/` is the one other subdirectory under `hooks/` — it holds the Fable playbook modules read by `fable-on-opus.sh` above, not additional registered hooks. `install.sh` copies it explicitly, as a separate step from the generic `hooks/*.sh` glob it uses for flat hook scripts (that glob does not pick up `*.md` files or subdirectories). Note that hook installation currently happens only in `install.sh` — `agency init`/`agency upgrade` sync skills, agents, and core docs but do not currently sync `hooks/` at all; re-running `install.sh` is the only supported way to pick up new or updated hooks post-install.

---

## Helper Scripts (`hooks/lib/`)

`hooks/lib/` is **not** a set of directly-registered Claude Code hooks — none of these scripts appear in `settings.json`. They are shared bash/python helper scripts that other hooks and agents `source` or invoke directly to avoid duplicating logic (log-file resolution, spawn lineage IDs, context-percentage publishing). Think of this directory as the hook system's internal library, analogous to a `lib/` or `utils/` folder in an application codebase.

### resolve-project.sh

Defines a single function, `resolve_project_path`, meant to be `source`d (not executed) by callers: `source ~/.claude/hooks/lib/resolve-project.sh && resolve_project_path`. It reads the Active Projects table in `~/.claude/memory/medium-term.md`, expands each row's backtick-quoted path, and longest-prefix-matches it against the current working directory (`$CLAUDE_PROJECT_DIR` or `$PWD`). On a match it sets `SPAWN_LOG_FILE` to `{project_root}/memory/spawns.jsonl`; otherwise it falls back to `~/.claude/logs/spawns.jsonl`. Used by `spawn-completion.sh` and `spawn-gate.sh`-adjacent tooling to keep spawn logs project-scoped. This is the bash/sourced twin of the `resolve_log_file()` python helper duplicated inline inside `spawn-logger.sh`, `spawn-completion.sh`, and `log-spawn-from-agent.sh`.

### log-spawn-from-agent.sh

Called by a PD/Coord/Mini-Coord **before** each `Agent({...})` call it makes directly (i.e. agent-instrumented spawn logging, as a complement to the automatic `spawn-logger.sh` PreToolUse hook). Takes `--parent-agent`, `--child-subagent-type`, `--description`, and `--prompt-excerpt` flags, writes a `spawn_start` JSONL entry (tagged `"source": "agent-instrumented"`), and prints a freshly generated `spawn_id` (UUID) to stdout for the caller to capture and pass down to the child. On any internal failure it still prints a valid UUID so the caller is never blocked.

### log-spawn-end-from-agent.sh

The completion-side counterpart to `log-spawn-from-agent.sh`. Called by a PD/Coord/Mini-Coord **after** an `Agent({...})` call returns, with `--spawn-id`, `--outcome`, and `--summary` flags. Writes a `spawn_end` JSONL entry (tagged `"source": "agent-instrumented"`) for the given `spawn_id`. Silent no-op if `--spawn-id` is empty; any internal error is silently swallowed.

### context-pct-publish.sh

Reads the current context-window usage (from `$CLAUDE_CONTEXT_PCT`, or parsed out of `$CLAUDE_USAGE` JSON as a fallback) and publishes it to `~/.claude/state/context-pct.txt` as an integer 0-100, so agents can self-monitor their own context budget per the Self-Respawn Protocol. Emits a `CONTEXT_PCT_ALERT` to stderr at the 70% (warning — complete current task, no new L3s) and 80% (mandatory `/save-state` + `/respawn-self`) thresholds.

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

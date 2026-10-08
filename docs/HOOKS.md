# Hook System

The Agency ships a lifecycle hook system that runs shell scripts at key Claude Code events. Every install path — `install.sh`, `install.ps1`, `agency init` and `agency upgrade` — copies the scripts to `{agency-root}/hooks/` and then wires the hooks listed in [`hooks/hooks.json`](../hooks/hooks.json) into `{agency-root}/settings.json`, keeping every hook and key you added yourself. `agency hooks sync` and `agency hooks remove` do the same wiring on demand. See [Settings Wiring](#settings-wiring) below.

> **`{agency-root}`** = `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`.
> Every path in this document is written with the default (`~/.claude`) for
> readability. If you installed with a custom root, substitute it everywhere —
> the installers already write the resolved path into `settings.json` for you, and
> every hook resolves its own root via `hooks/lib/resolve-root.sh`. See
> [INSTALL-LAYOUT.md](INSTALL-LAYOUT.md#where-the-root-comes-from).

This is a significant security and observability upgrade over a bare Claude Code install: 2 → 18 hooks across 5 lifecycle events, plus a statusLine badge hook and a set of shared helper scripts under `hooks/lib/` (sourced by other hooks, not registered as hooks themselves — see [Helper Scripts](#helper-scripts-hookslib) below). Of those 18, 14 are wired into `settings.json` by every install and upgrade — they are the entries of `hooks/hooks.json` (see [Settings Wiring](#settings-wiring) below); the remaining 4 — telemetry/convenience hooks plus the deliberately-unregistered `fable-on-opus.sh` — ship on disk but are not registered until an operator adds them manually.

---

## Hook Map

| Script | Event | Trigger | Purpose |
|--------|-------|---------|---------|
| `fable-on-opus.sh` | UserPromptSubmit | ships unwired — opt-in; self-gates on model when wired | Inject Fable-style operating-discipline guidance (`hooks/fable/*.md`) when the active model is Opus-line |
| `startup-sync.sh` | SessionStart | always | Auto-pull the agency root's config from GitHub on session open |
| `check-settings-secrets.sh` | SessionStart | always | Warn if `settings.json` has plaintext tokens in MCP env blocks |
| `check-session-state.sh` | SessionStart | always | Detect unclean prior exit (crash / Ctrl+C) |
| `gate-guard.sh` | PreToolUse | Edit, Write | Gate writes to sensitive files (settings, agents, hooks, SKILL.md) |
| `spawn-gate.sh` | PreToolUse | Agent | Generalist-switch gate — `general-purpose` + structural agent types pass; an unknown `subagent_type` (typo or archived specialist name) gets an `ask` pointing to `agents-archive/ROLE-MAP.md` |
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
| `cost-tracker.sh` | Stop | always | Compute token usage and estimated cost (per-model rates from `hooks/lib/claude_pricing.py`); append to `costs.jsonl` in the `metrics/` folder of the agency root |
| `caveman-statusline.sh` | StatusLine | always | Render the `[CAVEMAN]` mode badge (+ optional token-savings suffix) in the terminal status line — wired via the `statusLine` settings key, not `hooks` |
| `emit-metric.sh` | — (utility) | called by other hooks / agents | Append one JSON event line (with a `ts` timestamp) to the shared metrics log; not itself registered under a lifecycle event |

---

## Settings Wiring

`hooks/hooks.json` is the single list of hooks The Agency wires. Each entry has an `id`, the Claude Code `event`, a `matcher` (`""` = every tool / always), the `command` with the agency root written as `{root}`, and a one-line `purpose`. `cli/lib/hooks-merge.js` merges that list into `{agency-root}/settings.json`. It runs:

- on every `install.sh` / `install.ps1` run (not only when `settings.json` is new — that was the old behaviour, and it left every existing Claude Code user with no agency hooks at all);
- on `agency init`, and on `agency upgrade` right after the hook scripts are synced;
- on demand: `agency hooks sync` (wire) and `agency hooks remove` (unwire). Without the `agency` command on PATH: `node <repo>/cli/lib/hooks-merge.js sync --root "<agency-root>"`.

These are the hooks it wires (the table is generated from `hooks/hooks.json`):

<!-- hooks-manifest:begin -->
<!-- Generated from hooks/hooks.json by `node .github/scripts/check-hooks-manifest.js --write`. Do not edit by hand: CI fails when it drifts. -->

| ID | Event | Matcher | Command | Purpose |
|----|-------|---------|---------|---------|
| `gate-guard` | PreToolUse | `Edit\|Write` | `bash {root}/hooks/gate-guard.sh` | Gate writes to sensitive files (settings, agents, hooks, SKILL.md) |
| `config-protection` | PreToolUse | `Edit\|Write` | `bash {root}/hooks/config-protection.sh` | Block modification of existing linter/formatter configs |
| `secret-scanner` | PreToolUse | `Bash` | `bash {root}/hooks/secret-scanner.sh` | Scan shell commands for credential-looking patterns |
| `spawn-gate` | PreToolUse | `Agent` | `bash {root}/hooks/spawn-gate.sh` | Generalist-switch gate: unknown or archived agent types get an ask pointing to agents-archive/ROLE-MAP.md |
| `track-edits` | PostToolUse | `Edit\|Write` | `bash {root}/hooks/track-edits.sh` | Buffer edited file paths for batch checking at session end |
| `write-evidence` | PostToolUse | `Edit\|Write` | `bash {root}/hooks/write-evidence.sh` | Log path + byte count of deliverable-shaped writes (paper trail against fabricated completions) |
| `loop-detector` | PostToolUse | (all) | `bash {root}/hooks/loop-detector.sh` | Detect stall loops: 5 identical tool calls in a row triggers a warning |
| `artifact-verify` | PostToolUse | `Agent` | `bash {root}/hooks/artifact-verify.sh` | Check that files an agent claims to have delivered exist on disk |
| `startup-sync` | SessionStart | (all) | `bash {root}/hooks/startup-sync.sh` | Fast-forward the agency root's config from GitHub on session open |
| `check-settings-secrets` | SessionStart | (all) | `bash {root}/hooks/check-settings-secrets.sh` | Warn if settings.json has plaintext tokens in MCP env blocks |
| `check-session-state` | SessionStart | (all) | `bash {root}/hooks/check-session-state.sh` | Detect an unclean prior exit (crash / Ctrl+C) |
| `stop-chain` | Stop | (all) | `bash {root}/hooks/session-end.sh && bash {root}/hooks/batch-check.sh && bash {root}/hooks/cost-tracker.sh` | Mark the session cleanly ended, typecheck/shellcheck edited files, record session cost |

Retired (pruned from `settings.json` on the next sync): none.
<!-- hooks-manifest:end -->

The three Stop scripts stay one chained command, exactly as earlier installers wrote it, so an existing install is recognised as already wired instead of getting a duplicate.

**What the merge changes, and what it never touches.** An entry in `settings.json` is the agency's when its command, with the root spelled `{root}`, equals a command in `hooks/hooks.json`, in its `retired` list, or in `{agency-root}/hooks/.agency-hooks-state.json` (the record of what the last sync wired). Everything else is yours and is never edited, moved or reordered — including scripts of your own that live in `{agency-root}/hooks/` but are not in the manifest, composite commands that happen to call one of our scripts, and every other top-level key (`permissions`, `env`, `mcpServers`, `statusLine`, ...).

- **Add:** a manifest hook that is not wired yet goes into an existing group with the same matcher that holds only agency hooks, or into a new `{matcher, hooks: [...]}` group at the end of that event.
- **Already wired:** an entry counts as present in any equivalent spelling of the root — the resolved path with forward or back slashes, the Git Bash form `/c/Users/...`, and, when the root is the default `<home>/.claude`, `~/.claude`, `$HOME/.claude` and `${HOME}/.claude`. A working `bash ~/.claude/hooks/x.sh` entry is left exactly as it is, under whatever matcher you put it.
- **Update:** when a release changes the command or matcher of a hook the last sync wired, that one entry is changed or moved.
- **Remove:** an agency hook that is no longer shipped (listed under `retired`, or recorded in the state file but gone from the manifest) is pruned. Groups and events that this leaves empty are removed; groups you left empty are not.
- **Safety:** before any change the previous file is copied to `settings.json.bak-YYYYMMDD-HHMMSS` next to it, and the new file is written to a temporary file in the same folder and renamed into place. When nothing changed, nothing is written — no backup, no rewrite. A `settings.json` that is not valid JSON is never written; you get the error and the command to run once it is fixed.
- **Paths:** commands are written with the resolved root and forward slashes (`bash C:/Users/me/.claude/hooks/gate-guard.sh` on Windows). A root that contains a space or another shell-special character is quoted per path.

**What you see.** When hooks were added, updated or removed, the installer or upgrade prints one line per hook (name, event, purpose, what was done), the backup path and `Restart Claude Code to activate the hooks.` — Claude Code reads `settings.json` at start-up. When nothing changed it prints one line: `Hooks: 12 wired, up to date`. When wiring is skipped it prints why and the exact command to finish it:

- `AGENCY_NO_HOOKS=1` — opt out of the automatic wiring in the installers, `agency init` and `agency upgrade`. An explicit `agency hooks sync` still works.
- Windows without Git Bash — Claude Code runs a command hook inside Git Bash when Git for Windows is installed (and in PowerShell when it is not, where `bash ...` would fail), so wiring is skipped. The message links https://git-scm.com/downloads/win and says to run `agency hooks sync` afterwards (`agency hooks sync --force` wires them anyway).
- `node` not installed (installers only) — install Node.js, then run the command printed.

**Finding Git Bash on Windows.** The installer does not rely on the PowerShell `PATH` (Git Bash is often not on it). `cli/lib/hooks-merge.js` looks for `bash.exe` in this order and stops at the first hit: (1) the file `CLAUDE_CODE_GIT_BASH_PATH` names, (2) `git --exec-path` (`C:/Program Files/Git/mingw64/libexec/git-core`): `Git\bin\bash.exe` is three folders up, and two and four are tried too, (3) `%ProgramFiles%\Git\bin\bash.exe`, (4) `%LOCALAPPDATA%\Programs\Git\bin\bash.exe`, (5) a `bash.exe` on `PATH`, ignoring `%WINDIR%\System32\bash.exe` and anything under `\WindowsApps\` (the WSL launcher, which would run hooks inside WSL). Hook commands stay `bash {root}/hooks/x.sh` because they run inside Git Bash, where `bash` resolves. If Git Bash was found in step 2 or 5 (a non-standard place) and Claude Code cannot find it, set `"env": {"CLAUDE_CODE_GIT_BASH_PATH": "C:\\path\\to\\bash.exe"}` in `settings.json`; the installer prints that line but never writes it.

**Fable-on-Opus is not wired.** `fable-on-opus.sh` is not in `hooks/hooks.json`. Recent Opus-line models carry the reasoning/behavioral discipline this hook injects natively, so wiring it by default duplicated guidance the model already applies on its own. The script and its `hooks/fable/` playbooks still ship and stay useful for operators on older model lines, or anyone who wants that discipline injected explicitly regardless of model tier. An entry you added yourself is yours: the merge never removes it.

To wire it in yourself, this is the block under `hooks`:

```json
"UserPromptSubmit": [
  {
    "hooks": [
      { "type": "command", "command": "bash ~/.claude/hooks/fable-on-opus.sh" }
    ]
  }
]
```

See [fable-on-opus.sh](#fable-on-opussh-userpromptsubmit) below for full behavior and the playbook inventory.

---

### Hooks Not Wired By Default

Four of the 18 shipped lifecycle hooks are copied to `hooks/` but are not in `hooks/hooks.json`, so no install or upgrade path wires them:

| Hook | Event | Unwired because | What you lose |
|------|-------|-----------------|---------------|
| `spawn-logger.sh` | PreToolUse: Agent | telemetry, opt-in is defensible | No `spawn_start` events or lineage markers |
| `spawn-completion.sh` | PostToolUse: Agent | telemetry, opt-in is defensible | No `spawn_end` events (outcome, tokens, duration) |
| `bg-job-warn.sh` | PostToolUse: Bash | convenience, opt-in is defensible | No warning when a render/build is backgrounded |
| `fable-on-opus.sh` | UserPromptSubmit | deliberate — superseded on recent Opus-line models | No Fable discipline injection on older model lines |

All four are unwired on purpose — three are telemetry and convenience, and `fable-on-opus.sh` was deliberately unregistered because recent model lines carry its discipline natively. Nothing in this list is a safety gap: `spawn-gate.sh`, `loop-detector.sh`, `write-evidence.sh`, and `artifact-verify.sh` — the four hooks previously documented here as an installer gap — are wired by every install path. See [Settings Wiring](#settings-wiring) above for their entries in `hooks/hooks.json`, and [spawn-gate.sh](#spawn-gatesh-pretooluse-agent) / [loop-detector.sh](#loop-detectorsh-posttooluse-all-tools) / [write-evidence.sh](#write-evidencesh-posttooluse-write-edit) / [artifact-verify.sh](#artifact-verifysh-posttooluse-agent) below for full behavior.

To wire any of the remaining four in yourself, merge an entry into the corresponding array in your `settings.json` `hooks` block (don't replace the entries already there — add alongside them). For example, for `spawn-logger.sh`:

```json
"PreToolUse": [
  {
    "matcher": "Agent",
    "hooks": [
      { "type": "command", "command": "bash ~/.claude/hooks/spawn-logger.sh" }
    ]
  }
]
```

---

## Settings Hygiene Patterns

`settings.json` accumulates cruft over the life of an install — hooks that get superseded, env flags that outlive the behavior they gated, config keys that get expressed two different ways across upgrades. None of this breaks anything outright; it just makes the file progressively less trustworthy as a description of what's actually running. Apply these patterns periodically, not just when something visibly misbehaves.

### Unregistering a hook without deleting it

When a hook's behavior becomes redundant (superseded by newer model/tool behavior, replaced by another hook, or simply not needed for your workflow), remove its event entry from `settings.json` — do not delete the script from `hooks/`.

Note: this sticks for hooks that are **not** in `hooks/hooks.json`. A hook that is in the manifest is wired again by the next install, `agency upgrade` or `agency hooks sync`. To keep one of those off, either set `AGENCY_NO_HOOKS=1` and manage the wiring by hand, or turn it off through the [profile system](#profile-system) instead of unregistering it.

This beats deletion for three reasons:
- **Reversible.** Re-adding the event entry restores the behavior instantly; no need to re-fetch or rewrite the script.
- **Keeps the script available to operators who still benefit from it** — e.g. a different model tier, a different profile, or a different risk tolerance.
- **No installer churn.** Deleting a shipped script means every installer and upgrade path (`install.sh`, `install.ps1`, `cli/`) has to know to stop shipping it, and re-adding it later means re-plumbing all of them again. Leaving it on disk, unregistered, avoids that entirely.

**Verify a hook is unregistered:**
```bash
grep -A2 '"<EventName>"' ~/.claude/settings.json | grep '<hook-name>.sh'
```
No match means the hook is not wired to that event — it will not run regardless of what's on disk in `hooks/`.

### Pruning dead env flags

Env flags in the `env` block of `settings.json` gate behavior. When that behavior becomes default, gets renamed, or is removed upstream, the flag becomes a no-op — but it stays in your file silently, implying control you no longer have.

Watch specifically for **double-negative flags**: a `DISABLE_<FEATURE>` (or `NO_<FEATURE>`) flag set to a falsy value (`false`, `0`, unset-equivalent) reads as "this is off" when it's actually a no-op either way — a common source of "I set this and nothing changed" confusion, because the flag may no longer be read by anything.

Before keeping any env flag across an upgrade, verify it still exists in the current release:
```bash
grep -rn "<FLAG_NAME>" {agency-root}/hooks/ {agency-root}/cli/ 2>/dev/null
```
No match means nothing reads it anymore — safe to drop from `settings.json`.

### Consolidating duplicated config keys

Some settings are expressible through more than one key — for example, a reasoning-effort or verbosity setting that can be set at the top-level `env` block, inside a specific tool's config, or via a model-line-specific override. When more than one of these is present at once, precedence between them is version-dependent: which key "wins" can silently change on upgrade, producing behavior that doesn't match any key you actually set.

The pattern: pick exactly one key for a given setting and drop the rest. Do not rely on precedence order to resolve duplicates — resolve it yourself, once, explicitly.

**Verify no duplicate keys remain** for a setting you care about:
```bash
grep -n "<setting-name>" ~/.claude/settings.json
```
More than one match against the same logical setting is the signal to consolidate — read the current release's docs for which key is canonical, keep that one, and remove the others.

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

**Status: ships in `hooks/` but is not in `hooks/hooks.json`, so no install path wires it** — recent Opus-line models carry this discipline natively, so the default registration was removed. See [Settings Wiring](#settings-wiring) above for the rationale and the opt-in wiring block.

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

Fast-forwards `{agency-root}` from `origin/main`. It never stashes and never merges. Steps:

1. `git fetch` runs under a background watchdog, 5 seconds by default (`SYNC_FETCH_TIMEOUT`). On a timeout or fetch failure it prints a warning and skips.
2. If local equals remote, it prints "Config up to date". If you only have unpushed local commits, it prints "Config ahead of remote" and does nothing.
3. It pulls (`git pull --ff-only`) only when the branch is `main` and the tracked tree is clean. On any other branch it skips with a warning.
4. If tracked files have uncommitted changes, it prints one warning (with how many commits the remote is ahead) and leaves your work untouched. Commit, then pull by hand.
5. If local and remote have diverged, it prints "manual merge needed" and changes nothing.

It always exits 0, so it can never block a session from starting. It uses no coreutils `timeout`, so it works on macOS bash 3.2.

**Effect:** Every new Claude Code session picks up the latest agents, skills, and hooks from your remote when it is safe to do so.

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

**Status: wired into `settings.json` by every install path (`hooks/hooks.json`)** — see [Settings Wiring](#settings-wiring) above.

Since the generalist switch (2026-10-06), `general-purpose` plus 1-3 named skills is the default spawn, and it passes without a question. The specialist agents are archived; their role-to-skills table is `{agency-root}/agents-archive/ROLE-MAP.md`. The gate only catches a `subagent_type` that is not recognized, such as a typo or a stale archived name. It never blocks: its strongest answer is an `ask`.

**Passes immediately (no marker needed):**

- `general-purpose`, `claude`, and an empty `subagent_type`
- Structural types: `pd-coordinator`, `coord`, `mini-coord`, `task-executor`, `curator`, `codebase-search`, `Delegator`, `save-state-runner`, `project-scaffolder`
- Any `*-pd` project director, any `* Dept-Coord`, `critique-*`, `*-critique`, and `Critiques Lead`
- The department heads: `Chief Content Officer`, `Design Lead`, `Engineering Lead`, `Project Management Lead`, `Specialized Agents Lead`, `Testing Lead`, `Video Studio Director`
- The knowledge-graph analyzers (`architecture-analyzer`, `article-analyzer`, `assemble-reviewer`, `domain-analyzer`, `file-analyzer`, `graph-reviewer`, `knowledge-graph-guide`, `project-scanner`, `tour-builder`)
- Built-in Claude Code types: `Explore`, `Plan`, `statusline-setup`, `claude-code-guide`, `fork`, and `caveman:*`

**Also passes (checked on the prompt, for any other type):**

- A prompt that starts with `You are PD-` (PD boot sequences from `/pd-spawn` and `/pd-resume`).
- A prompt with an explicit routing marker: `DELEGATOR ROUTING`, `HARDCODED ROUTING:`, or `SKILL SPAWN:`.
- A prompt that matches a skill-owned spawn pattern: `You own the save-state ritual`, `You own the cc-loop ritual`, `You are {name}, resuming work`, or `You are resuming work on inbox task`.

**Unknown type:** anything else receives `permissionDecision: ask`. The message names the unknown type, says the default is `general-purpose` + 1-3 skills, points to `{agency-root}/agents-archive/ROLE-MAP.md` for archived names, and says how to keep the type anyway (`HARDCODED ROUTING: {task-type} -> {agent}` in the prompt).

The hook emits no metric.

Respects the `.hook-profile` system: in `minimal` profile, the hook exits immediately with `{}` (all spawns allowed). It reads `{agency-root}/.hook-profile`, the same file as every other profile-aware hook. (Before Wave 16 this one hook read `~/.agency/.hook-profile` — a path nothing has ever written, so the documented way to turn this gate off silently did nothing.)

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

Logs a paper trail for deliverable writes. On every Write/Edit whose target path contains `/outputs/`, `/plans/`, `/reports/`, or `/qa/`, or ends in `.html`, `.htm`, `.pdf`, `.docx`, `.pptx`, or `.xlsx`, it stats the file post-write and appends a `write_evidence` entry (path, byte count, `exists` flag) to `~/.claude/logs/write-evidence.jsonl`. It also fire-and-forgets the same event to `{agency-root}/hooks/emit-metric.sh` (if present) so it's queryable alongside other metrics events.

**Effect:** pairs with `artifact-verify.sh` — if an agent claims a deliverable is DONE, there must be a corresponding `write_evidence` entry with non-zero bytes, or the fabrication guard has grounds to flag the claim.

Any internal error is silent; the hook never blocks a write.

### loop-detector.sh (PostToolUse: all tools)

**Status: wired into `settings.json` by every install path (`hooks/hooks.json`)** — see [Settings Wiring](#settings-wiring) above.

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

On every completion it first calls `hooks/lib/reconcile-stale-spawns.sh` on the same log file (see [reconcile-stale-spawns.sh](#reconcile-stale-spawnssh)), so spawns that never got a `spawn_end` are closed as `ABANDONED`.

Respects the `.hook-profile` system: in `minimal` profile, exits immediately without logging. Any internal error is silent.

### bg-job-warn.sh (PostToolUse: Bash, `run_in_background`)

Tracks fire-and-forget background Bash jobs. On every Bash tool call made with `run_in_background: true`, appends an entry (command, description, extracted background job ID, `resolved: false`) to `~/.claude/.pending-bg-jobs.jsonl`.

If the backgrounded command matches a render/build signal (`render`, `ffmpeg`, `bun run`, `npm run build`, `make `, `cargo build`, `go build`), it immediately prints a warning to stderr instructing the agent that it **must** await the job and `test -f` the output before reporting DONE — it must not proceed to a summary until the artifact is verified on disk.

Any internal error is silent; the hook never blocks the Bash call.

### cost-tracker.sh (Stop)

Reads the session transcript JSONL (from `transcript_path` in the hook input, or `$CLAUDE_TRANSCRIPT_PATH`) and appends one JSONL row to `costs.jsonl` in the `metrics/` folder of the agency root. It prints one summary line to stderr, for example `Session cost: $1.2345 (...)`. All rate tables and transcript parsing live in `hooks/lib/claude_pricing.py`, the single source for rates (see [claude_pricing.py](#claude_pricingpy)).

- **No double counting.** Usage is de-duplicated by `message.id`. Claude Code writes one API message as several transcript lines, each repeating the same usage.
- **Priced per model.** A session that switches models is priced message by message, not by the last model seen.
- **Row fields:** `timestamp`, `session_id`, `model` (the model with the most output tokens), `rate_label`, `rate_source` (`exact`, `family_fallback`, or `unknown_default`), token counts (input, output, cache write 5m and 1h, cache read), `by_model` (cost per model), `estimated_cost_usd`, and `pricing_version`.
- **Subagent transcripts are not included.**
- Nothing in it blocks. A parse failure writes nothing; the traceback goes to `.cost-tracker.err` in that same folder, which is overwritten on each run.

### caveman-statusline.sh (StatusLine)

Not a lifecycle hook — wired via the `statusLine` key in `settings.json` (`"statusLine": {"type":"command","command":"bash .../caveman-statusline.sh"}`), not the `hooks` key. Runs on every statusline render (effectively every turn).

Reads the caveman-mode flag file (`~/.claude/.caveman-active` by default, respecting `$CLAUDE_CONFIG_DIR`) and renders a colored `[CAVEMAN]` badge, or `[CAVEMAN:<MODE>]` for a specific mode (`lite`, `full`, `ultra`, `wenyan-*`, `commit`, `review`, `compress`). Refuses to read the flag (or the optional token-savings suffix file) if either is a symlink, hard-caps reads at 64 bytes, and strips any byte outside `[a-z0-9-]` before rendering — hardening against a local attacker planting ANSI-escape or OSC-hyperlink injection payloads in either file. Unrecognized mode values render nothing rather than echoing attacker-controlled bytes.

Optionally appends a pre-rendered token-savings suffix (from `~/.claude/.caveman-statusline-suffix`, written by `/caveman-stats`) unless `CAVEMAN_STATUSLINE_SAVINGS=0` is set.

### emit-metric.sh (utility — not a registered lifecycle hook)

A shared one-line utility, not itself wired into `settings.json`. Other hooks (`write-evidence.sh`) and agents call it directly: `emit-metric.sh '{"event":"...", ...}'`. It appends the given JSON payload — with a `ts` (UTC ISO-8601) field added automatically — as one line to `~/.claude/memory/metrics/events.jsonl`.

Always exits 0 and never raises; if the input is missing or unparseable, it's a silent no-op.

`hooks/fable/` is the one other subdirectory under `hooks/` — it holds the Fable playbook modules read by `fable-on-opus.sh` above, not additional registered hooks. `install.sh` copies it explicitly, as a separate step from the generic `hooks/*.sh` glob it uses for flat hook scripts (that glob does not pick up `*.md` files or subdirectories). `agency init` and `agency upgrade` copy the whole `hooks/` tree, `fable/` and `lib/` included.

---

## Helper Scripts (`hooks/lib/`)

`hooks/lib/` is **not** a set of directly-registered Claude Code hooks — none of these scripts appear in `settings.json`. They are shared bash/python helper scripts that other hooks and agents `source` or invoke directly to avoid duplicating logic (log-file resolution, spawn lineage IDs, context-percentage publishing, token pricing, stale-spawn cleanup). Think of this directory as the hook system's internal library, analogous to a `lib/` or `utils/` folder in an application codebase.

### resolve-root.sh

The single source of truth for **where the agency is installed**. Sourced (never executed) by every script under `hooks/` and `scripts/` that needs to address a sibling tree; it exports one variable, `AGENCY_ROOT`, resolved as `$AGENCY_HOME` → `$CLAUDE_CONFIG_DIR` → `~/.claude`.

Callers source it by a path relative to *their own* location — `. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh"` — because resolving the root is precisely the thing they cannot do yet. Each call site appends `2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"` as a degraded fallback, so a partial install cannot hard-fail a hook on Claude Code's hot path.

Before this existed, every hook and script hardcoded `$HOME/.claude` while the installers honoured `AGENCY_HOME` — so a custom-root install wrote to one directory and was read from another, silently. `.github/scripts/check-hardcoded-root.sh` now fails the build if that pattern returns. Python scripts use the documented inline twin (`os.environ.get("AGENCY_HOME") or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()/".claude"`) rather than importing, because several are run by absolute path from arbitrary working directories.

### resolve-project.sh

Defines a single function, `resolve_project_path`, meant to be `source`d (not executed) by callers: `source {agency-root}/hooks/lib/resolve-project.sh && resolve_project_path`. It reads the Active Projects table in `~/.claude/memory/medium-term.md`, expands each row's backtick-quoted path, and longest-prefix-matches it against the current working directory (`$CLAUDE_PROJECT_DIR` or `$PWD`). On a match it sets `SPAWN_LOG_FILE` to `{project_root}/memory/spawns.jsonl`; otherwise it falls back to `~/.claude/logs/spawns.jsonl`. Used by `spawn-completion.sh` and `spawn-gate.sh`-adjacent tooling to keep spawn logs project-scoped. This is the bash/sourced twin of the `resolve_log_file()` python helper duplicated inline inside `spawn-logger.sh`, `spawn-completion.sh`, and `log-spawn-from-agent.sh`.

### log-spawn-from-agent.sh

Called by a PD/Coord/Mini-Coord **before** each `Agent({...})` call it makes directly (i.e. agent-instrumented spawn logging, as a complement to the automatic `spawn-logger.sh` PreToolUse hook). Takes `--parent-agent`, `--child-subagent-type`, `--description`, and `--prompt-excerpt` flags, writes a `spawn_start` JSONL entry (tagged `"source": "agent-instrumented"`), and prints a freshly generated `spawn_id` (UUID) to stdout for the caller to capture and pass down to the child. On any internal failure it still prints a valid UUID so the caller is never blocked.

### log-spawn-end-from-agent.sh

The completion-side counterpart to `log-spawn-from-agent.sh`. Called by a PD/Coord/Mini-Coord **after** an `Agent({...})` call returns, with `--spawn-id`, `--outcome`, and `--summary` flags. Writes a `spawn_end` JSONL entry (tagged `"source": "agent-instrumented"`) for the given `spawn_id`. Silent no-op if `--spawn-id` is empty; any internal error is silently swallowed.

### claude_pricing.py

A Python module, not a hook. `cost-tracker.sh` imports it. It holds the per-model Claude rates (USD per million tokens: input, 5-minute and 1-hour cache write, cache read, output) as the single source of truth, plus three functions:

- `rate_for(model)` returns the rate and a `rate_source`: `exact` (a known model id), `family_fallback` (an unknown version of a known family gets that family's newest rate, so a stale table shows up instead of silently mispricing), or `unknown_default`.
- `cost_usd(model, ...)` prices a set of token counts.
- `usage_from_transcript(path)` sums usage over a Claude Code transcript, de-duplicated by `message.id`, with a per-model breakdown.

The table carries a verification date in its header. Before you edit any rate, check it against the live Anthropic pricing page. Do not copy prices from memory.

### reconcile-stale-spawns.sh

Called by `spawn-completion.sh` on every completion, with the spawn log path as its only argument (`bash reconcile-stale-spawns.sh /path/to/spawns.jsonl`). A completion record can be lost: the session may crash or hit a usage limit before the Agent call returns, or an agent may skip the manual `log-spawn-end-from-agent.sh` step. This script turns that silent gap into a known state. Any `spawn_start` with no `spawn_end` after `SPAWN_STALE_THRESHOLD_SEC` (default 21600, 6 hours) gets a synthetic `spawn_end` with `outcome: "ABANDONED"` and `source: "reconciliation-sweep"`.

- **Append-only and idempotent.** It never rewrites or deletes a line, and a `spawn_id` that already has any `spawn_end` is never touched again.
- **Throttled.** A `.reconcile-marker` file beside the log limits real work to once per `SPAWN_RECONCILE_INTERVAL_SEC` (default 900 seconds), so it is safe on a hot path.
- **Fire-and-forget.** It always exits 0 and never writes to stderr in a way that shows in hook output.

### context-pct-publish.sh

Reads the current context-window usage (from `$CLAUDE_CONTEXT_PCT`, or parsed out of `$CLAUDE_USAGE` JSON as a fallback) and publishes it to `~/.claude/state/context-pct.txt` as an integer 0-100, so agents can self-monitor their own context budget per the Self-Respawn Protocol. Emits a `CONTEXT_PCT_ALERT` to stderr at the 70% (warning — complete current task, no new L3s) and 80% (mandatory `/save-state` + `/respawn-self`) thresholds.

---

## Extending the Hook System

To add a new hook:

1. Write the script to `hooks/{name}.sh` and document it under [Hook Details](#hook-details)
2. Add an entry to `hooks/hooks.json` (`id`, `event`, `matcher`, `command` as `bash {root}/hooks/{name}.sh`, `purpose`), then run `node .github/scripts/check-hooks-manifest.js --write` to regenerate the table in [Settings Wiring](#settings-wiring). Every install and `agency upgrade` then wires it, and prints it as new. To stop shipping a hook later, move its entry to `retired` (`id`, `event`, `command`) so existing installs get it pruned.
3. Make it profile-aware if it blocks or warns:
   ```bash
   PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
   if [ "$PROFILE" = "minimal" ]; then echo '{}'; exit 0; fi
   ```
4. Return `{}` for pass-through, or a JSON object with `permissionDecision` and `message` for PreToolUse hooks

To disable a single hook without removing it from settings, use the `minimal` profile or comment out the command in `settings.json`.

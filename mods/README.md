# Mods

Optional Claude Code plugins that ship with The Agency. Each one is a plugin of function hooks that hot-reloads in a running session. Mods need Claude Code 2.1.287 or newer. The installer and `agency upgrade` wire them for you.

- **context-band**: Claude Code shows no running context, cache or usage-window figures above the prompt -> a band with context %, tokens, model, cost, cache warm/cold countdown and 5h/7d reset timers, plus `/ctx` for a detail pane.
- **agent-ctx**: A long-running agent does not notice its own context filling up -> it tells the agent when its own context crosses a threshold. Subagents: absolute tokens, warn at 200k, finish at 250k, stop line on every tool result from 300k. Main session: 70/75/80% of its window. Controllers (PD/Coord) also get `CHILD_CTX` on Agent and SendMessage results and `CHILD_CTX_ALERT` when a live child passes 250k/300k.
- **loop-guard**: An agent repeats the same tool call forever and nobody notices -> it injects a stall warning after five identical calls in a row.
- **spawn-ledger**: Subagent spawns leave no record, the `model` param leaks Opus onto sonnet-pinned agents and nothing caps parallel Execs -> it logs every spawn to JSONL, pins the model, caps Execs per PD, verifies claimed artifacts and relays `RESPAWN_REQUEST`. With the skill router on (`AGENCY_SKILL_ROUTER=1`) it also runs the optional Jev spawn gate (see below).
- **voice-compact**: The CAVEMAN / PONYTAIL startup injections cost a lot of tokens every session -> it rewrites them into ~150-token compact rules.

## Installing

The installer and `agency upgrade` set the mods up for you. `install.sh`, `install.ps1`, `agency init` and `agency upgrade` all run the same step (`cli/lib/mods-merge.js`):

1. Copy each `mods/<name>/` to `<root>/mods/<name>/`, so the entry keeps working if you move or delete the clone.
2. Add the absolute path of each copy to `env.CLAUDE_CODE_PLUGIN_DIRS` in your user `settings.json` (`:` between entries on macOS and Linux, `;` on Windows). Your own value stays as it was, in the same order; ours go after it.
3. Record what it added in `<root>/hooks/.agency-hooks-state.json` (the `mods` key), so a later run and `agency mods remove` touch only that.

A timestamped `settings.json.bak-*` copy is written next to `settings.json` before any change. A run that changes nothing writes nothing.

What it will not do:

- **Old Claude Code.** Mods need Claude Code 2.1.287 or newer. On an older version, or when the `claude` CLI is not found, nothing is written and the installer prints one line: `Mods: skipped (needs Claude Code 2.1.287+, found <version|none>). After updating: agency mods sync`.
- **A mod you already have.** Duplicates are matched by mod NAME, not by path. If one of your `CLAUDE_CODE_PLUGIN_DIRS` entries already provides a mod of that name (the entry is a plugin folder, or a folder of plugin folders), yours wins and ours is not added.
- **A folder that is not ours.** If `<root>/mods/<name>/` already exists and the agency did not put it there (a live checkout you maintain, say), it is skipped and left alone.

Restart Claude Code after any change so it loads the mods.

Opt out of the automatic step with `AGENCY_NO_MODS=1` (any value except empty or `0`) in the environment of the installer or `agency upgrade`. An explicit `agency mods sync` ignores it.

### The `agency mods` command

```bash
agency mods sync      # copy the mods and wire them (the same step the installer runs)
agency mods status    # what is wired, what would change, what is skipped
agency mods remove    # unwire exactly our entries and delete exactly the folders we copied
```

`remove` restores your own `CLAUDE_CODE_PLUGIN_DIRS` value. A mod the repo stops shipping, or one you now provide yourself, is pruned by the next `sync`. Add `--json` for a machine-readable result, `--root <dir>` to target another agency root. Without the `agency` command on PATH: `node <repo>/cli/lib/mods-merge.js sync|remove|status --root "<root>"`.

`agency hooks remove` does not remove the mods; it keeps the `mods` record in the ownership file (see `docs/HOOKS.md`).

`<root>` is your agency root: `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`. Every mod resolves paths from that root the same way.

## Manual loading (fallback)

Use this only if you opted out, or you want to load a mod straight from a clone. Pick one:

**(a) Every session.** In your user settings (`~/.claude/settings.json`, or the settings file in your Claude config dir) list the mod folders in `env.CLAUDE_CODE_PLUGIN_DIRS`:

```json
{ "env": { "CLAUDE_CODE_PLUGIN_DIRS": "<root>/mods/context-band:<root>/mods/spawn-ledger" } }
```

- Separator: `:` on macOS and Linux, `;` on Windows.
- Use absolute paths or `~` paths only.
- Project and local settings cannot set it; only user settings count.
- The variable needs Claude Code 2.1.280 or newer (the installer step above needs 2.1.287).

**(b) One session.** `claude --plugin-dir <root>/mods/<name>`.

Warning: two entries that resolve to the same mod name BOTH load, and its hooks fire twice (verified on Claude Code 2.1.293). The installer step avoids this for you; by hand, disable one with `"<name>@inline": false` under `enabledPlugins`.

## Overlap with the shell hooks

`hooks/hooks.json` wires two hooks by default that do the same job as a mod, and the installer now wires the mods too, so by default you get both. They stay wired side by side for now (owner decision), which gives duplicates:

- `loop-detector.sh` (all tools) and `loop-guard`: two stall warnings. Both write the `stall_*` keys of `<root>/session-state.json` idempotently; the shell hook also keeps `.tool-call-tracker.jsonl`. Both honour `.hook-profile` = `minimal`.
- `artifact-verify.sh` (Agent) and `spawn-ledger`: duplicate `ARTIFACT_MISSING` warnings and duplicate rows in `logs/artifact-verify.jsonl`.
- `spawn-logger.sh` and `spawn-completion.sh` are opt-in (see `docs/HOOKS.md`, "Hooks Not Wired By Default"). Wiring them next to `spawn-ledger` gives duplicate `spawn_start` / `spawn_end` rows with different `spawn_id`s. `spawn-logger.sh` also injects the `[[CLAUDE_SPAWN_META]]` marker.
- `agent-ctx` is independent of `context-pct-publish.sh`.

To run one of each pair, disable the shell hook (`agency hooks disable loop-detector`; ids are listed in `docs/HOOKS.md`) or skip the mod (`agency mods remove`, or `"<name>@inline": false` under `enabledPlugins`).

## Dependencies and degradation

| Mod | Reads | Writes | When something is absent |
|-----|-------|--------|--------------------------|
| context-band | session usage from Claude Code; `<root>/memory/metrics/jev-usage.jsonl` and `<root>/state/skill-route/jev-down` (older `<root>/logs/jev-usage.jsonl`, `<root>/state/jev-down` if the new ones are missing; `JEV_USAGE_LOG` and `SKILL_ROUTE_STATE_DIR` override) | nothing | No usage log and no flag: the Jev router row is hidden and the rest of the band draws. Rates are built in; no pricing script needed. |
| agent-ctx | session context percent; `<root>/.hook-profile` | nothing | No `.hook-profile`: standard profile. `minimal` turns the alert off. |
| loop-guard | `<root>/.hook-profile` | `<root>/session-state.json` (`stall_*` keys) | No `.hook-profile`: standard. Unwritable state file: the warning still fires. |
| spawn-ledger | `<root>/memory/medium-term.md` (project registry), `<root>/agents/*.md` (model lookup), `<root>/.hook-profile`, `hooks/lib/model-pin.py` + `exec-model-map.json`, `hooks/lib/spawn_project.py` (which project log a spawn belongs to), `hooks/lib/claude_pricing.py` (cost), `hooks/lib/reconcile-stale-spawns.sh`, `hooks/lib/find_bash.py` (which `bash` may be started), `scripts/skill-route.py` and `scripts/jev-spawn-gate.py` (both only when `AGENCY_SKILL_ROUTER=1`) | spawn JSONL (`spawns.jsonl` in the spawn's project `memory/`, else `<root>/logs/`; see below), `<root>/logs/artifact-verify.jsonl`, `<root>/memory/metrics/events.jsonl`, `<root>/state/spawn-slots.jsonl` | No `python3` or no `model-pin.py`: spawns go through unchanged (fail open). No `medium-term.md`: `RESPAWN_REQUEST` slugs are not checked against known projects and the log goes to `<root>/logs/spawns.jsonl`. Skill-route shadow call runs only when `AGENCY_SKILL_ROUTER=1` and `scripts/skill-route.py` exists. `.hook-profile` = `minimal` turns the whole mod off. Kill switches for the pin: `MODEL_PIN_OFF=1`, `state/model-pin.off`; cap only: `SPAWN_CAP_OFF=1`, `state/spawn-cap.off`. Router off (the default): the Jev gate is never started. |
| voice-compact | the hook-context injections of the caveman / ponytail plugins | nothing | Plugins not installed: nothing to rewrite, the mod does nothing. |

`spawn-ledger` takes cost rates from the shipped `hooks/lib/claude_pricing.py`. The installers copy `hooks/lib/*.py` and `hooks/lib/*.json` (`model-pin.py`, `spawn_project.py`, `exec-model-map.json`, `claude_pricing.py`) next to the shell hooks, so the mod finds them under `<root>/hooks/lib/`.

### Jev spawn gate (router on only)

The Jev spawn gate is the optional enforcer for binding skill routing on spawns. It ships DISABLED, together with the skill router: the mod calls `scripts/jev-spawn-gate.py` from its `agent.spawn` hook, before the model pin, only when `AGENCY_SKILL_ROUTER` is exactly `1`. With the router off (the default) no gate process starts and a spawn is untouched. The script also passes unchanged when the router is off.

With the router on, the gate relays one of three answers:

- **pass**: the spawn goes through as it is. A `note` rides the Agent result as context.
- **rewrite**: the spawn goes through with the full replacement prompt (the `Jev[r=<route_id>]` line and `Skills:` line injected).
- **deny**: the spawn is refused once with a ready-to-paste message; the spawner re-issues the same call with its verdict line. No ledger row is written for a denied spawn and the model pin (and its Exec cap slot) is never consulted. Three denies for one route id, or for one spawner and task, turn into a pass.

Jev down never blocks: a timeout, a crash, no `python3`, non-JSON output, an unknown action, a rewrite without a prompt or a deny without a message all fail open and the spawn runs unchanged. Off switches (the script reads them, not the mod): `JEV_GATE_OFF=1`, the file `<root>/state/jev-gate.off`, and `<root>/.hook-profile` = `minimal`. The gate path resolves through the same root as everything else (`AGENCY_HOME`, `CLAUDE_CONFIG_DIR`, `<home>/.claude`). The router needs your own Jev key (see `scripts/skill-route/README.md`).

### Effort policy (on by default)

The `effort` section of `hooks/lib/exec-model-map.json` sets the reasoning effort of every subagent by task type: `pd` medium, `coding_complex` high, `coding_routine` medium, `visual` high, `content_en` high, `content_vi` xhigh, `other` medium, `lookup` low (only with an explicit `MODEL-CATEGORY: lookup`). The mod API cannot set `effort` at `agent.spawn`, so `model-pin.py` only DECIDES it there, the `spawn-ledger` hook stores the decision per agent, and a `turn.step` hook APPLIES it to every request of that subagent. The policy overrides the caller's `effort` param and the agent file's `effort:` frontmatter. Fork, teammate and workflow spawns are skipped.

Classification reuses the Jev route cache (`Jev[r=<id>]` in the prompt), so with the router off (the default) there is no Jev line: PDs (`*-pd`, `pd-coordinator`) and the named agents in the `agents` table (critics, `coord`, `mini-coord`, `codebase-search`, `Delegator`) still classify, and every `general-purpose` spawn falls to `other` = `medium` unless the prompt carries `MODEL-CATEGORY: <name>` (`lookup`, `debug`). Every PD def carries `effort: medium`; other agent defs carry no `effort:` line (`hooks/tests/test_effort_policy_defs.py` checks this).

Ledger rows: `effort_override` (policy value differs from the agent file's `effort:`), `effort_policy` (already equal) and `effort_skipped` at spawn, `effort_applied` at the first `turn.step` (`ledger.py effort_applied`), and a `model_pin_error` row prefixed `effort: ` if the step fails (fail open: the spawn is untouched). Kill switches (effort only): `EFFORT_POLICY_OFF=1`, `state/effort-policy.off`, or `effort.enabled: false`; the model-pin switches turn it off too.

Windows: CI unit/TS tests only; the live `turn.step` relay is unproven on a real Windows session.

### Where spawn rows live

A spawn's rows (`spawn_start`, `spawn_launched`, `spawn_end`) go to ONE `spawns.jsonl`, chosen by `hooks/lib/spawn_project.py` in this order: a `Project:` line in the prompt (a path on it, else its first word if it is a slug in `<root>/memory/medium-term.md`), then a parent agent named `{slug}-pd`, then a subagent type `{slug}-pd`, then the working directory (longest path-boundary match against the project table), else `<root>/logs/spawns.jsonl`. `<root>/logs/spawns.jsonl` therefore holds only spawns with no project hint; looking only there makes a healthy ledger look empty. `ledger.py launched` and `end` find the start row in whichever log holds it, `model-pin.py` counts the Exec cap across every known log, and `reconcile-stale-spawns.sh` checks all of them before it closes a spawn as ABANDONED.

## Shared code: `mods/_shared/`

`mods/_shared/` is for developers of the mods; it is not a mod. It holds `platform.ts` (home directory, path joining, python launcher), `testpaths.ts` (test-only: the kit runs every path through the host's `path.resolve`, which rewrites `C:\x/y` on Windows, so tests compare through `seenWin` / `seenPosix`; no `register` file imports it) and a test that fails when a copy drifts. A mod cannot import a file outside its own plugin folder, so agent-ctx, context-band, loop-guard and spawn-ledger each carry a byte-identical copy of both at `hooks/platform.ts` and `hooks/testpaths.ts`. Edit the file in `_shared/`, copy it over the four, then run `python3 mods/_shared/test_copies_identical.py`. `_shared/` has no plugin manifest, so the installer neither copies it to `<root>/mods/` nor adds it to `CLAUDE_CODE_PLUGIN_DIRS` (`check-mods-merge.js` and `check-mods-install.sh` pin this).

## Tests

From the repo root. The JavaScript tests need the `claude` CLI; the Python ones need only `python3`.

```bash
for m in agent-ctx context-band loop-guard spawn-ledger voice-compact; do
  claude plugin validate mods/$m && claude plugin test mods/$m
done
python3 -m unittest discover -s mods/spawn-ledger/tests   # includes test_model_pin.py (the one copy of the model-pin tests)
python3 -m unittest discover -s hooks/tests                # spawn_project.py, find_bash.py, the live-log guard, the win32 model-pin tests
python3 mods/_shared/test_copies_identical.py              # platform.ts and testpaths.ts copies are byte-identical
python3 -m unittest discover -s scripts/tests -p "test_[0wz]*.py"   # isolation bootstrap, win32 jev, live-log guard (the full suite is `-s scripts/tests`)
```

`hooks/lib/model-pin.py` is tested from `mods/spawn-ledger/tests/test_model_pin.py` only; there is no second copy under `hooks/tests/`.

**Tests never write a live log.** Each suite (`mods/spawn-ledger/tests`, `hooks/tests`, `scripts/tests`) starts with `test_00_isolation.py`, which snapshots every live log and moves `HOME`, `USERPROFILE`, `HOMEDRIVE` and `HOMEPATH` of the whole test process to a temp tree before any test module loads; `AGENCY_HOME` and `CLAUDE_CONFIG_DIR` are cleared there, so the agency root of every writer is the temp tree too (`hooks/lib/test_home.py`). Each suite ends with `test_zz_real_ledger_guard.py`, which fails the run if a live log changed (`hooks/lib/live_log_guard.py`; it resolves the real root with the same `AGENCY_HOME` -> `CLAUDE_CONFIG_DIR` -> `<home>/.claude` ladder). `ledger.py` also refuses a `spawns.jsonl` outside the temp dir under a test run, and its `verify` log honours `ARTIFACT_VERIFY_LOG`. The isolation covers `unittest discover`; a single test file run on its own, and the TypeScript tests (a fake engine, no real file system), rely on their own stubs. Tests that need `bash` use `hooks/lib/find_bash.py`: on Windows a bare `bash` is the WSL launcher, which exits 1 without output.

## Windows status

Windows support is only partly proven. Do not read this section as "Windows is supported". What has been done:

- **Simulated on macOS.** The mods and their Python helpers were made Windows-aware (`USERPROFILE` as the home, a python launcher that falls back to `py -3`, an `msvcrt` lock for the Exec cap, UTF-8 stdio, drive-letter and `~\` path forms in the project and artifact checks, a Windows process-detach flag, Git for Windows' `bash` picked by full path) and tested with `win32` simulated: stubbed environment and platform, mocked `os.name`, `sys.platform`, `shutil.which` and `Popen`, a fake `msvcrt`, and subprocesses forced to a cp1252 code page. These tests show the code takes the right branch.
- **CI unit tests on a real runner.** The `windows-latest` CI job now also runs the mods' Python suites (spawn-ledger, `hooks/tests`, the `mods/_shared` identity test, the `scripts/tests` isolation and win32 subset) and `claude plugin validate` + `claude plugin test` for all five mods. Those steps are required, like the ubuntu job's. A real Windows runner found bugs the simulation hid, all fixed: a bare `bash` resolved to the WSL launcher so the stale-spawn sweep silently did nothing, `os.path.expanduser` ignores `HOME` there so tests that moved only `HOME` resolved the real home, and the host's `path.resolve` rewrote the separators the TypeScript tests compared.

A ledger export from one real Windows host (counts only) has since checked part of the list:

- **Check 2 PASSED.** A spawn writes a ledger row: 54 `spawn_start`, 54 launched and 107 end rows.
- **Check 3 PASSED.** The Exec cap holds under `msvcrt`: 8 `spawn_denied` at running=5, cap=5.
- **Check 5 FAILED on the pre-fix build.** Vietnamese text came back as cp1252 mojibake. The fix is the UTF-8 transcript read in `hooks/lib/claude_pricing.py` plus the UTF-8 stdio and env forcing already in the mod. It still needs one fresh Vietnamese spawn on Windows after `agency upgrade` to count as PASS.
- The same export showed all 54 starts labelled with the wrong project (a `D:\` root never matched); fixed by the single resolver in `hooks/lib/spawn_project.py` and the `global` label for no-project rows. Confirm on the next export that rows carry the real slug.
- **Checks 1, 4 and 6 remain unproven.** Nothing is marked passed in the list below.
- `UNKNOWN` outcomes (39 of the 107 end rows) are expected whenever the final report carries no English outcome token (DONE, COMPLETE, BLOCKED, ESCALATE, KILLED); they are not a parse failure (see the OUTCOME docstring in `mods/spawn-ledger/bin/ledger.py`).

That is still mostly "simulated + CI unit tests". These stay UNPROVEN on a real Windows host:

- live hook loading in a real Windows Claude Code session (check 1 below);
- what `reconcile-stale-spawns.sh` does to a live ledger there (CI runs it on a temp ledger only);
- a Windows host without Git for Windows (simulated only: the sweep is skipped, nothing else changes).

Until the checks below pass on a real Windows host, treat the mods there as untested.

### Checks to run on a real Windows host

1. **Mods load with no hook errors.** Start `claude --debug` with the mods wired and read the log for hook errors from agent-ctx, context-band, loop-guard and spawn-ledger.
2. **A spawn writes a ledger row, through `py -3`.** On a machine where `python3` is the Microsoft Store stub, spawn any subagent with no `Project:` line. A `spawn_start` row must appear in `%USERPROFILE%\.claude\logs\spawns.jsonl` (`<root>\logs\spawns.jsonl` if you set `AGENCY_HOME` or `CLAUDE_CONFIG_DIR`). The mod probes `python3`, then `CLAUDE_PYTHON`, `py -3`, `python`, and accepts only Python 3.
3. **The Exec cap holds under the Windows lock.** Start six `general-purpose` Execs under one PD at once; the sixth must be denied with the `[spawn-cap]` message (the cap lock is `msvcrt` there, `fcntl` elsewhere).
4. **`ledger.py verify` with a `C:\` path.** Pipe `{"text": "DONE wrote C:\\nope\\x.pdf"}` into `py -3 mods\spawn-ledger\bin\ledger.py verify`; it must print an `ARTIFACT_MISSING` warning naming that path.
5. **A Vietnamese prompt round-trips.** Spawn with a Vietnamese prompt and check the `spawns.jsonl` row and the `ledger.py` output come back intact (the helpers force UTF-8 over a cp1252 default).
6. **The context-band Jev line updates on a large log.** With a `jev-usage.jsonl` over 1 MiB, the Jev line must still update (the band reads the tail; Windows has no `tail`, so it falls back to a python one-liner).

### Known gaps on Windows

- `scripts/skill-route.py` and `hooks/lib/resolve-project.sh` now resolve the project through `hooks/lib/spawn_project.py` (drive-letter and Git-Bash spellings match). Still POSIX-only: the `medium-term.md` parsing in `scripts/jev-feedback.py`, the inline python of `hooks/lib/reconcile-stale-spawns.sh`, and the legacy `hooks/lib/log-spawn-from-agent.sh`, `hooks/lib/log-spawn-end-from-agent.sh` and `hooks/spawn-logger.sh`, which still label a global-log row with the old basename rule.
- `hooks/lib/reconcile-stale-spawns.sh` and `hooks/emit-metric.sh` need `bash` (Git for Windows). `hooks/lib/find_bash.py` finds it by full path and never returns the WSL launcher in `System32`; without Git for Windows `ledger.py` skips the stale-spawn sweep.
- `CLAUDE_PYTHON` names one executable path, no arguments. A launcher that needs flags must go through `py -3` or a wrapper.
- If neither `fcntl` nor `msvcrt` loads, or `msvcrt` gives up after about 10 seconds, the Exec cap runs without the lock and parallel spawns can over-count.
- Root resolution is not a gap here: the mods, `ledger.py`, `model-pin.py` and `spawn_project.py` all honour `AGENCY_HOME`, then `CLAUDE_CONFIG_DIR`, then `<home>/.claude`.

Make no claim of Windows support beyond this section.

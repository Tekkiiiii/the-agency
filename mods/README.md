# Mods

Optional Claude Code plugins that ship with The Agency. Each one is a plugin of function hooks that hot-reloads in a running session. Mods need Claude Code 2.1.287 or newer. The installer and `agency upgrade` wire them for you.

- **context-band**: Claude Code shows no running context, cache or usage-window figures above the prompt -> a band with context %, tokens, model, cost, cache warm/cold countdown and 5h/7d reset timers, plus `/ctx` for a detail pane.
- **agent-ctx**: A long-running agent does not notice its own context filling up -> it tells the agent when its own context crosses 70% and 80% (respawn threshold).
- **loop-guard**: An agent repeats the same tool call forever and nobody notices -> it injects a stall warning after five identical calls in a row.
- **spawn-ledger**: Subagent spawns leave no record, the `model` param leaks Opus onto sonnet-pinned agents and nothing caps parallel Execs -> it logs every spawn to JSONL, pins the model, caps Execs per PD, verifies claimed artifacts and relays `RESPAWN_REQUEST`.
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
| spawn-ledger | `<root>/memory/medium-term.md` (project registry), `<root>/agents/*.md` (model lookup), `<root>/.hook-profile`, `hooks/lib/model-pin.py` + `exec-model-map.json`, `hooks/lib/spawn_project.py` (which project log a spawn belongs to), `hooks/lib/claude_pricing.py` (cost), `hooks/lib/reconcile-stale-spawns.sh`, `scripts/skill-route.py` | spawn JSONL (`spawns.jsonl` in the spawn's project `memory/`, else `<root>/logs/`; see below), `<root>/logs/artifact-verify.jsonl`, `<root>/memory/metrics/events.jsonl`, `<root>/state/spawn-slots.jsonl` | No `python3` or no `model-pin.py`: spawns go through unchanged (fail open). No `medium-term.md`: `RESPAWN_REQUEST` slugs are not checked against known projects and the log goes to `<root>/logs/spawns.jsonl`. Skill-route shadow call runs only when `AGENCY_SKILL_ROUTER=1` and `scripts/skill-route.py` exists. `.hook-profile` = `minimal` turns the whole mod off. Kill switches for the pin: `MODEL_PIN_OFF=1`, `state/model-pin.off`; cap only: `SPAWN_CAP_OFF=1`, `state/spawn-cap.off`. |
| voice-compact | the hook-context injections of the caveman / ponytail plugins | nothing | Plugins not installed: nothing to rewrite, the mod does nothing. |

`spawn-ledger` takes cost rates from the shipped `hooks/lib/claude_pricing.py`. The installers copy `hooks/lib/*.py` and `hooks/lib/*.json` (`model-pin.py`, `spawn_project.py`, `exec-model-map.json`, `claude_pricing.py`) next to the shell hooks, so the mod finds them under `<root>/hooks/lib/`.

### Where spawn rows live

A spawn's rows (`spawn_start`, `spawn_launched`, `spawn_end`) go to ONE `spawns.jsonl`, chosen by `hooks/lib/spawn_project.py` in this order: a `Project:` line in the prompt (a path on it, else its first word if it is a slug in `<root>/memory/medium-term.md`), then a parent agent named `{slug}-pd`, then a subagent type `{slug}-pd`, then the working directory (longest path-boundary match against the project table), else `<root>/logs/spawns.jsonl`. `<root>/logs/spawns.jsonl` therefore holds only spawns with no project hint; looking only there makes a healthy ledger look empty. `ledger.py launched` and `end` find the start row in whichever log holds it, `model-pin.py` counts the Exec cap across every known log, and `reconcile-stale-spawns.sh` checks all of them before it closes a spawn as ABANDONED.

## Shared code: `mods/_shared/`

`mods/_shared/` is for developers of the mods; it is not a mod. It holds `platform.ts` (home directory, path joining, python launcher) and a test that fails when a copy drifts. A mod cannot import a file outside its own plugin folder, so agent-ctx, context-band, loop-guard and spawn-ledger each carry a byte-identical copy at `hooks/platform.ts`. Edit `_shared/platform.ts`, copy it over the four, then run `python3 mods/_shared/test_copies_identical.py`. `_shared/` has no plugin manifest, so the installer neither copies it to `<root>/mods/` nor adds it to `CLAUDE_CODE_PLUGIN_DIRS` (`check-mods-merge.js` and `check-mods-install.sh` pin this).

## Tests

From the repo root. The JavaScript tests need the `claude` CLI; the Python ones need only `python3`.

```bash
for m in agent-ctx context-band loop-guard spawn-ledger voice-compact; do
  claude plugin validate mods/$m && claude plugin test mods/$m
done
python3 -m unittest discover -s mods/spawn-ledger/tests   # includes test_model_pin.py (the one copy of the model-pin tests)
python3 -m unittest discover -s hooks/tests                # spawn_project.py and the win32 model-pin tests
python3 mods/_shared/test_copies_identical.py
```

`hooks/lib/model-pin.py` is tested from `mods/spawn-ledger/tests/test_model_pin.py` only; there is no second copy under `hooks/tests/`. A test run can never write a real ledger: `ledger.py` refuses a `spawns.jsonl` outside the temp dir under a test run, and `test_zz_real_ledger_guard.py` fails the suite if a real ledger changed.

## Windows status

Windows support is UNPROVEN on a real Windows host. What has been done:

- **Simulated on macOS only.** The mods and their Python helpers were made Windows-aware (`USERPROFILE` as the home, a python launcher that falls back to `py -3`, an `msvcrt` lock for the Exec cap, UTF-8 stdio, drive-letter and `~\` path forms in the project and artifact checks, a Windows process-detach flag, a `bash`-missing guard) and tested with `win32` simulated: stubbed environment and platform, mocked `os.name`, `sys.platform`, `shutil.which` and `Popen`, a fake `msvcrt`, and subprocesses forced to a cp1252 code page. These tests show the code takes the right branch. They do not show a real Windows run works.
- **No Windows run of the mods.** The `windows-latest` CI job checks the installer wiring (the mods land in `CLAUDE_CODE_PLUGIN_DIRS` with Windows paths). It does not load a mod or run the mods' Python helpers (`ledger.py`, `model-pin.py`, `spawn_project.py`).

Do not read this as "Windows is supported". Until the checks below pass on a real Windows host, treat the mods there as untested.

### Checks to run on a real Windows host

1. **Mods load with no hook errors.** Start `claude --debug` with the mods wired and read the log for hook errors from agent-ctx, context-band, loop-guard and spawn-ledger.
2. **A spawn writes a ledger row, through `py -3`.** On a machine where `python3` is the Microsoft Store stub, spawn any subagent with no `Project:` line. A `spawn_start` row must appear in `%USERPROFILE%\.claude\logs\spawns.jsonl` (`<root>\logs\spawns.jsonl` if you set `AGENCY_HOME` or `CLAUDE_CONFIG_DIR`). The mod probes `python3`, then `CLAUDE_PYTHON`, `py -3`, `python`, and accepts only Python 3.
3. **The Exec cap holds under the Windows lock.** Start six `general-purpose` Execs under one PD at once; the sixth must be denied with the `[spawn-cap]` message (the cap lock is `msvcrt` there, `fcntl` elsewhere).
4. **`ledger.py verify` with a `C:\` path.** Pipe `{"text": "DONE wrote C:\\nope\\x.pdf"}` into `py -3 mods\spawn-ledger\bin\ledger.py verify`; it must print an `ARTIFACT_MISSING` warning naming that path.
5. **A Vietnamese prompt round-trips.** Spawn with a Vietnamese prompt and check the `spawns.jsonl` row and the `ledger.py` output come back intact (the helpers force UTF-8 over a cp1252 default).
6. **The context-band Jev line updates on a large log.** With a `jev-usage.jsonl` over 1 MiB, the Jev line must still update (the band reads the tail; Windows has no `tail`, so it falls back to a python one-liner).

### Known gaps on Windows

- `scripts/skill-route.py` resolves the project from the working directory with `/`-only path logic, so a drive-letter working directory does not match a project there. It only runs when `AGENCY_SKILL_ROUTER=1`. Not changed.
- `hooks/lib/reconcile-stale-spawns.sh` and `hooks/emit-metric.sh` need `bash` (Git for Windows). Without it `ledger.py` skips the stale-spawn sweep.
- `CLAUDE_PYTHON` names one executable path, no arguments. A launcher that needs flags must go through `py -3` or a wrapper.
- If neither `fcntl` nor `msvcrt` loads, or `msvcrt` gives up after about 10 seconds, the Exec cap runs without the lock and parallel spawns can over-count.
- Root resolution is not a gap here: the mods, `ledger.py`, `model-pin.py` and `spawn_project.py` all honour `AGENCY_HOME`, then `CLAUDE_CONFIG_DIR`, then `<home>/.claude`.

Make no claim of Windows support beyond this section.

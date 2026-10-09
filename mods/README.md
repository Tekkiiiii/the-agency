# Mods

Optional Claude Code plugins that ship with The Agency. Each one is a plugin of function hooks that hot-reloads in a running session. Mods need Claude Code 2.1.287 or newer.

- **context-band**: Claude Code shows no running context, cache or usage-window figures above the prompt -> a band with context %, tokens, model, cost, cache warm/cold countdown and 5h/7d reset timers, plus `/ctx` for a detail pane.
- **agent-ctx**: A long-running agent does not notice its own context filling up -> it tells the agent when its own context crosses 70% and 80% (respawn threshold).
- **loop-guard**: An agent repeats the same tool call forever and nobody notices -> it injects a stall warning after five identical calls in a row.
- **spawn-ledger**: Subagent spawns leave no record, the `model` param leaks Opus onto sonnet-pinned agents and nothing caps parallel Execs -> it logs every spawn to JSONL, pins the model, caps Execs per PD, verifies claimed artifacts and relays `RESPAWN_REQUEST`.
- **voice-compact**: The CAVEMAN / PONYTAIL startup injections cost a lot of tokens every session -> it rewrites them into ~150-token compact rules.

## Loading

Manual for now. The installer does not set mods up yet (open owner decision). Pick one:

**(a) Every session.** In your user settings (`~/.claude/settings.json`, or the settings file in your Claude config dir) list the mod folders in `env.CLAUDE_CODE_PLUGIN_DIRS`:

```json
{ "env": { "CLAUDE_CODE_PLUGIN_DIRS": "<root>/mods/context-band:<root>/mods/spawn-ledger" } }
```

- Separator: `:` on macOS and Linux, `;` on Windows.
- Use absolute paths or `~` paths only.
- Project and local settings cannot set it; only user settings count.
- The variable needs Claude Code 2.1.280 or newer.

**(b) One session.** `claude --plugin-dir <root>/mods/<name>`.

`<root>` is your agency root: `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude`. Every mod resolves paths from that root the same way.

Warning: two entries that resolve to the same mod name BOTH load, and its hooks fire twice (verified on Claude Code 2.1.293). Disable one with `"<name>@inline": false` under `enabledPlugins`.

## Overlap with the shell hooks

`hooks/hooks.json` wires two hooks by default that do the same job as a mod. Loading both gives duplicates:

- `loop-detector.sh` (all tools) and `loop-guard`: two stall warnings. Both write the `stall_*` keys of `<root>/session-state.json` idempotently; the shell hook also keeps `.tool-call-tracker.jsonl`. Both honour `.hook-profile` = `minimal`.
- `artifact-verify.sh` (Agent) and `spawn-ledger`: duplicate `ARTIFACT_MISSING` warnings and duplicate rows in `logs/artifact-verify.jsonl`.
- `spawn-logger.sh` and `spawn-completion.sh` are opt-in (see `docs/HOOKS.md`, "Hooks Not Wired By Default"). Wiring them next to `spawn-ledger` gives duplicate `spawn_start` / `spawn_end` rows with different `spawn_id`s. `spawn-logger.sh` also injects the `[[CLAUDE_SPAWN_META]]` marker.
- `agent-ctx` is independent of `context-pct-publish.sh`.

Run one of each pair.

## Dependencies and degradation

| Mod | Reads | Writes | When something is absent |
|-----|-------|--------|--------------------------|
| context-band | session usage from Claude Code; `<root>/memory/metrics/jev-usage.jsonl` and `<root>/state/skill-route/jev-down` (older `<root>/logs/jev-usage.jsonl`, `<root>/state/jev-down` if the new ones are missing; `JEV_USAGE_LOG` and `SKILL_ROUTE_STATE_DIR` override) | nothing | No usage log and no flag: the Jev router row is hidden and the rest of the band draws. Rates are built in; no pricing script needed. |
| agent-ctx | session context percent; `<root>/.hook-profile` | nothing | No `.hook-profile`: standard profile. `minimal` turns the alert off. |
| loop-guard | `<root>/.hook-profile` | `<root>/session-state.json` (`stall_*` keys) | No `.hook-profile`: standard. Unwritable state file: the warning still fires. |
| spawn-ledger | `<root>/memory/medium-term.md` (project registry), `<root>/agents/*.md` (model lookup), `<root>/.hook-profile`, `hooks/lib/model-pin.py` + `exec-model-map.json`, `hooks/lib/claude_pricing.py` (cost), `hooks/lib/reconcile-stale-spawns.sh`, `scripts/skill-route.py` | spawn JSONL (`spawns.jsonl` in the project's `memory/`, else `<root>/logs/`), `<root>/logs/artifact-verify.jsonl`, `<root>/memory/metrics/events.jsonl`, `<root>/state/spawn-slots.jsonl` | No `python3` or no `model-pin.py`: spawns go through unchanged (fail open). No `medium-term.md`: `RESPAWN_REQUEST` slugs are not checked against known projects and the log goes to `<root>/logs/spawns.jsonl`. Skill-route shadow call runs only when `AGENCY_SKILL_ROUTER=1` and `scripts/skill-route.py` exists. `.hook-profile` = `minimal` turns the whole mod off. Kill switches for the pin: `MODEL_PIN_OFF=1`, `state/model-pin.off`; cap only: `SPAWN_CAP_OFF=1`, `state/spawn-cap.off`. |
| voice-compact | the hook-context injections of the caveman / ponytail plugins | nothing | Plugins not installed: nothing to rewrite, the mod does nothing. |

`spawn-ledger` takes cost rates from the shipped `hooks/lib/claude_pricing.py`.

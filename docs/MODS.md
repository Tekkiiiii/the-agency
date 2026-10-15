# Mods

Five optional Claude Code plugins in `mods/` add what shell hooks cannot: a live band above the prompt, nudges when an agent's context fills, stall detection, and a ledger of subagent spawns. They need Claude Code 2.1.287 or newer.

| Mod | Gap it closes | What you get |
|---|---|---|
| `context-band` | Claude Code shows no context, cache or usage-window figures above the prompt | A band with context %, cost, cache countdown and 5h/7d reset timers |
| `agent-ctx` | An agent does not notice its context filling up | The agent is told at 70% and 80% |
| `loop-guard` | An agent repeats the same tool call forever | A stall warning after five identical calls |
| `spawn-ledger` | Subagent spawns leave no record, and nothing pins their model or caps parallel Execs | A JSONL spawn ledger, model pin, Exec cap, artifact check and the [effort policy](SKILLS.md#effort-policy) |
| `voice-compact` | The CAVEMAN / PONYTAIL startup injections cost tokens every session | Compact rules of about 150 tokens |

## Installing

`install.sh`, `install.ps1`, `agency init` and `agency upgrade` copy each mod to `{root}/mods/<name>/` and add it to `env.CLAUDE_CODE_PLUGIN_DIRS` in your user `settings.json`, after your own value. A mod you already provide under the same name wins. With Claude Code older than 2.1.287, or none found, the step is skipped with one line; run `agency mods sync` after updating. Restart Claude Code after any change.

```bash
AGENCY_NO_MODS=1 bash install.sh   # opt out of the automatic step
agency mods status                 # what is wired
agency mods sync                   # wire them now
agency mods remove                 # remove exactly our entries and copies; your value is restored
```

The full install behaviour (what counts as "ours", skipped cases) is in [SETUP.md](SETUP.md#mods).

## Overlap with shell hooks

The shell hooks `loop-detector` and `artifact-verify` stay wired next to the `loop-guard` and `spawn-ledger` mods, so you may see duplicate warnings. [`mods/README.md`](../mods/README.md) explains how to run only one of each pair, how to load a mod by hand, and what each mod reads.

## Windows

On Windows the mods are covered by simulated tests only and are unproven on a real Windows host. See [Windows status](../mods/README.md#windows-status).

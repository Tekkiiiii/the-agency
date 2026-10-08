# Skill router (optional, off by default)

`skill-route.py` picks 0-3 skills from the skill menu for a task text, plus a model tier and a tool profile. It asks Jev (TypeSafe SystemOne) multiple-choice questions, degrades to Haiku through the Claude Code CLI when Jev fails, and to a local grep ranker when that fails too.

**It is disabled.** Nothing calls it: no hook, no `CLAUDE.md` path, no installer step. Default routing stays "pick 1-3 skills from `skills/INDEX.md`". The router runs only when the environment variable `AGENCY_SKILL_ROUTER` is exactly `1`. The Agency ships no key; you bring your own.

Stdlib only, Python 3.9+. Nothing to `pip install`.

Terms: `{root}` = `$AGENCY_HOME`, else `$CLAUDE_CONFIG_DIR`, else `~/.claude` (Windows: `%USERPROFILE%\.claude`). Commands below use the default root; with a custom root, replace `~/.claude` with it and keep `AGENCY_HOME` (or `CLAUDE_CONFIG_DIR`) set when you run the scripts, so they read the same `{root}/skills`.

## Disabled behaviour

With the variable unset, `0`, `true`, or anything but `1`, every `skill-route.py` invocation (any arguments, stdin, `--shadow`, `--rebuild-menu`) prints this one line and exits 0:

```json
{"router":"disabled","enabled":false,"skills":[],"reason":"AGENCY_SKILL_ROUTER is not 1","fallback":"pick 1-3 skills from skills/INDEX.md","enable":"see scripts/skill-route/README.md"}
```

It happens before `jev_client` is imported: no key read, no socket, no `claude -p`, no file written. `jev_client.ask()` refuses too (`RouterUnavailable`, reason `disabled`). `jev-drill.py` and `skill-route-eval.py` print `skill router disabled (set AGENCY_SKILL_ROUTER=1 to run <tool>); nothing run` and exit 0. CI proves the no-network guarantee: `.github/scripts/check-skill-route-disabled.py`.

Work offline whether or not the router is enabled: `jev-gate-check.py --only menu-build`, `skill-route-overlay-add.py`, `jev-feedback.py`, and in-process `load_menu()` / `menu_stats()`.

## Enable

Do the steps in order. **Step 2 must come before step 3**: an enabled router with no key treats every call as a Jev outage (reason `no_key`). It writes the `jev-down` flag, sends a desktop notification on macOS, and answers through `claude -p` Haiku instead (see [Fallback](#fallback-cost-logging-jev-down-flag)).

**1. Get your own Jev key.** Sign up at <https://typesafe.ai> and create an API key for the SystemOne endpoint.

**2. Put the key in the env file.** The secret variable is `TYPESAFE_API_KEY`. It is read from this file only, never from the process environment.

macOS / Linux:

```bash
mkdir -p ~/.config/typesafe && chmod 700 ~/.config/typesafe
( umask 077; printf 'TYPESAFE_API_KEY=your-key-here\n' > ~/.config/typesafe/.env )
chmod 600 ~/.config/typesafe/.env
```

Then replace `your-key-here` with your key in an editor (this keeps the key out of your shell history).

Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\typesafe" | Out-Null
Set-Content -Path "$env:USERPROFILE\.config\typesafe\.env" -Value "TYPESAFE_API_KEY=your-key-here"
```

Then replace `your-key-here` with your key in an editor and save. Only after that, restrict the file to your account (this removes inherited access, so do it last):

```powershell
icacls "$env:USERPROFILE\.config\typesafe\.env" /inheritance:r /grant:r "${env:USERNAME}:(R,W)"
```

- Path: `~/.config/typesafe/.env` (Windows `%USERPROFILE%\.config\typesafe\.env`). Set `JEV_ENV_FILE` to use another path.
- Keep it private: mode `600`, never commit it. The router never prints the key and redacts credential-shaped strings from task text before sending.
- Save the file as UTF-8 (a BOM is accepted).
- Format: `NAME=value` lines, `#` comments, optional `export `, optional quotes. The same file may set non-secret `JEV_MODEL` and `JEV_ENDPOINT` (default `https://api.typesafe.ai/v1/systemone`).
- The installer and `agency upgrade` never create or touch this file.

**3. Turn the switch on.** Set `AGENCY_SKILL_ROUTER` to the string `1`.

Preferred: Claude Code `settings.json` (`~/.claude/settings.json`, Windows `%USERPROFILE%\.claude\settings.json`; with a custom root, the `settings.json` in it). Merge an `env` block into the file; keep your other keys:

```json
{
  "env": {
    "AGENCY_SKILL_ROUTER": "1"
  }
}
```

Claude Code applies the `env` block to the session environment, so Bash tool calls inherit it on macOS, Linux and Windows. A terminal you start yourself does not inherit it; use one of the shell forms below for that.

Shell alternatives:

```bash
# macOS / Linux: this shell only
export AGENCY_SKILL_ROUTER=1
# persistent: add that line to ~/.zshrc or ~/.bashrc
```

```powershell
# Windows PowerShell: this session only
$env:AGENCY_SKILL_ROUTER = "1"
# persistent for new terminals (not the current one)
setx AGENCY_SKILL_ROUTER 1
```

**4. Rebuild the menu.** First run builds it on demand; rebuild explicitly to see problems now.

```bash
AGENCY_SKILL_ROUTER=1 python3 ~/.claude/scripts/skill-route.py --rebuild-menu
```

```powershell
$env:AGENCY_SKILL_ROUTER = "1"; python "$env:USERPROFILE\.claude\scripts\skill-route.py" --rebuild-menu
```

On Windows use whichever of `python`, `py -3` runs Python 3.9+. With a custom root: `AGENCY_HOME=/path/to/root AGENCY_SKILL_ROUTER=1 python3 /path/to/root/scripts/skill-route.py --rebuild-menu`.

It prints menu stats as one JSON line: `{"routable": N, "excluded": N, "excluded_names": {...}, "domains": {...}}`, exit 0. A skill of yours with no overlay entry prints a one-line warning on stderr and is simply not routable until you add it (see [Overlay](#overlay-maintenance)); a broken overlay exits 2 with the problem list on stderr.

**5. Verify.**

```bash
python3 ~/.claude/scripts/jev-gate-check.py --only menu-build
AGENCY_SKILL_ROUTER=1 python3 ~/.claude/scripts/skill-route.py --no-log "build a React landing page with tailwind"
```

Expected from the first: `PASS menu-build: menu builds ...`, then an `INFO skill router switch: off; set AGENCY_SKILL_ROUTER=1 to enable the router (this gate is offline: it reads files only, no network call)` line (it says `on` instead when `AGENCY_SKILL_ROUTER=1` is set in the shell that runs the gate), then `OVERALL PASS`, exit 0. Expected from the second: one JSON object (see [Output contract](#output-contract)) with `"router": "jev"` and `"jev_down": false`. If `"router"` is `"haiku"` or `"grep"` the key is missing, wrong or Jev is unreachable: check step 2, and `{root}/memory/metrics/jev-usage.jsonl` for a line with `"router": "jev", "ok": false`.

If you keep your own skills in `{root}/skills`, the first command can instead print `FAIL menu-build: menu build FAILED ... no overlay entry: NAME`, then `OVERALL FAIL`, exit 1, while routing still works. The gate is strict: it fails on any skill directory with no overlay entry, but the router just leaves such a skill out of the menu. Fix it with `python3 ~/.claude/scripts/skill-route-overlay-add.py NAME [--domain D --hint H]`, or ignore it: the step-4 stats line and the sample route above are the functional check.

**Disable.** Unset the variable (delete the `env` entry, `unset AGENCY_SKILL_ROUTER`, `Remove-Item Env:AGENCY_SKILL_ROUTER`; for `setx` use the Windows environment-variable settings). Logs, state and the key file stay where they are.

**Privacy.** The router sends the task text to the Jev endpoint, and to Anthropic through `claude -p` when it falls back. The client redacts credential-shaped strings and caps the text at 6000 characters; it does no other filtering. Use `--router grep` for text that must not leave your machine.

## CLI

```
skill-route.py [TEXT]                 # or the text on stdin
    [--project SLUG] [--router jev|haiku|grep] [--mode two-stage|flat]
    [--no-log] [--rebuild-menu] [--shadow] [--shadow-report]
```

| Flag | Meaning |
|---|---|
| `--project SLUG` | recorded in the decision log |
| `--router` | `jev` (default), `haiku` (never calls Jev), `grep` (no model call at all) |
| `--mode` | `two-stage` (default: domain question, then skill + model + tools questions) or `flat` (one request over the whole menu; split into chunks of 254 skills + `none`) |
| `--no-log` | skip the decision log `skill-route.jsonl`; the cost log `jev-usage.jsonl` is still written |
| `--rebuild-menu` | rebuild the menu cache; with no text, print menu stats and stop |
| `--shadow`, `--shadow-report` | advanced; nothing shipped calls them |

Exit codes: `0` ok (including disabled), `2` usage error, no task text, or a broken menu/overlay (`MenuError` on stderr, stdout empty).

In-process: load the file with `importlib.util.spec_from_file_location("skill_route", "<root>/scripts/skill-route.py")` and call `route(text, project=None, router=None, mode=None, log=True, cwd=None)` and `load_menu(rebuild=False)`. `route()` never prints and raises only `MenuError`; any Jev/Haiku/network failure degrades to the grep router.

### Output contract

One JSON object on stdout:

```json
{"skills": ["frontend"], "model": "sonnet", "tools": "edit",
 "scores": {"frontend": 1.0, "ui-ux-pro-max": 0.0},
 "domain": "frontend-ui", "router": "jev", "gate": "pass",
 "pre_rules": [], "lang": "en", "jev_down": false}
```

| Key | Values |
|---|---|
| `skills` | 0-3 menu names. Rank 1 whenever a skill fits; ranks 2-3 only at probability >= 0.15. `[]` = no listed skill fits (the `none` option won, the grep router found no word overlap, or the text was empty); `gate` is then `low_confidence`. Treat `[]` as "spawn without a skill". |
| `scores` | top-3 real candidates with probability > 0 (`none` is never a key). Two-stage: raw stage-2 probabilities. Flat: merged probability. Grep: relative overlap share, not calibrated. |
| `domain` | stage-1 answer (two-stage), or the domain of `skills[0]` (flat, grep); `null` when `skills` is `[]` and no domain was chosen |
| `model` | `haiku` / `sonnet` / `opus`. `tools`: `read-only` / `edit` / `web` / `full`. Grep and passthrough use `sonnet` / `edit`. |
| `router` | `jev`, `haiku`, `grep`, or `passthrough` |
| `gate` | `pass` or `low_confidence`. Two-stage passes when domain p x skill p >= 0.50 and domain p x (skill p1 - skill p2) >= 0.10. Flat passes when top-1 >= 0.45 and top-1 - top-2 >= 0.10. The grep router is always `low_confidence`. |
| `pre_rules` | rules that fired: `explicit`, `vietnamese` |
| `lang` | `en` or `vi` |
| `jev_down` | the `jev-down` flag is present after the call |

Pre-rules:

1. `explicit`: `/name` tokens that match menu skills (case-insensitive, max 3) are returned as-is, `router: "passthrough"`, `gate: "pass"`, no model call. Paths (`/usr/x`, `a/frontend/src`), URLs and unknown names do not count.
2. `vietnamese`: `lang: "vi"` when the text has >= 3 Vietnamese-only diacritic characters or matches `tiếng Việt|Vietnamese|VN`. Chosen skills map through the overlay `vi_map` (for example `humanizer` to `humanizer-vi`); `en_only` skills are dropped; an emptied list becomes `content-polish`.

Sample outputs, captured on a fresh sandbox install (`AGENCY_HOME` set to a temp dir; run from `{root}`):

```text
# disabled (variable unset)
$ python3 scripts/skill-route.py "build a landing page"
{"router":"disabled","enabled":false,"skills":[],"reason":"AGENCY_SKILL_ROUTER is not 1","fallback":"pick 1-3 skills from skills/INDEX.md","enable":"see scripts/skill-route/README.md"}

# enabled, no key file, Haiku fallback unavailable -> grep (degraded)
$ AGENCY_SKILL_ROUTER=1 JEV_ENV_FILE=/nonexistent JEV_HAIKU_CMD=/usr/bin/false JEV_NOTIFY=0 JEV_EMIT=0 \
    python3 scripts/skill-route.py "build a React landing page"
{"skills": ["frontend", "ui-ux-pro-max", "design-taste-frontend"], "model": "sonnet", "tools": "edit", "scores": {"frontend": 0.2485, "ui-ux-pro-max": 0.2485, "design-taste-frontend": 0.1905}, "domain": "frontend-ui", "router": "grep", "gate": "low_confidence", "pre_rules": [], "lang": "en", "jev_down": true}

# explicit /name passthrough
$ AGENCY_SKILL_ROUTER=1 python3 scripts/skill-route.py --no-log "/frontend /tailwind do it"
{"skills": ["frontend", "tailwind"], "model": "sonnet", "tools": "edit", "scores": {"frontend": 1.0, "tailwind": 1.0}, "domain": "frontend-ui", "router": "passthrough", "gate": "pass", "pre_rules": ["explicit"], "lang": "en", "jev_down": true}
```

(`jev_down` is `true` because the no-key call created the flag in `{root}/state/skill-route/`; the passthrough call only reports it.)

## Menu

Built from `{root}/skills/*/SKILL.md` (depth 1; directories starting with `_` or `.` and nested directories are not in the menu): frontmatter `description`, plus `skills/INDEX.catalog.json` triggers if present, plus the overlay (`domain`, `hint`, `exclude`), plus the overlay `synthetic` entries (harness built-ins that have no `SKILL.md`: `code-review`, `simplify`, `security-review`, `plugin-authoring`, `claude-api`, `update-config`, `keybindings-help`, `fewer-permission-prompts`, `dataviz`; a real `SKILL.md` of the same name wins).

- Every skill question ends with a `none` option ("no listed skill fits"). A question holds at most 254 skills + `none`.
- The Jev `state` is the task text only; menu text lives in the question criteria. Question text shrinks in steps (down to 60 characters per description) before a skill would ever be dropped.
- Cache: `{root}/state/skill-route/skill-route-menu.json` (`SKILL_ROUTE_STATE_DIR` moves it). Rebuilt when any `SKILL.md`, the overlay or the catalog is newer than the cache, when the set of skill directories changes, or with `--rebuild-menu`.
- The shipped overlay assigns the 243 shipped skills to 16 domains or excludes them (`exclude`, for example internal session skills); 232 are routable with the 9 synthetic entries.

## Overlay maintenance

`scripts/skill-route/overlay.json` assigns each skill directory a routing `domain` and `hint`, or an `exclude` reason. Shapes:

```json
"my-skill":  {"domain": "frontend-ui", "hint": "Use to BUILD X; not for Y (other-skill)."}
"internal":  {"exclude": "internal", "why": "not offered to the router"}
```

Optional keys on a routable entry: `also_domains` (list; also offer the skill when stage 1 picks one of those domains; two-stage only), `why`. Top-level keys: `domains` (name to description), `skills`, `synthetic`, `vi_map`, `en_only`, `notes`. The `hint` text is where near-duplicate skills are told apart ("use when X; not when Y"); do not edit `SKILL.md` for routing.

Rules:

- A skill directory with no overlay entry is a **contributor error** and fails CI (below). For a user it is not an outage: at runtime the skill is left out of the menu and the CLI prints one stderr line, `skill-route.py: warning: N skill(s) have no overlay entry and are not routable: a, b. Fix: python3 <scripts dir>/skill-route-overlay-add.py NAME [--domain D --hint H]`.
- Every other overlay problem fails loud (`MenuError`, exit 2, problems listed on stderr, cache not written): an entry with neither `domain` nor `exclude`, an unknown `domain` or `also_domains` name, an unreadable overlay, or an empty menu.
- `jev-gate-check.py --only menu-build` is strict: a missing entry is a FAIL.

Add an entry for a new skill:

```bash
python3 scripts/skill-route-overlay-add.py NAME                                # default: excluded as "internal"
python3 scripts/skill-route-overlay-add.py NAME --domain frontend-ui --hint "Use to build X; not for Y"
```

| Arg | Meaning |
|---|---|
| `NAME` | skill directory name (no `/`, not starting with `.` or `_`) |
| `--domain D` | make it routable; `D` must be a key of `overlay["domains"]` |
| `--hint H` | routing hint (needs `--domain`) |
| `--why W` | reason text |

Output: `added: NAME` (exit 0), `exists: NAME` (exit 0, existing entries are never overwritten), `exists (invalid entry: <why>): NAME` on stderr (exit 1, fix by hand), usage errors exit 2 (`error: unknown domain 'x'; valid domains: ...`), unreadable overlay exit 1. The write is atomic and idempotent, parallel-safe where `fcntl` exists, and keeps the file's formatting. It edits the overlay next to the script (`SKILL_ROUTE_OVERLAY` overrides). Run it from the repo for a contributor change, or from `{root}/scripts/` for an installed copy.

`agency upgrade` and the installers overwrite `{root}/scripts/skill-route/overlay.json` with the shipped one. Entries you added for your own skills are lost on upgrade (those skills become "unassigned", not an outage). To keep them: re-run `skill-route-overlay-add.py` after upgrading, or keep a private overlay (a copy of the shipped file plus your entries) and point `SKILL_ROUTE_OVERLAY` at it, re-merging shipped changes yourself.

### CI gate

`.github/scripts/check-skill-route-menu.py` (exit 0 PASS, 1 FAIL; no network, no key, no switch):

1. `overlay["skills"]` keys equal the set of shipped depth-1 skill directories, exactly.
2. `load_menu(rebuild=True)` builds on the real skills and overlay.
3. Fail-safe proof: a copy of the overlay with one skill removed must raise `MenuError` naming it; no domain, an unknown domain and an unknown `also_domains` entry must raise too. If the builder ever stops being strict, the gate fails.
4. `jev-gate-check.py --only menu-build` exits 0 on the real overlay and 1, naming the skill, on the stripped one.
5. Zero network attempts, in this process and its children.

`.github/scripts/check-skill-route-disabled.py` runs the real script with the switch off (several argument shapes, stdin, `--shadow`) behind a socket/subprocess guard and asserts the pinned line, zero connections, zero spawns, and no files written; a positive control with the switch on proves the guard sees traffic.

## Fallback, cost logging, jev-down flag

Failure handling, in order:

1. **Jev** (`https://api.typesafe.ai/v1/systemone`, 2 s timeout). Outage class: timeout, connection error, redirect, 401/403/408/429, 5xx, an unparseable body, or a missing key. Bad-request class: 400, 422 and other 4xx (your request or endpoint config is wrong). Both fall back to Haiku.
2. **Haiku** through `claude -p --model haiku` (the `claude` executable on `PATH`, or `JEV_HAIKU_CMD`). The Claude Code CLI must be installed and logged in. The child runs in an empty temp directory with no tools, no MCP servers, no hooks, no settings and no session persistence, and its environment drops `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `TYPESAFE_API_KEY` and the parent-session variables, so it can only use the logged-in subscription, never a billed key. A 60 s timeout applies; malformed output is repaired once.
3. **Grep**: a local word-overlap ranker. No network. Always `gate: "low_confidence"`.

`jev-down` flag: `{root}/state/skill-route/jev-down` (JSON `since`, `last_failure`, `reason`, `failures`). The first outage creates it, records a `down` line in `{root}/memory/metrics/jev-notify.log` and, on macOS, shows one desktop notification ("Jev router down"; `JEV_NOTIFY=0` suppresses it). Later outages only update the flag. The first Jev success removes it, logs `up` and notifies once ("Jev router back up"). Bad-request failures never set the flag. `jev_down` in the output reports it.

Logs (append-only JSONL under `{root}/memory/metrics/`):

| File | Content |
|---|---|
| `jev-usage.jsonl` | one line per call attempt, Jev and Haiku: `ts`, `purpose`, `router` (`jev`/`haiku`), `model`, `input_tokens`, `output_tokens`, `usd`, `latency_ms`, `ok`, `shadow`. A failed Jev attempt that falls back writes a Jev line with `ok: false` and 0 tokens, then the Haiku line. Written even with `--no-log`. |
| `skill-route.jsonl` | one decision per route: text excerpt (200 chars), mode, router, domain, probabilities, `skills`, `scores`, `model`, `tools`, `gate`, `lang`, `pre_rules`, `jev_down`, `calls`, tokens, `usd`, `latency_ms`. Skipped by `--no-log`. |
| `jev-notify.log` | `<timestamp><TAB>down|up` |
| `jev-feedback.jsonl` | reviewer feedback (`jev-feedback.py`) |

`usd` is an estimate. Jev: `input_tokens x JEV_USD_PER_M_INPUT / 1e6` (a constant in `jev_client.py`; TypeSafe's own billing is authoritative). Haiku: `hooks/lib/claude_pricing.py` if present under `{root}`, else the CLI's `total_cost_usd`.

## Environment variables

All optional except the switch.

| Variable | Default | Meaning |
|---|---|---|
| `AGENCY_SKILL_ROUTER` | unset | `1` enables; anything else disables |
| `JEV_ENV_FILE` | `~/.config/typesafe/.env` | file holding `TYPESAFE_API_KEY` (and optional `JEV_MODEL`, `JEV_ENDPOINT`) |
| `JEV_ENDPOINT` | `https://api.typesafe.ai/v1/systemone` | overrides the file; non-secret |
| `JEV_MODEL` | `jev-latest` | overrides the file; non-secret |
| `AGENCY_HOME`, `CLAUDE_CONFIG_DIR` | `~/.claude` | root, in that precedence |
| `SKILL_ROUTE_SKILLS_DIR` | `{root}/skills` | skills directory |
| `SKILL_ROUTE_OVERLAY` | `<scripts>/skill-route/overlay.json` | overlay file |
| `SKILL_ROUTE_STATE_DIR` | `{root}/state/skill-route` | menu cache, `jev-down` flag, shadow kill switch |
| `SKILL_ROUTE_LOG` | `{root}/memory/metrics/skill-route.jsonl` | decision log |
| `SKILL_ROUTE_SHADOW_LOG` | `{root}/memory/metrics/skill-route-shadow.jsonl` | shadow log |
| `JEV_USAGE_LOG` | `{root}/memory/metrics/jev-usage.jsonl` | cost log |
| `JEV_NOTIFY_LOG` | `{root}/memory/metrics/jev-notify.log` | down/up log |
| `JEV_NOTIFY` | on | `0` skips the macOS notification (the log line is still written) |
| `JEV_EMIT` | on | `0` skips `{root}/hooks/emit-metric.sh` events (`jev_down`, `jev_up`, `jev_bad_request`, `jev_haiku_fallback`) |
| `JEV_HAIKU_CMD` | `claude` | path of the Claude Code executable for the Haiku fallback |
| `JEV_PURPOSE` | `skill-route` | `purpose` written to the usage log (the eval and drill set their own) |
| `SKILL_ROUTE_CHILD` | unset | `1` stops the router from spawning `claude` (recursion guard, set for the Haiku child) |

Files created under `{root}`: `state/skill-route/` (menu cache, `jev-down`, lock files) and `memory/metrics/*.jsonl`. Nothing is created while disabled.

## Maintainer tools

All in `scripts/`. Stdlib only. Run them with the same root as the router.

**`jev-gate-check.py [--json] [--only NAME ...]`**: offline readiness gate. Reads files, opens no connection, needs no key and no switch. One line per criterion `PASS|FAIL name: value (threshold) source`, then `OVERALL PASS|FAIL`. Exit 0 only on overall PASS, 1 on FAIL, 2 on input error. Criteria:

| Criterion | Passes when |
|---|---|
| `menu-build` | the menu builds fresh with `load_menu(rebuild=True)`; a skill with no overlay entry FAILS (names it and prints the `skill-route-overlay-add.py` fix). Computed live, not subject to the staleness guard. Rewrites the menu cache (set `SKILL_ROUTE_STATE_DIR` to a temp dir in CI). |
| `skill-route-gated-accuracy` | latest eval result (`router=jev`, `split=all`, the default mode): accuracy among `gate=pass` rows >= 0.95 AND coverage (share of scored rows with `gate=pass`) >= 0.70, no outage rows |
| `outage-drill` | latest drill result ran steps `s1`-`s4` and passed |
| `shadow-window` | >= 7 days since the earliest shadow/feedback record, or >= 50 gated tasks |

The last three only read result files written by the opt-in tools below and print `run: <command>` when absent. Results go stale by content hash (`jev_fingerprint.py`: AST of `skill-route.py` + `jev_client.py`, plus the routable menu), not by mtime. `--only NAME` evaluates just that criterion; `--only menu-build` reads no result file. Input paths: `JEV_GATE_SKILL_ROUTE_RESULTS`, `JEV_GATE_DRILL_RESULTS`, `JEV_GATE_SKILL_ROUTE_SHADOW`, `JEV_GATE_FEEDBACK`, `JEV_GATE_SKILL_ROUTE_MODE`, `JEV_GATE_NOW`, `JEV_GATE_SCRIPTS_DIR`.

**`jev-drill.py`**: outage drill. Needs `AGENCY_SKILL_ROUTER=1`, calls the real endpoint with your real key in step `s4`, and needs the `claude` CLI (steps `s1`-`s3` degrade to Haiku). Four subprocess steps: `s1` bogus key gives 401, so haiku, flag created, one `down` line; `s2` repeat, flag count up, no new line; `s3` slow local server gives timeout, so haiku; `s4` real key gives `jev`, flag removed, one `up` line. Uses an isolated state dir by default (`--real-state` uses `{root}/state/skill-route` and refuses if `jev-down` exists). Dry run: `AGENCY_SKILL_ROUTER=1 python3 scripts/jev-drill.py --no-notify --notify-log /tmp/n.log --events off --results-dir /tmp/res --usage-log /tmp/u.jsonl`. Writes `{root}/evals/jev-drill/results/<date>.json`; exit 0 only if every executed step passes.

**`skill-route-eval.py`**: scores the router against labelled tasks. Needs `AGENCY_SKILL_ROUTER=1`; costs real Jev calls (logged with purpose `eval`).

```bash
AGENCY_SKILL_ROUTER=1 python3 scripts/skill-route-eval.py --router jev --mode two-stage --split all [--limit N] [--concurrency 4] [--seed FILE]
```

**The seed is not shipped.** Write your own `{root}/evals/skill-route/seed.jsonl`, one object per line: `{"id": "t1", "task": "build a React landing page", "expected_skills": ["frontend"], "split": "dev|holdout", "lang": "en", "source": "hand"}` (`split`, `lang`, `source` optional; `"expected_none": true` with `[]` means no skill fits; `"unscored": true` excludes the row). Confirmed mismatches from `jev-feedback.jsonl` are added automatically. Optional `{root}/evals/skill-route/prerules.jsonl` assertions run against a loopback counting server and a counting `claude` stub, so they never spend money. Output: top-1, top-3, gate-pass rate, top-1 among `gate=pass`, per-split tables, cost; results in `{root}/evals/skill-route/results/`. Exit 0 ok or disabled, 1 a prerule assertion failed, 2 usage/IO error.

**`jev-feedback.py`**: reviewer feedback log (offline, local file, works with the router off). Subcommands: `add --project P --task-id ID --verdict SKILL --router jev|haiku|grep|passthrough --review agree|disagree [--reason R] [--task-text T]`; `outcome TASK_ID ok|wrong_skill [--correct-skills a,b]`; `mismatches` (confirmed mismatches as JSONL). `--file` or `JEV_FEEDBACK_LOG` selects the file (default `{root}/memory/metrics/jev-feedback.jsonl`). Task text is redacted before it is stored.

## Files

| Path | Role |
|---|---|
| `scripts/skill-route.py` | router CLI and module |
| `scripts/jev_client.py` | Jev client, Haiku fallback, redaction, usage log, outage flag |
| `scripts/jev_fingerprint.py` | content hash used by the gate |
| `scripts/skill-route/overlay.json` | domains and per-skill routing data |
| `scripts/skill-route-overlay-add.py` | add overlay entries |
| `scripts/jev-gate-check.py`, `jev-drill.py`, `skill-route-eval.py`, `jev-feedback.py` | maintainer tools |
| `.github/scripts/check-skill-route-menu.py`, `check-skill-route-disabled.py` | CI gates |
| `cli/lib/skill-router.js` | prints the `Skill router: disabled (...)` / `enabled` line for the installers |

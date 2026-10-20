# The Agency

**The only repo you need to fix Claude Code's problems.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)

It is Monday. You open Claude Code on the project you were deep in last week, and before any work starts you explain it all again: the approach you dropped, the part waiting on someone else, the file you were halfway through. Later that week an agent tells you the report is written and the folder is empty, and the usage window runs dry with no way to tell which job spent it.

The Agency is a set of plain files you install on top of Claude Code. Each part goes after one problem like these. Each part below says what it does today, what it needs from you, and what ships switched off.

---

## Install

```bash
# Clone anywhere except ~/.claude (that folder already exists if you use Claude Code)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency

bash install.sh        # macOS / Linux
.\install.ps1          # Windows (PowerShell)
```

The installer copies skills, agents, hooks and the `agency` command into your Claude Code config directory (`~/.claude/` by default; it prints a `Sync root:` line naming the one it used) and merges its hooks into `settings.json` next to yours, with a backup. Keep the clone: `agency upgrade` pulls it and re-syncs.

```bash
agency onboard                                           # guided setup, start here
agency new invoice-app "Invoicing for a two-person design studio"
```

Open Claude Code and run `/recall invoice-app`. A new project answers "no prior session found". Tell Claude what to build, and run `/save-state` when you stop.

Already cloned? `node cli/bin/agency.js init` does the same sync. Install broken, or no clone at all? This finds your clone, pulls it, repairs a broken state, and clones to `~/the-agency/` if there is none:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

---

## What it fixes

### Claude Code forgets the project when the session ends

Monday's re-explaining is the price of a blank start. A restaurant kitchen avoids it with a prep list taped to the fridge: the closing cook writes down what is half done, and the morning shift reads it before touching a knife. `/save-state` is that list for your project. It writes the phase, the next step, what is blocked, the decisions you locked and the work in flight into one short file, plus a dated session log. `/recall` is the morning shift reading it:

```
/recall invoice-app

RECALL — invoice-app
Phase: PDF export
Next: add the VAT line to the invoice template
Blockers: client has not sent the tax ID format
Decisions: totals are computed on the server
Mid-flight: templates/invoice.html, half styled
Context: export works for one-page invoices, multi-page breaks
```

The same file carries a job across days. `/pd-resume invoice-app` starts a project lead, the session that plans the work and hands pieces to helpers, from that file and a short briefing. `agency new` registers each project so `/recall` can find it.

You run `/save-state` yourself; nothing saves for you. If a session dies without a clean stop, the next one opens with:

```
NOTICE: Previous session may have ended uncleanly (last clean stop: <timestamp>).
  Run /recall [slug] or /save-state [slug] to check project state.
```

### Long jobs stall halfway, or come back "done" with nothing behind them

A job that takes days needs more than one prompt. The project lead splits it into pieces, hands each to a helper (a subagent that gets one to three skills) and runs independent pieces in parallel. A piece is accepted on evidence. `/qa-only` tests a running app and reports a health score with screenshots and repro steps, and a piece with critical findings goes back to a fresh helper with the fix list. Anything bigger than a one-file change gets an approach check before work starts and a check-in halfway.

A kitchen checks at the pass, where someone counts the plates against the order ticket before anything leaves. When a helper reports a finished PDF, page, image, clip or data file, a hook looks for that file on disk:

```
[artifact-verify] <timestamp> ARTIFACT_MISSING WARNING
[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:
  MISSING: /path/to/report.pdf
```

Each write of a deliverable-shaped file also leaves a row with its path and byte count, so a "done" claim can be checked against a record. For prose, `/cc-loop` sends a draft past critics who score it, and back for another round, up to three.

The check confirms a file exists, not that it is right, and it warns while the run carries on. The QA gate, the rework loop and the hand-over format are instructions that the lead and helpers follow; no code enforces them.

### Context fills up without a word

An agent deep in a job has no sense of how full its context is. The `agent-ctx` mod tells it when its context passes 70 percent. At 80 percent it asks the agent to save and hand over:

```
CONTEXT_PCT_ALERT: 80% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.
```

A fresh agent then picks up from the saved files. A project lead that needs a fresh start says so with a `RESPAWN_REQUEST <project>` line, and a toast tells you which `/pd-resume` to run.

You get the same view yourself. A band above the prompt shows context percent, tokens, model, cost so far, a countdown for the prompt cache, and when your 5-hour and 7-day usage windows reset. `/ctx` opens the detail.

### The usage window empties and you cannot say which job spent it

A kitchen keeps the receipt for every service, so the owner can see where the money went. Each time a session stops, the cost log (`metrics/costs.jsonl`) gets a row with tokens and cost, priced model by model. Every helper run adds rows to `spawns.jsonl` with its model and cost, because the session row leaves helper transcripts out.

Less gets spent in the first place. Code search runs on the small Haiku model. Project questions are answered from your memory files before any helper is spawned. A cap on running helpers refuses the next one with a `[spawn-cap]` message until a slot frees up. If you use the caveman or ponytail plugins, the `voice-compact` mod rewrites their long startup instructions into about 150 tokens of rules; without those plugins it does nothing.

This tells you where usage went. It cannot give back usage already spent, and the cap counts helpers, not price.

### Every task runs on the same model at the same effort

A quick lookup runs on your most expensive model, and a hard refactor gets the same thinking time as a typo fix. The Agency sets the model by role and the effort by kind of task, on every spawn, and its setting wins over whatever the caller asks for.

- **Project lead:** Opus, medium effort.
- **Critics** (code, security, design, copy, brand, search, video and more): Opus, high effort.
- **Helpers:** Sonnet. A call that asks for another model is pinned back to Sonnet; the option for a helper to ask for Opus with a reason ships switched off.
- **Code search:** Haiku, low effort.

Helpers get their effort from the kind of task:

| Kind of task | Effort | Fresh install | With the skill router |
|---|---|---|---|
| Hard code: debugging, refactors, migrations, security | high | when the brief is tagged `MODEL-CATEGORY: debug` | when the job reads as complex code |
| Routine code | medium | medium | medium |
| Visual work: pages, images, video, decks | high | medium | high |
| English writing | high | medium | high |
| Vietnamese writing | xhigh | medium | xhigh |
| Quick lookup | low | when tagged `MODEL-CATEGORY: lookup` | when tagged `MODEL-CATEGORY: lookup` |
| Anything else | medium | medium | medium |

Read the right-hand columns first. On a fresh install the skill router is off: `AGENCY_SKILL_ROUTER` is unset, nothing calls the router and it makes no network request. The roles above keep their model and effort, and helpers fall back to medium unless the brief carries a tag. Setting `AGENCY_SKILL_ROUTER=1` turns the router on, and it needs a routing key from your own account. The router reads each helper's task, picks one to three skills for it and names the kind of job, and the effort in the last column follows. Setup steps are in [`scripts/skill-route/README.md`](scripts/skill-route/README.md). Model pinning and effort need Claude Code 2.1.287 or newer; older versions skip them.

### It deletes more than you meant, and it leaks keys

An agent pastes a token into a shell command, or a cleanup reaches into folders you never named. Hooks check before either happens, and one stops an agent from "fixing" a failing lint rule by loosening the config:

- **Secrets in commands.** Before a shell command runs, the scanner looks for GitHub, Slack, Google and AWS tokens, JWTs and `api_key=` assignments, and asks you first:

  ```
  [secret-scanner] Command contains what looks like a GitHub token. Use env vars or keychain instead of inline credentials.
  ```

- **Config edits.** An existing linter or formatter config (ESLint, Prettier, Biome, Ruff, ShellCheck, Stylelint, markdownlint) cannot be edited. The message tells the agent to fix the code, not the config.
- **Sensitive files.** Writes to `settings.json`, agent definitions, hook scripts and `SKILL.md` files, or a write whose content looks like a token, get a warning before they land.
- **Settings at session start.** A check warns if your `settings.json` holds tokens in plain text.
- **`/guard`.** Switch it on when you touch production. It warns before `rm -rf`, `DROP TABLE`, `git push --force` and `git reset --hard`, and it keeps edits inside the one folder you name (`/careful` and `/freeze` are its two halves).

For review, `/security` checks code against the common web risks, `/cso` runs a full audit, and `/security-critique` grades the result.

Profiles set how hard the hooks push, through `~/.claude/.hook-profile`: `standard` (the default) asks on secrets and warns on sensitive files, `strict` refuses both, `minimal` turns them off. The scanner reads shell commands only, so a `.env` that an agent opens with its file tool never passes through it. `/guard` is off until you invoke it. Rules that live only as instructions, such as waiting for your yes before a deploy, have no code behind them.

### The same failing call runs until you press Escape

The `loop-guard` mod and the `loop-detector` hook both watch for five identical tool calls in a row. When it happens, the agent sees:

```
[loop-detector] STALL DETECTED: 5 identical Bash calls in a row.
```

The message tells it to restate the goal, check the real state of the files, try a different approach, or save and stop. The stall is also noted, and the next session opens with a warning that an agent looped, so you check whether the task finished. The warning does not stop the run, and a loop that varies each call passes. You may see a warning twice, because the shell hook and the mod overlap; [docs/MODS.md](docs/MODS.md) shows how to keep one.

### Plans and reviews arrive as a wall of chat

`/html-plan-style` turns plans, reports and reviews into styled pages you open in a browser. Work passes between agents in a fixed hand-over format (`core/nexus/HANDOFF.md`). Brand colours and fonts live as JSON in `design-system/`, and the CSS the design skills use is generated from them, so the palette stops drifting from file to file. A local task list sits behind `agency tasks` (it needs `npm install better-sqlite3` first). Nothing forces an agent to use the page style or the hand-over format.

### One opinion is not enough for a hard call

`/codex` hands your diff to the Codex CLI you install, for a review, an adversarial attempt to break it, or a free-form second opinion. Convene the council and the same question goes to one reviewer per Claude model tier in a single wave; you get a table of verdicts, agreements and disagreements. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#agency-council).

---

## Skills for the work around the code

Skills are instructions Claude Code loads for one kind of work, invoked as `/name`. The full list, with descriptions, is in [skills/INDEX.md](skills/INDEX.md).

| Domain | Skills |
|---|---|
| Frontend and UI | `/frontend`, `/ui-ux-pro-max`, `/shadcn-ui`, `/next-best-practices` |
| Design direction and review | `/impeccable`, `/design-consultation`, `/design-review`, `/design-taste-frontend` |
| Image prompts | `/gpt-image-prompts`, `/image-prompt-engineer` |
| Backend, data and deploy | `/backend`, `/postgresql-schema`, `/supabase-deploy`, `/vercel-deploy`, `/railway-deploy`, `/land-and-deploy` |
| Debugging, testing and review | `/superpowers-systematic-debugging`, `/superpowers-test-driven-development`, `/investigate`, `/review`, `/qa`, `/webapp-testing` |
| Security | `/security`, `/cso`, `/security-critique` |
| Browser and web data | `/lightpanda`, `/agent-browser`, `/firecrawl-scrape`, `/scrape` |
| English writing | `/content-polish`, `/humanizer`, `/stop-slop`, `/proofreader`, `/tech-writer`, `/simple-english` |
| Vietnamese writing | `/humanizer-vi`, `/grammar-checker-vi`, `/translationese-cleaner-vi`, `/style-guide-vi` |
| Marketing, content and SEO | `/copywriting`, `/content-strategy`, `/content-creator`, `/pipeline-seo-geo-aeo`, `/marketing-critique`, `/inbound-sales` |
| Video and audio | `/hyperframes`, `/video-use`, `/subtitle-burner`, `/ffmpeg`, `/musicgen` |
| Decks, documents and reports | `/marp`, `/deck-narrative`, `/strategic-deck`, `/make-pdf`, `/markitdown`, `/xlsx-toolkit` |
| Planning | `/superpowers-writing-plans`, `/plan-eng-review`, `/plan-ceo-review`, `/office-hours`, `/pipeline-feature` |
| Research | `/auto-researcher`, `/pipeline-research`, `/graphify` |
| Google Workspace | `/gws` for Gmail, Drive, Docs, Sheets, Calendar |
| Cloud cost | `/finops` |
| Career | `/career-ops`, `/cover-letter-gen` |
| Memory and system | `/save-state`, `/recall`, `/lint-memory`, `/context-save`, `/skill-creator` |

---

## What runs by default

| Part | Fresh install | What it needs |
|---|---|---|
| `/save-state` and `/recall` | Available | You run `/save-state` |
| Missing-file check, edit trail, crash notice, loop warning | On | Warns; never stops the run |
| Secret scanner, config protection, sensitive-file warning | On, `standard` profile | `strict` to refuse instead of ask |
| `/guard` | Off until you invoke it | |
| Context alerts, band, cost rows, helper cap, model pin, effort by role | On, as mods | Claude Code 2.1.287 or newer |
| Effort by kind of task for helpers | Off; helpers get medium | Skill router and your own routing key |
| Short-reply rewrite | On, idle | The caveman or ponytail plugin |
| QA gate, rework loop, hand-over format | Instructions | Followed by the agents, not enforced by code |
| `agency tasks` | Needs a package | `npm install better-sqlite3` |

The mods live in [mods/](mods/) and install with the rest; `AGENCY_NO_MODS=1` skips them and `agency mods remove` undoes them. Everything is plain files on your machine, with no servers to run and no extra keys; only the optional skill router needs one. The installers and mods pass CI on Windows; proof on a real Windows machine is still pending.

---

## Credits

Not everything here was made by one person. The memory design is inspired by Andrej Karpathy's LLM Wiki idea. The token-saving mode builds on the caveman and ponytail plugins, and `/self-healing` is inspired by Hermes Agent. Many skills started as other people's open-source work. [CREDITS.md](CREDITS.md) names each source, its author and its licence.

---

## Docs

| Guide | What it covers |
|-------|----------------|
| [User Guide](docs/GUIDE.md) | Install, quick start, and a walkthrough from clone to shipped feature |
| [Setup](docs/SETUP.md) | Prerequisites, upgrades, optional integrations, troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | The project lead and helper chain, QA gates, memory, hand-overs, routing, model tiers, council |
| [Skills](docs/SKILLS.md) | Skills by domain, pipelines, the optional skill router, the effort policy |
| [Hooks](docs/HOOKS.md) | Every lifecycle hook, profiles, settings wiring |
| [Mods](docs/MODS.md) | The five optional Claude Code mods |
| [Developer Guide](docs/DEVELOPER.md) | Repo layout, adding skills and agents, testing |
| [Install Layout](docs/INSTALL-LAYOUT.md) | What each installer deploys and where the root comes from |

## Contributing

Most contributions are skills: a folder `skills/<name>/SKILL.md`, registered and routed as described in [docs/DEVELOPER.md](docs/DEVELOPER.md).

## License

MIT. Use it however you want. Repo: [github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency).

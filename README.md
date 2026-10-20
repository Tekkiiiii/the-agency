# The Agency

**The only repo you need to fix all of your AI IDE's problems.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)

Monday morning. You open Claude Code on last week's project and spend the first half hour explaining it again: the approach you dropped, the file you were halfway through, the part still waiting on someone else. By Thursday an agent has told you the report is written, and you open the folder to find it empty. On Friday the usage window runs dry and you cannot say which job spent it.

These are habits of the tool, and each one has a fix. The Agency installs on top of Claude Code as plain files you can open and read. Each section below shows one fix at work and says how far it goes on a fresh install.

---

## Install

```bash
# Clone anywhere except ~/.claude (that folder already exists if you use Claude Code)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency

bash install.sh        # macOS / Linux
.\install.ps1          # Windows (PowerShell)
```

The installer copies skills, agents, hooks and the `agency` command into your Claude Code config folder (`~/.claude/` unless you set another; its `Sync root:` line names the one it used). It merges its hooks into `settings.json` beside yours and keeps a backup. Keep the clone, because `agency upgrade` pulls it and syncs again.

```bash
agency onboard                                           # guided setup, start here
agency new invoice-app "Invoicing for a two-person design studio"
```

Open Claude Code and run `/recall invoice-app`. A new project answers "no prior session found". Tell Claude what to build, and run `/save-state` when you stop.

Cloned already? `node cli/bin/agency.js init` runs the same sync. If an install breaks, or you have no clone yet, the rescue script finds your clone, pulls it, repairs it, and clones to `~/the-agency/` when there is none:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

---

## What it fixes

### Every session starts from zero

A restaurant kitchen solves this with a prep list taped to the fridge. The closing cook writes down what is half done, and the morning shift reads it before anyone picks up a knife. `/save-state` writes that list for your project: the phase, the next step, what is blocked, the decisions you locked and the work in flight, in one short file plus a dated session log. `/recall` reads it back:

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

`/pd-resume invoice-app` starts a project lead from the same file, a session that plans the work and hands pieces to helpers, so a job that runs for days picks up where it stopped. The save is yours to run. If a session dies before you run it, the next one opens with:

```
NOTICE: Previous session may have ended uncleanly (last clean stop: <timestamp>).
  Run /recall [slug] or /save-state [slug] to check project state.
```

### Long jobs stall, or come back "done" with nothing behind them

A feature that takes days needs more than one prompt. The project lead splits it into pieces and hands each one to a helper, a subagent loaded with one to three skills. Pieces that do not depend on each other run side by side. Work bigger than a one-file change gets an approach check first and a check-in halfway. A piece passes on evidence: `/qa-only` tests the running app and returns a health score with screenshots and repro steps, and a piece with critical findings goes back to a fresh helper with the fix list.

Before a plate leaves the kitchen, someone at the pass counts it against the ticket. When a helper reports a finished file, such as a PDF or a page, a hook looks for it on disk:

```
[artifact-verify] <timestamp> ARTIFACT_MISSING WARNING
[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:
  MISSING: /path/to/report.pdf
```

Each deliverable write also leaves a row with its path and byte count. The check proves the file exists, not that it is right, so `/cc-loop` sends prose past critics who score it and send it back, for up to three rounds.

### Context runs out in the middle of the task

An agent deep in a job cannot see how full its context is, so the `agent-ctx` mod tells it. Your main session gets a warning at 70 and 75 percent of its window, and at 80 percent this:

```
CONTEXT_PCT_ALERT: 80% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.
```

Helpers count absolute tokens: a warning at 200k, "finish the current task" at 250k, and from 300k a stop line on every tool result. Whoever started a helper sees its fill as a `CHILD_CTX` line, plus a `CHILD_CTX_ALERT` once it passes 250k. A project lead that needs a restart prints `RESPAWN_REQUEST <project>`, a toast tells you which `/pd-resume` to run, and the fresh session picks up from the saved files.

For you, a band above the prompt shows context, tokens, model, cost so far, a prompt-cache countdown and when your 5-hour and 7-day usage windows reset. `/ctx` opens the detail.

### The usage window empties and no one can say which job spent it

A kitchen keeps the receipt from every service so the owner can see where the money went. Each time a session stops, `metrics/costs.jsonl` gets a row with its tokens and cost, priced model by model. Helper transcripts sit outside that row, so each helper run writes its own rows to `spawns.jsonl`, with model and cost.

Less gets spent in the first place. Code search runs on the small Haiku model, and project questions go to your memory files before anyone spawns a helper. A cap on running helpers refuses the next one with a `[spawn-cap]` message until a slot frees. If you use the caveman or ponytail plugins, the `voice-compact` mod rewrites their long startup instructions into about 150 tokens of rules. None of it hands back usage already spent, and the cap counts helpers, not dollars.

### A typo fix runs on the same model as a migration

Left alone, a quick lookup runs on your most expensive model and a hard refactor gets the thinking time of a typo fix. The Agency sets the model by role on every spawn and overrides whatever the caller asked for:

- **Project lead:** Opus at medium effort.
- **Critics** for code, security, design, copy, brand, search, video and more: Opus at high effort.
- **Helpers:** Sonnet. A request for another model is pinned back to Sonnet; letting a helper ask for Opus with a reason ships switched off.
- **Code search:** Haiku at low effort.

Helpers also get an effort level, how hard the model thinks before it answers, from the kind of task. How far that goes depends on the skill router:

| Helper task | Router off (fresh install) | Router on |
|---|---|---|
| Hard code: debugging, refactors, migrations, security | high when the brief carries `MODEL-CATEGORY: debug`, else medium | high when the job reads as complex code |
| Routine code | medium | medium |
| Visual work: pages, images, video, decks | medium | high |
| English writing | medium | high |
| Vietnamese writing | medium | xhigh |
| Quick lookup | low when the brief carries `MODEL-CATEGORY: lookup` | the same |
| Anything else | medium | medium |

On a fresh install `AGENCY_SKILL_ROUTER` is unset, so the router never runs and makes no network request, and the roles above keep their settings. Set it to `1` with a routing key from your own account, and the router reads each helper's task, picks up to three skills and names the kind of job, which sets the effort. A spawn gate then checks that each helper brief carries the pick, and a router outage lets spawns through unchanged. Setup is in [`scripts/skill-route/README.md`](scripts/skill-route/README.md).

### It leaks a key, or deletes more than you asked

An agent pastes a token into a shell command, or a cleanup reaches into folders you never named. Hooks check first:

- **Keys in commands.** A scanner looks for GitHub, Slack, Google and AWS tokens, JWTs and `api_key=` assignments, and asks you before the command runs:

  ```
  [secret-scanner] Command contains what looks like a GitHub token. Use env vars or keychain instead of inline credentials.
  ```

- **Linter configs.** An agent cannot loosen an existing ESLint, Prettier, Biome, Ruff, ShellCheck, Stylelint or markdownlint config to silence a failing rule. The refusal tells it to fix the code.
- **Sensitive files.** Writes to `settings.json`, agent definitions, hook scripts and `SKILL.md` files, or content that looks like a token, get a warning first. At session start a check warns if `settings.json` holds tokens in plain text.
- **`/guard`.** Turn it on before you touch production. It warns before `rm -rf`, `DROP TABLE`, `git push --force` and `git reset --hard`, and keeps edits inside the one folder you name.

`~/.claude/.hook-profile` sets how hard the hooks push: `standard` (the default) asks on keys and warns on sensitive files, `strict` refuses both, `minimal` turns them off. The scanner reads shell commands only, so an agent that opens `.env` with its file tool goes past it, and a rule such as "wait for my yes before a deploy" is an instruction with no code behind it. For review, `/security` checks code against the common web risks and `/cso` runs a full audit.

### The same failing call runs until you press Escape

After five identical tool calls in a row, the agent sees:

```
[loop-detector] STALL DETECTED: 5 identical Bash calls in a row.
```

The message tells it to restate the goal, check the real state of the files and try another approach, or save and stop. The next session opens with a note that an agent looped, so you can check whether the task finished. The warning never stops the run, and a loop that changes each call slips past it. A mod and a hook both watch for this, so you may see it twice; [docs/MODS.md](docs/MODS.md) shows how to keep one.

### Plans and reviews arrive as a wall of chat

`/html-plan-style` turns plans, reports and reviews into styled pages you open in a browser. Agents pass work to each other in a fixed hand-over format (`core/nexus/HANDOFF.md`). Brand colours and fonts live as JSON in `design-system/`, and the design skills use CSS generated from it, so the palette holds from file to file. `agency tasks` keeps a local task list once you run `npm install better-sqlite3`.

### A hard call deserves a second opinion

`/codex` hands your diff to the Codex CLI, if you have it installed, for a review, an attempt to break it, or an open question. For a decision rather than a diff, convene the council: one read-only reviewer per Claude model tier gets the same brief in a single wave, and you get back a table of verdicts, agreements and disagreements. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#agency-council).

---

## Skills for the work around the code

Skills are instructions Claude Code loads for one kind of work, called as `/name`. These ship in the repo, and [skills/INDEX.md](skills/INDEX.md) lists the rest with descriptions.

| Domain | Skills |
|---|---|
| Frontend and design | `/frontend`, `/ui-ux-pro-max`, `/impeccable`, `/design-review`, `/gpt-image-prompts` |
| Backend, data and deploy | `/backend`, `/postgresql-schema`, `/supabase-deploy`, `/vercel-deploy` |
| Debugging, testing and review | `/superpowers-systematic-debugging`, `/superpowers-test-driven-development`, `/review`, `/qa` |
| Security | `/security`, `/cso`, `/security-critique` |
| Browser and web data | `/lightpanda`, `/agent-browser`, `/firecrawl-scrape` |
| English writing | `/content-polish`, `/humanizer`, `/stop-slop`, `/tech-writer` |
| Vietnamese writing | `/humanizer-vi`, `/grammar-checker-vi`, `/translationese-cleaner-vi`, `/style-guide-vi` |
| Marketing, content and SEO | `/copywriting`, `/content-strategy`, `/pipeline-seo-geo-aeo`, `/marketing-critique`, `/inbound-sales` |
| Video and audio | `/hyperframes`, `/video-use`, `/subtitle-burner`, `/musicgen` |
| Decks, documents and spreadsheets | `/marp`, `/deck-narrative`, `/make-pdf`, `/xlsx-toolkit` |
| Planning and research | `/superpowers-writing-plans`, `/plan-eng-review`, `/office-hours`, `/auto-researcher`, `/graphify` |
| Google Workspace | `/gws` |
| Cloud cost | `/finops` |
| Career | `/career-ops`, `/cover-letter-gen` |
| Memory and system | `/save-state`, `/recall`, `/lint-memory`, `/skill-creator` |

---

## What a fresh install runs

| Part | Fresh install | What it needs |
|---|---|---|
| `/save-state`, `/recall`, `/pd-resume` | Ready | You run the save |
| File check, edit trail, crash notice, loop warning | On | Warns, never stops the run |
| Key scanner, linter-config lock, sensitive-file warning | On, `standard` profile | `strict` to refuse instead of ask |
| `/guard` | Off | You invoke it |
| Context alerts, band, cost rows, helper cap, model pin, effort by role | On, as mods | Claude Code 2.1.287 or newer |
| Effort by kind of task | Off; helpers get medium | The skill router and your own routing key |
| Startup-rule rewrite | On, idle | The caveman or ponytail plugin |
| QA gate, approach check, rework loop, hand-over format, page style | Instructions | Agents follow them; no code enforces them |
| `agency tasks` | Needs a package | `npm install better-sqlite3` |

The mods live in [mods/](mods/) and install with the rest; `AGENCY_NO_MODS=1` skips them and `agency mods remove` takes them out. Everything runs as plain files on your machine with no server to host, and only the optional router needs a key. On Windows the installers and mods pass CI, and a run on a real Windows machine is still pending.

---

## Credits

Not everything here was made by one person. The memory design is inspired by Andrej Karpathy's LLM Wiki idea. The token-saving setup builds on the caveman and ponytail plugins, and `/self-healing` is inspired by Hermes Agent. Many skills began as other people's open-source work. [CREDITS.md](CREDITS.md) names each source, its author and its licence.

---

## Docs

| Guide | What it covers |
|-------|----------------|
| [User Guide](docs/GUIDE.md) | A walkthrough from clone to shipped feature |
| [Setup](docs/SETUP.md) | Prerequisites, upgrades, integrations, troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | Project lead and helpers, QA gates, memory, routing, council |
| [Skills](docs/SKILLS.md) | Skills by domain, pipelines, the skill router, the effort policy |
| [Hooks](docs/HOOKS.md) | Each hook, the profiles, settings wiring |
| [Mods](docs/MODS.md) | What each mod fixes, and how to add or remove it |
| [Developer Guide](docs/DEVELOPER.md) | Repo layout, adding skills, testing |
| [Install Layout](docs/INSTALL-LAYOUT.md) | What each installer puts where |

## Contributing

Most contributions are skills: a folder `skills/<name>/SKILL.md`, registered and routed as described in [docs/DEVELOPER.md](docs/DEVELOPER.md).

## License

MIT. Use it however you want. Repo: [github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency).

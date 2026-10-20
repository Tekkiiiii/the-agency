# The Agency

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)

**Claude Code gives you a team. The Agency gives it the habits of a good one.**

The Agency is a set of plain files for Claude Code that you can open and read: agent definitions for the project lead and coordinators, skills that specialists load, and the hooks and mods (small Claude Code plugins) that carry out the rules.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency && cd ~/the-agency && bash install.sh
```

Then run `agency onboard`. The installer backs up `settings.json` before it merges its hooks in; Windows steps: [Install](#install).

An established team runs on habits. A project lead scopes the job and gives each piece to the person who fits it. QA signs off on evidence, and every session and subagent run lands in a cost log.

Change control checks a risky command before it runs. A task that fails a third time goes up a level, and a hard call gets a second opinion. The closing shift writes a handover for the next one, and the finished work arrives as a document you can read.

The Agency installs those habits into Claude Code. Each section below names the role that owns one habit and says which parts run as code on a fresh install and which are written instructions. [What a fresh install runs](#what-a-fresh-install-runs) puts them in one table.

---

## Where the ideas came from

The Agency is built on ideas and skills from these sources:

| From | What it gave The Agency |
|---|---|
| Anthropic | Claude Code, the host the skills, hooks and mods run in. `/webapp-testing` and `/mcp-builder` ship from anthropics/skills, and `/impeccable` builds on Anthropic's frontend-design skill. |
| Jesse Vincent (obra), superpowers | The skills for brainstorming, writing plans, test-driven development, systematic debugging and subagent-driven development. |
| Andrej Karpathy, LLM Wiki | The memory design is inspired by it: an index plus cross-linked markdown pages the agents write, with a periodic lint pass. His raw-folder habit is behind `/graphify`. |
| Nous Research, Hermes Agent | `/self-healing` is inspired by the way Hermes recovers and learns from failed turns. |
| WikiProject AI Cleanup, Wikipedia | The catalogue of AI-writing patterns behind `/humanizer`. |
| Julius Brussee (caveman) and Dietrich Gebert (ponytail) | Caveman's compressed replies and ponytail's minimal-solution mode, plus the `ponytail:` comment that marks a deliberate shortcut. Both plugins install separately. |
| HeyGen HyperFrames, Cloudflare, HashiCorp, Supabase, Google Labs Stitch, Browser Use, Firecrawl | Their agent skills ship inside. |
| Microsoft, markitdown | `/markitdown` wraps the library. |

[CREDITS.md](CREDITS.md) lists every source with its author and licence.

---

## Handover in writing

At the end of each session `/save-state` plays the closing shift and writes the handover into one short file plus a dated session log. The next session opens with `/recall`, which reads it back:

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

`/pd-resume invoice-app` starts a project lead from the same file, so a job that runs for days picks up at the step it reached.

Each project also keeps an index plus plain markdown memory pages that the agents write and cross-link. `/lint-memory` checks them for orphans and dead links.

When a session ends before its handover, the next one opens with:

```
NOTICE: Previous session may have ended uncleanly (last clean stop: <timestamp>).
  Run /recall [slug] or /save-state [slug] to check project state.
```

A shift also ends when the context window fills. The `agent-ctx` mod warns your main session at 70 and 75 percent of its window, and at 80 percent prints:

```
CONTEXT_PCT_ALERT: 80% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.
```

Subagents count absolute tokens: a warning at 200k, "finish the current task" at 250k and a stop at 300k ([docs/MODS.md](docs/MODS.md)). A project lead that needs a fresh session prints `RESPAWN_REQUEST <project>`, a toast names the `/pd-resume` to run, and the new session starts from the handover.

On a fresh install `/save-state`, `/recall` and `/pd-resume` are ready, and you run the save. The crash notice runs as a hook and the context alerts as a mod.

---

## Scope, then delegate

A feature that takes days starts with a project lead. The lead scopes the job and splits it into pieces, one for each coordinator. A coordinator hands a piece that fits one specialist straight to one and splits a bigger piece again. A specialist is a subagent loaded with one to three skills for its piece, and independent pieces run side by side. Work larger than a one-file change gets an approach check before it starts and a check-in halfway.

A cap on running specialists per project lead refuses the next spawn until a slot frees:

```
[spawn-cap] <n> Execs already running under PD <project> tree (cap <max>, Exec cap policy: max <max> Execs per PD across all its coords). Please wait for a slot - a completion notification arrives on its own - then spawn again, or merge tasks. Do not retry in a loop.
```

The output says PD for the project lead and Exec for a specialist. On a fresh install the cap runs as code, in the `spawn-ledger` mod. The split and both checks are written instructions the lead and its coordinators follow.

---

## Right person for the ticket

A team lead matches each ticket to the right person and the right amount of thought. The Agency does that on every spawn: it sets the model by role and overrides the caller's request.

- **Project lead:** Opus at medium effort.
- **Coordinators:** Sonnet at medium effort.
- **Critics:** Opus at high effort.
- **Specialists:** Sonnet. A request for another model is pinned back to Sonnet. An opt-in setting lets a specialist ask for Opus with a reason.
- **Code search:** Haiku at low effort.

With the router on, specialists also get an effort level, how hard the model thinks before it answers, set by the kind of task: high for hard code, visual work and English writing, xhigh for Vietnamese writing, low for quick lookups and medium for the rest. [docs/SKILLS.md](docs/SKILLS.md#effort-policy) has the table.

On a fresh install the model pin and the effort by role run as code in the `spawn-ledger` mod. `AGENCY_SKILL_ROUTER` is unset, so the router stays off and offline, and a specialist gets medium effort unless its brief carries a `MODEL-CATEGORY:` line such as `debug` or `lookup`.

Set `AGENCY_SKILL_ROUTER=1` with your own key for Jev, a hosted routing service, and the router picks up to three skills for each specialist's task and names the kind of job, which sets the effort. A spawn gate checks that each brief carries the pick as a `Jev[r=<route_id>]` line, and a router outage lets spawns through unchanged. Setup: [`scripts/skill-route/README.md`](scripts/skill-route/README.md).

---

## Done means QA signed

The QA desk signs a piece off on evidence. `/qa-only` tests the running app and returns a health score with screenshots and repro steps, and a piece with critical findings goes back to a fresh specialist with the fix list.

When a specialist reports a finished file, such as a PDF or a page, a hook looks for it on disk:

```
[artifact-verify] <timestamp> ARTIFACT_MISSING WARNING
[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:
  MISSING: /path/to/report.pdf
```

Each deliverable write adds a row with its path and byte count to `logs/write-evidence.jsonl` under your Claude Code config folder. `/cc-loop` sends the deliverable past critics who score it and return it for fixes, for up to three rounds.

On a fresh install the file check is a hook that warns while the run carries on. The QA gate is a written instruction the project lead follows.

---

## Every hour on a cost code

Finance logs what each session spent. Each time a session stops, `metrics/costs.jsonl` gets a row with its tokens and cost, priced model by model. Each subagent run writes its own rows to `spawns.jsonl`, with model and cost. A band above your prompt shows context, tokens, model, cost so far, a prompt-cache countdown and when your 5-hour and 7-day usage windows reset. `/ctx` opens the detail.

The code-search agent runs on the small Haiku model, and the lookup-first rule tells agents to read your memory files before they spawn a subagent. If you use the caveman or ponytail plugins, the `voice-compact` mod rewrites their long startup instructions into about 150 tokens of rules.

On a fresh install the session row comes from a hook, and the subagent rows and the band run as mods. `voice-compact` waits idle until you install caveman or ponytail.

---

## Second pair of eyes on production

Change control checks a risky command before it runs. Turn on `/guard` before you touch production: it warns before `rm -rf`, `DROP TABLE`, `git push --force` and `git reset --hard`, and keeps edits inside the one folder you name.

Hooks watch the rest of the time:

- **Keys in commands.** A scanner looks for GitHub, Slack, Google and AWS tokens, JWTs and `api_key=` assignments, and asks you before the command runs:

  ```
  [secret-scanner] Command contains what looks like a GitHub token. Use env vars or keychain instead of inline credentials.
  ```

- **Linter configs.** When an agent tries to loosen a lint config such as ESLint or Ruff to silence a failing rule, the hook refuses and tells it to fix the code.
- **Sensitive files.** Writes to `settings.json`, agent definitions, hook scripts and `SKILL.md` files, or content that looks like a token, get a warning first. At session start a check warns if `settings.json` holds tokens in plain text.

`~/.claude/.hook-profile` sets how hard the hooks push: `standard` (the default) asks on keys and warns on sensitive files, `strict` refuses both, `minimal` turns them off. The key scanner reads shell commands; [docs/HOOKS.md](docs/HOOKS.md) lists what each hook reads. For review, `/security` checks code against the common web risks and `/cso` runs a full audit.

On a fresh install `/guard` is off until you invoke it, and the hooks run on the `standard` profile. Approval rules, such as "wait for my yes before a deploy", are instructions the agent follows.

---

## Three strikes, escalate

Under the on-call rule, a problem goes up a level after the third failed try. `/investigate` stops after three hypotheses fail and asks you how to proceed. `/qa-only` escalates after three failed attempts with what it tried and a recommendation. A `/cc-loop` deliverable still under the bar after three rounds goes back to the project lead, who can hand it to a fresh writer with the critics' fix list.

A loop that repeats one call trips a hook. After five identical tool calls in a row, the agent sees:

```
[loop-detector] STALL DETECTED: 5 identical Bash calls in a row.
```

The message tells it to restate its goal and try another approach, or save and stop. The next session opens with a note that an agent looped, so you can check whether the task finished.

On a fresh install the three-strike rules are skill instructions. The loop warning is a hook that matches identical calls and lets the run continue; [docs/MODS.md](docs/MODS.md#overlap-with-shell-hooks) covers the mod that watches for the same loop.

---

## Second opinion on hard calls

The review board takes the calls that need a second view. `/codex` hands your diff to the Codex CLI for a review or an attempt to break it. For a decision, convene the council: one read-only reviewer per Claude model tier gets the same brief at once, and you get back a table of where the seats agree and where they split. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#agency-council).

On a fresh install the four council seats ship as agent files in `agents/council/`, and `/codex` runs once you install the Codex CLI. The council protocol is a written instruction the caller follows.

---

## Deliverables as documents

Reporting writes each result as a document you can open. `/html-plan-style` turns plans and reports into styled pages for the browser. Agents pass work to each other in a fixed hand-over format (`core/nexus/HANDOFF.md`).

On a fresh install the page style and the hand-over format are instructions the agents follow.

---

## Install

```bash
# Clone to any folder outside ~/.claude (Claude Code already uses that one)
git clone https://github.com/Tekkiiiii/the-agency.git ~/the-agency
cd ~/the-agency

bash install.sh        # macOS / Linux
.\install.ps1          # Windows (PowerShell)
```

The installer copies skills, agents, hooks and the `agency` command into your Claude Code config folder (`~/.claude/` unless you set another; its `Sync root:` line names it). It merges its hooks into `settings.json` beside yours and keeps a backup. Keep the clone: `agency upgrade` pulls it and syncs again.

```bash
agency onboard                                           # guided setup, start here
agency new invoice-app "Invoicing for a two-person design studio"
```

Open Claude Code and run `/recall invoice-app`. A new project answers "no prior session found". Tell Claude what to build, and run `/save-state` when you stop.

If you cloned already, `node cli/bin/agency.js init` runs the same sync. If `agency upgrade` breaks, `bash rescue.sh` in the clone (`rescue.ps1` on Windows) pulls the latest code; [Troubleshooting](docs/SETUP.md#troubleshooting) covers the rest.

### What a fresh install runs

| Part | Fresh install | What it needs |
|---|---|---|
| `/save-state`, `/recall`, `/pd-resume` | Ready | You run the save |
| File check, edit trail, crash notice, loop warning | On | Warns; the run carries on |
| Session cost row | On, as a hook | Runs when a session stops |
| Key scanner, linter-config lock, sensitive-file warning | On, `standard` profile | `strict` to refuse instead of ask |
| `/guard` | Off | You invoke it |
| Context alerts, band, subagent cost rows, specialist cap, model pin, effort by role | On, as mods | Claude Code 2.1.287 or newer |
| Effort by kind of task | Off; specialists get medium | The skill router and your own routing key |
| Startup-rule rewrite | On, idle | The caveman or ponytail plugin |
| QA gate, approach check, rework loop, hand-over format, page style | Instructions | Agents follow them; enforcement rests with the agent |
| `agency tasks` | Needs a package | `npm install better-sqlite3` |

The mods install with the rest; `AGENCY_NO_MODS=1` skips them and `agency mods remove` takes them out. Everything runs as plain files on your machine, and the optional router is the one part that needs a key. Windows status: [docs/MODS.md](docs/MODS.md#windows).

---

## Skills the specialists carry

Skills are instructions Claude Code loads for one kind of work, called as `/name`, and a specialist loads one to three of them for its piece. These ship in the repo; [skills/INDEX.md](skills/INDEX.md) lists the rest.

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

The design skills take their colours and fonts from the JSON in `design-system/`.

---

## Docs

| Guide | What it covers |
|-------|----------------|
| [User Guide](docs/GUIDE.md) | A walkthrough from clone to shipped feature |
| [Setup](docs/SETUP.md) | Prerequisites, upgrades, integrations, troubleshooting |
| [Architecture](docs/ARCHITECTURE.md) | Project lead, coordinators and specialists, QA gates, memory, routing, council |
| [Skills](docs/SKILLS.md) | Skills by domain, pipelines, the skill router, the effort policy |
| [Hooks](docs/HOOKS.md) | Each hook, the profiles, settings wiring |
| [Mods](docs/MODS.md) | What each mod fixes, and how to add or remove it |
| [Developer Guide](docs/DEVELOPER.md) | Repo layout, adding skills, testing |
| [Install Layout](docs/INSTALL-LAYOUT.md) | What each installer puts where |
| [Credits](CREDITS.md) | Every source with its author and licence |

## Contributing

Most contributions are skills: a folder `skills/<name>/SKILL.md`, registered and routed as described in [docs/DEVELOPER.md](docs/DEVELOPER.md).

## License

MIT. Use it however you want.

# The Agency

**Claude Code gives you a team. The Agency runs it like one.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform: Claude Code](https://img.shields.io/badge/Platform-Claude%20Code-yellow)

A team that has worked together for a while runs on a handful of habits. Whoever closes the shift writes a handover for whoever opens it. A project lead scopes the job and gives each piece to the person who fits it. QA signs off before anything ships, and every hour lands on a cost code. A second pair of eyes reads any change headed for production. When a task fails for the third time it goes up a level, and a hard call gets a second opinion. The finished work arrives as a document someone can read.

The Agency installs those habits into Claude Code as plain files you can open and read. Each habit below comes with the role that owns it, the lines that role prints and how far it goes on a fresh install.

---

## Where the habits came from

A good team adopts the best practice it can find and says where it came from. The Agency is built on ideas and skills from these people and projects:

| From | What it gave The Agency |
|---|---|
| Andrej Karpathy, LLM Wiki | The memory design is inspired by it: an index plus plain markdown pages the agents write, linked to each other, with a periodic lint pass. His raw-folder habit is behind `/graphify`. |
| Nous Research, Hermes Agent | `/self-healing` is inspired by the way Hermes recovers and learns from failed turns. |
| Anthropic | Claude Code, the host everything runs in, plus skills built on anthropics/skills and the frontend-design skill behind `/impeccable`. |
| Jesse Vincent (obra), superpowers | The skills for brainstorming, writing plans, test-driven development, systematic debugging and subagent-driven development. |
| WikiProject AI Cleanup, Wikipedia | The catalogue of AI-writing patterns behind `/humanizer`. |
| Julius Brussee (caveman) and Dietrich Gebert (ponytail) | The token discipline, and the `ponytail:` comment that marks a deliberate shortcut. |
| HeyGen HyperFrames, Cloudflare, HashiCorp, Supabase, Google Labs Stitch, Browser Use, Firecrawl | Skills from their own repositories ship inside. `/markitdown` is built on Microsoft's markitdown library. |

[CREDITS.md](CREDITS.md) lists every source with its author, link and licence.

---

## Handover in writing

The closing shift is any session you end. `/save-state` writes its handover: the phase, the next step, what is blocked, the decisions you locked and the work in flight, in one short file plus a dated session log. The next session opens with `/recall`, which reads it back:

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

`/pd-resume invoice-app` starts a project lead from the same file, so a job that runs for days picks up at the step it reached. You run the save yourself. When a session ends before its handover, the next one opens with:

```
NOTICE: Previous session may have ended uncleanly (last clean stop: <timestamp>).
  Run /recall [slug] or /save-state [slug] to check project state.
```

Shifts also end on the clock, when the context window fills. The `agent-ctx` mod tells each agent how full its context is. Your main session gets a warning at 70 and 75 percent of its window, and at 80 percent this:

```
CONTEXT_PCT_ALERT: 80% — MANDATORY RESPAWN THRESHOLD (80%). Run /save-state and /respawn-self now.
```

Subagents count absolute tokens: a warning at 200k, "finish the current task" at 250k, and from 300k a stop line on every tool result. Whoever started a subagent sees its fill as a `CHILD_CTX` line, plus a `CHILD_CTX_ALERT` once it passes 250k. A project lead that needs a fresh session prints `RESPAWN_REQUEST <project>`, a toast tells you which `/pd-resume` to run, and the new session starts from the handover.

---

## Scope, then delegate

A feature that takes days starts with a project lead. The lead scopes the job and splits it into pieces, one for each coordinator. A coordinator hands a piece that fits one specialist straight to one, and splits a bigger piece again. A specialist is a subagent loaded with one to three skills for the piece in front of it. Pieces that stand on their own run side by side. Work larger than a one-file change gets an approach check before it starts and a check-in halfway.

A lead staffs the desks it has. A cap on running specialists per project lead refuses the next spawn until a slot frees:

```
[spawn-cap] <n> Execs already running under PD <project> tree (cap <max>, Exec cap policy: max <max> Execs per PD across all its coords). Please wait for a slot - a completion notification arrives on its own - then spawn again, or merge tasks. Do not retry in a loop.
```

On a fresh install the cap runs as code, in the `spawn-ledger` mod. The split, the approach check and the check-in are written instructions that the lead and its coordinators follow.

---

## Right person for the ticket

The team lead reads each ticket and decides who takes it and how much thought it gets. The Agency makes that call on every spawn: it sets the model by role and overrides whatever the caller asked for.

- **Project lead:** Opus at medium effort.
- **Coordinators:** Sonnet at medium effort.
- **Critics** for code, security, design, copy, brand, search, video and more: Opus at high effort.
- **Specialists:** Sonnet. A request for another model is pinned back to Sonnet; a setting that lets a specialist ask for Opus with a reason ships switched off.
- **Code search:** Haiku at low effort.

Specialists also get an effort level, how hard the model thinks before it answers, from the kind of task. How far that goes depends on the skill router:

| Specialist task | Router off (fresh install) | Router on |
|---|---|---|
| Hard code: debugging, refactors, migrations, security | high when the brief carries `MODEL-CATEGORY: debug`, else medium | high when the job reads as complex code |
| Routine code | medium | medium |
| Visual work: pages, images, video, decks | medium | high |
| English writing | medium | high |
| Vietnamese writing | medium | xhigh |
| Quick lookup | low when the brief carries `MODEL-CATEGORY: lookup` | the same |
| Anything else | medium | medium |

On a fresh install `AGENCY_SKILL_ROUTER` is unset: the router stays off and offline, and the roles above keep their settings. Set it to `1` with a key from your own account on Jev, the routing service it calls, and the router reads each specialist's task, picks up to three skills and names the kind of job, which sets the effort. A spawn gate then checks that each specialist brief carries the pick as a `Jev[r=<route_id>]` line, and a router outage lets spawns through unchanged. Setup is in [`scripts/skill-route/README.md`](scripts/skill-route/README.md).

---

## Done means QA signed

The QA desk signs a piece off on evidence. `/qa-only` tests the running app and returns a health score with screenshots and repro steps, and a piece with critical findings goes back to a fresh specialist with the fix list.

When a specialist reports a finished file, such as a PDF or a page, a hook looks for it on disk:

```
[artifact-verify] <timestamp> ARTIFACT_MISSING WARNING
[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:
  MISSING: /path/to/report.pdf
```

Each deliverable write also leaves a row with its path and byte count. The hook confirms the file is there, and the critics judge whether it is right: `/cc-loop` sends prose past critics who score it and send it back, for up to three rounds.

On a fresh install the file check is a hook that warns while the run carries on. The QA gate is a written instruction the project lead follows.

---

## Every hour on a cost code

Finance logs what each session spent. Each time a session stops, `metrics/costs.jsonl` gets a row with its tokens and cost, priced model by model. Subagent transcripts sit outside that row, so each subagent run writes its own rows to `spawns.jsonl`, with model and cost. A band above your prompt shows context, tokens, model, cost so far, a prompt-cache countdown and when your 5-hour and 7-day usage windows reset. `/ctx` opens the detail.

The budget also shapes how work gets done. Code search runs on the small Haiku model, and project questions go to your memory files before anyone spawns a subagent. If you use the caveman or ponytail plugins, the `voice-compact` mod rewrites their long startup instructions into about 150 tokens of rules. These savings apply to work still ahead, and the specialist cap counts running specialists rather than dollars.

---

## Second pair of eyes on production

Change control reads a risky change before it lands. Turn on `/guard` before you touch production: it warns before `rm -rf`, `DROP TABLE`, `git push --force` and `git reset --hard`, and keeps edits inside the one folder you name.

Hooks watch the rest of the time:

- **Keys in commands.** A scanner looks for GitHub, Slack, Google and AWS tokens, JWTs and `api_key=` assignments, and asks you before the command runs:

  ```
  [secret-scanner] Command contains what looks like a GitHub token. Use env vars or keychain instead of inline credentials.
  ```

- **Linter configs.** When an agent tries to loosen an existing ESLint, Prettier, Biome, Ruff, ShellCheck, Stylelint or markdownlint config to silence a failing rule, the hook refuses and tells it to fix the code.
- **Sensitive files.** Writes to `settings.json`, agent definitions, hook scripts and `SKILL.md` files, or content that looks like a token, get a warning first. At session start a check warns if `settings.json` holds tokens in plain text.

`~/.claude/.hook-profile` sets how hard the hooks push: `standard` (the default) asks on keys and warns on sensitive files, `strict` refuses both, `minimal` turns them off. The scanner reads shell commands, so an agent that opens `.env` with its file tool goes past it. A rule such as "wait for my yes before a deploy" is an instruction the agent follows rather than a hook. For review, `/security` checks code against the common web risks and `/cso` runs a full audit.

On a fresh install `/guard` is off until you invoke it, and the hooks run on the `standard` profile.

---

## Three strikes, escalate

The on-call rule sends a problem up a level after the third failed try. `/investigate` stops after three hypotheses fail and asks you how to proceed, with escalation for human review as one of the options. `/qa-only` escalates after three failed attempts with a status, the reason, what it tried and a recommendation. A `/cc-loop` deliverable still under the bar after three rounds goes back to the project lead, who can hand it to a fresh writer with the critics' fix list.

A loop that repeats one call trips a hook. After five identical tool calls in a row, the agent sees:

```
[loop-detector] STALL DETECTED: 5 identical Bash calls in a row.
```

The message tells it to restate the goal, check the real state of the files and try another approach, or save and stop. The next session opens with a note that an agent looped, so you can check whether the task finished.

On a fresh install the three-strike rules are skill instructions. The loop warning is a hook that lets the run continue, and a loop that changes each call slips past it. A mod and a hook both watch for this, so you may see it twice; [docs/MODS.md](docs/MODS.md) shows how to keep one.

---

## Second opinion on hard calls

The review board takes the calls that deserve more than one view. `/codex` hands your diff to the Codex CLI, if you have it installed, for a review, an attempt to break it, or an open question. For a decision rather than a diff, convene the council: one read-only reviewer per Claude model tier gets the same brief in a single wave, and you get back a table of verdicts, agreements and disagreements. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#agency-council).

---

## Deliverables as documents

Reporting hands work over as documents. `/html-plan-style` turns plans, reports and reviews into styled pages you open in a browser. Agents pass work to each other in a fixed hand-over format (`core/nexus/HANDOFF.md`). Brand colours and fonts live as JSON in `design-system/`, and the design skills use CSS generated from it, so the palette holds from file to file. `agency tasks` keeps a local task list once you run `npm install better-sqlite3`.

On a fresh install the page style and the hand-over format are instructions the agents follow, and the task list waits on that one package.

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

Cloned already? `node cli/bin/agency.js init` runs the same sync. If an install breaks, or you have yet to clone, the rescue script finds your clone, pulls it and repairs it, or clones a fresh one to `~/the-agency/`:

```bash
curl -fsSL https://raw.githubusercontent.com/Tekkiiiii/the-agency/main/rescue.sh | bash
```

### What a fresh install runs

| Part | Fresh install | What it needs |
|---|---|---|
| `/save-state`, `/recall`, `/pd-resume` | Ready | You run the save |
| File check, edit trail, crash notice, loop warning | On | Warns; the run carries on |
| Key scanner, linter-config lock, sensitive-file warning | On, `standard` profile | `strict` to refuse instead of ask |
| `/guard` | Off | You invoke it |
| Context alerts, band, cost rows, specialist cap, model pin, effort by role | On, as mods | Claude Code 2.1.287 or newer |
| Effort by kind of task | Off; specialists get medium | The skill router and your own routing key |
| Startup-rule rewrite | On, idle | The caveman or ponytail plugin |
| QA gate, approach check, rework loop, hand-over format, page style | Instructions | Agents follow them; enforcement rests with the agent |
| `agency tasks` | Needs a package | `npm install better-sqlite3` |

The mods live in [mods/](mods/) and install with the rest; `AGENCY_NO_MODS=1` skips them and `agency mods remove` takes them out. Everything runs as plain files on your machine, and the optional router is the one part that needs a key. On Windows the installers and mods pass CI, and a run on a real Windows machine is still pending.

---

## Skills the specialists carry

Skills are instructions Claude Code loads for one kind of work, called as `/name`. A specialist carries one to three of them. These ship in the repo, and [skills/INDEX.md](skills/INDEX.md) lists the rest with descriptions.

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

## Credits

The sources behind The Agency are summed up in [Where the habits came from](#where-the-habits-came-from). Many more skills began as other people's open-source work, and [CREDITS.md](CREDITS.md) names each one with its author and its licence.

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

## Contributing

Most contributions are skills: a folder `skills/<name>/SKILL.md`, registered and routed as described in [docs/DEVELOPER.md](docs/DEVELOPER.md).

## License

MIT. Use it however you want. Repo: [github.com/Tekkiiiii/the-agency](https://github.com/Tekkiiiii/the-agency).

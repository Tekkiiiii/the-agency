# Agent Gaps Log

When a caller needs to spawn for a task and NO named agent covers it
(after checking delegator-cache → agency-dispatch → `agents-archive/MANIFEST.md`),
the caller MUST:

1. Append a row here (date, task pattern, agent created).
2. Create a minimal named agent def at `agents/specialized/{slug}.md`
   (frontmatter: name, description, restricted `tools:` list, model; body:
   short role prompt). Registration takes effect next session.
3. Spawn: if the new type resolves, use it. If it does not resolve yet
   (same-session registration lag), spawn the fallback ONCE with the new
   agent's role prompt inlined, and note "bridged" below.

Generalist spawns without a row here are a `generalist_ban_violation`.

| Date | Task pattern | Agent created | Bridged? |
|---|---|---|---|
| 2026-07-02 | (log initialized — no gaps yet) | — | — |

## Known Failure Modes (check these proactively, don't wait for a spawn error)

Two spawn-breaking patterns have shown up repeatedly across projects using this
agent registry. Both are silent until spawn time — nothing flags them at
authoring time — so treat this as a checklist to run whenever a new PD or
agent def is added, not just a post-mortem.

### 1. Registered PD with no matching agent definition file

A project can be listed as `active` in the project registry (e.g.
`memory/medium-term.md` or your equivalent registry file) with a full PD
identity file at `projects/{slug}/memory/{slug}-pd.md`, and still have **zero**
matching `agents/**/{slug}-pd.md`. `Agent(subagent_type: "{slug}-pd")` then
fails outright with "Agent type not found" — there is no partial-degradation
path.

- **Detection:** sweep every `active`-flagged project in the registry against
  `agents/**/*.md` filenames. Any registry entry with no matching agent def
  is a gap.
- **Fix:** create a minimal `agents/specialized/{slug}-pd.md` (standard PD
  frontmatter + explicit tool list, pointing at the project identity file as
  source of truth). Registration takes effect **next session** — the agent
  registry resolves once at session start, so same-session respawns still hit
  the missing definition.
- **Example (placeholder names, not a real incident in this repo):** project
  `example-widgets` is registered active with an identity file at
  `projects/example-widgets/memory/example-widgets-pd.md`, but
  `agents/specialized/example-widgets-pd.md` doesn't exist. First spawn
  attempt fails; create the file, log the row above, respawn next session (or
  bridge — see checklist item 3 in the header block).

### 2. `tools: All tools` in frontmatter is not a valid tool list

`tools: All tools` (or any other free-text stand-in for "everything") is not
a list the harness can parse. It gets read as an unrecognized single-item
list and the agent would be spawned with **zero** usable tools — not "all
tools," the opposite. This fails the same way whether it's a PD, a
department member, or a one-off specialist def.

- **Detection:** `grep -rn "^tools: All tools" agents/` (or scan frontmatter
  for any `tools:` value that isn't a literal comma-separated/YAML-list of
  real tool names) across the whole `agents/` tree, not just the file you're
  currently editing — this is a copy-paste bug that spreads to every def
  cloned from the same template.
- **Fix:** replace with an explicit tool list matching the agent's actual
  needs (e.g. `Read, Write, Edit, Bash, Glob, Grep` for an agent that runs
  shell commands; drop `Bash`/`Edit` for read-only agents). Match the pattern
  already used by other working agents of the same role rather than
  inventing a new list each time.
- **Example (placeholder names, not a real incident in this repo):**
  `agents/specialized/example-report-agent.md` has `tools: All tools`.
  Any other agent def cloned from the same starter template inherits the
  same bug — sweep the whole tree once, not just the one file that errored.

Both patterns are "create the minimal agent def / fix the frontmatter, log
it here, respawn next session" — same checklist as the header of this file,
just naming the two concrete triggers to check for before they cause a
failed spawn instead of after.

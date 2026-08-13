# Memory: the two-directory contract

The agency splits memory content across two directories that look similar but
serve different purposes. Every doc that references a `memory/*.md` path
should point at one of these two, deliberately — not the other by accident.

## `core/memory/` — shipped templates and system tables

Ships with the repo, gets installed to `{agency-root}/core/memory/` by
`install.sh` (and `install.ps1` / `cli/commands/init.js`) via a straight
`cp -r core/* {agency-root}/core/`. Reinstalling or upgrading the agency
overwrites this directory with whatever the new version ships.

Holds two kinds of files:

- **Spec/reference docs** — `MEMORY.md` (the memory-system spec),
  `memory-v2.md`, `gardener-runbook.md`, `autonomy-tiers.json`. Read-only in
  practice; nothing mutates these at runtime.
- **System tables that ship pre-seeded and grow in place** —
  `agency-dispatch.md` (the agent/skill routing table), `delegator-cache.md`
  (task-pattern → route cache), `medium-term.md` (active-projects registry).
  These ship as empty scaffolds with the correct headers, and agents read
  *and write* them at their shipped `core/memory/` path. They are agency-wide
  state, not private to one operator, so living alongside the rest of
  `core/` is the right tradeoff even though an upgrade can overwrite
  accumulated entries — the same tradeoff `agency-dispatch.md` already makes.

## `{agency-root}/memory/` — the operator's runtime memory dir

Created **empty** by the installer (`mkdir -p "$CLAUDE_HOME"/{...,memory}`) —
nothing ships into it. It exists so operators and running agents have a place
to accumulate their own memory content: `user`/`feedback`/`project`/
`reference` type files (see `core/memory/MEMORY.md` for the taxonomy),
`lessons/`, session logs, and anything else that's genuinely per-operator
state that should survive an agency upgrade untouched.

`lint-memory` scans this directory (plus each project's own `memory/`) for
health — dead links, orphans, stale entries — because this is where content
actually accumulates over a session.

## Writing a reference correctly

- Pointing at a file that ships in this repo under `core/memory/`? Write
  `{agency-root}/core/memory/<file>.md`.
- Pointing at something the operator is expected to create/accumulate
  themselves, with no shipped template? Word it as conditional — "if this
  file exists" — rather than asserting the path is already there. A bare
  `{agency-root}/memory/` reference (no filename) describing it as an empty,
  operator-populated scope is fine as-is.
- Before adding a new agency-wide table that skills read and write, ask
  whether it's more like `agency-dispatch.md` (ship it here, in `core/`) or
  more like a `lessons/` file (belongs in the operator's runtime `memory/`).

# Memory: the two-directory contract

The agency splits memory content across two directories that look similar but
serve different purposes. Every doc that references a `memory/*.md` path
should point at one of these two, deliberately — not the other by accident.

## `core/memory/` — shipped templates and system tables

Ships with the repo, gets installed to `{agency-root}/core/memory/` by all four
deploy paths (`install.sh`, `install.ps1`, `cli/commands/init.js`,
`cli/commands/upgrade.js`). Reinstalling or upgrading the agency refreshes this
directory with whatever the new version ships — **except** for the files named
in `core/.preserve`.

Holds two kinds of files, and the difference decides whether an upgrade
overwrites it:

- **Shipped content** — `MEMORY.md` (the memory-system spec), `memory-v2.md`,
  `gardener-runbook.md`, `autonomy-tiers.json`, `agency-dispatch.md` (the
  agent/skill routing table), `lessons/*.md`. Nothing in the shipped system
  writes to any of these at runtime; they are read-only in practice. They are
  **overwritten on every upgrade, deliberately** — that is how an existing
  install receives new agent routes, new tier definitions and new lessons.
  Freezing them would be a silent regression, not a safe default.
- **Accumulating files** — `medium-term.md` (active-projects registry, appended
  by `project-scaffolder` on every `/new-project`), `delegator-cache.md`
  (task-pattern → route cache, appended by every caller on a Delegator miss),
  `quality-prefs.md` (thresholds the operator edits directly). The running
  system writes rows into these **at their installed path**, so an upgrade that
  overwrote them would destroy real user data. They are listed in
  `core/.preserve` and are never overwritten once they exist.

### The preserve contract

`core/.preserve` is the **single** definition of that list — one file, read by
bash (`install.sh`), PowerShell (`install.ps1`) and Node (`syncCore()` in
`cli/commands/sync-assets.js`, used by both `agency init` and `agency
upgrade`). There is deliberately no second copy to drift out of sync. Format:
one path per line, relative to `core/`, forward slashes, exact file paths,
`#` for comments.

The rule is **skip-if-exists**:

| Destination | Behaviour |
|---|---|
| file already there | left exactly as-is, never overwritten |
| file not there | seeded from the repo copy |

One rule covers both first-install seeding and upgrade preservation. There is
no merge — merging would need per-file format knowledge, and a wrong merge
loses rows just as surely as an overwrite does.

**Adding a new agency-wide table that agents write to? Add it to
`core/.preserve` in the same commit.** A new accumulating file that is not on
that list reintroduces exactly this bug: it will be silently overwritten on
every reinstall and every `agency upgrade`, with exit code 0 and no warning.
`.github/scripts/check-core-preserve.js` fails the build if a listed path does
not exist under `core/`, but nothing can detect a file you forgot to list.

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
  whether it's more like `agency-dispatch.md` (agency-wide, ship it here in
  `core/`) or more like a `lessons/` file (per-operator, belongs in the
  operator's runtime `memory/`). If it ships here **and** anything writes to
  it at runtime, it must also go in `core/.preserve` — see the preserve
  contract above.

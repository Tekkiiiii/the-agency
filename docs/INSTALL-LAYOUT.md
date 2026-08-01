# Install Layout — what each installer deploys

There are three installers, and they must agree. Every gap between them is not a
cosmetic difference: it is a class of **dangling reference**, because shipped agent
defs, runbooks, skills and scripts refer to their siblings by deployed path
(`{agency-root}/hooks/emit-metric.sh`, `{agency-root}/runbooks/service-lookups.md`,
`{agency-root}/scripts/save-state.py`). If a tree is not deployed, every reference
into it silently 404s at runtime — with no error, because most of those call sites
are fire-and-forget.

## Where the root comes from

`{agency-root}` resolves in this order, highest first:

1. `$AGENCY_HOME`
2. `$CLAUDE_CONFIG_DIR` — Claude Code's own config-dir override. If a user has
   relocated it, that is the only directory Claude Code reads skills, agents and
   hooks from, so it is the only directory worth installing into.
3. `~/.claude`

**One idiom, five places, and they must not drift:**

| Where | Form |
|---|---|
| `hooks/lib/resolve-root.sh` | `AGENCY_ROOT="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"` — the SSOT |
| `install.sh` | `CLAUDE_HOME="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"` |
| `install.ps1` | `$env:AGENCY_HOME` → `$env:CLAUDE_CONFIG_DIR` → `$env:USERPROFILE\.claude` |
| `cli/bin/agency.js` | `process.env.AGENCY_HOME \|\| process.env.CLAUDE_CONFIG_DIR \|\| ~/.claude` |
| `scripts/*.py` | `os.environ.get("AGENCY_HOME") or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()/".claude"` |

Every shell script under `hooks/` and `scripts/` sources the resolver **by a path
relative to its own location**, because resolving the root is exactly the thing it
cannot do yet:

```sh
hooks/foo.sh      . "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
hooks/lib/foo.sh  . "$(dirname "${BASH_SOURCE[0]:-$0}")/resolve-root.sh"     2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
scripts/foo.sh    . "$(dirname "${BASH_SOURCE[0]:-$0}")/../hooks/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
```

The trailing `||` is a degraded fallback so a partial install cannot hard-fail a
hook on Claude Code's hot path. `.github/scripts/check-hardcoded-root.sh` fails the
build if any other form of the default root reappears in executable code.

Python scripts inline the equivalent instead of importing, because several are run
by absolute path from arbitrary working directories where an import would not
resolve.

## The deploy matrix

| Repo tree | `install.sh` | `install.ps1` | `agency init` | `agency upgrade` | Notes |
|---|:--:|:--:|:--:|:--:|---|
| `skills/` | ✓ | ✓ | ✓ | ✓ | directory layout `skills/<name>/SKILL.md` + sibling assets |
| `agents/` | ✓ | ✓ | ✓ | ✓ | `.md` only in the CLI path |
| `core/` | ✓ | ✓ | ✓ | ✓ | |
| `hooks/` | ✓ | ✓ | ✓ | ✓ | incl. `hooks/lib/` (carries `resolve-root.sh`) and `hooks/fable/`; `+x` on `.sh` |
| `runbooks/` | ✓ | ✓ | ✓ | ✓ | docs only |
| `scripts/` | ✓ | ✓ | ✓ | ✓ | `+x` on `.sh`/`.py`/`.js`; `__pycache__` excluded |

Not deployed by design: `docs/`, `evals/`, `plans/`, `openspec/`, `memory/`,
`agents-archive/`, `cli/` (the CLI is symlinked, not copied).

`memory/` is created empty by the installers — the repo's `memory/` is a runtime
*sample*, not a mirror of anyone's memory, and is never copied over a user's.

## Where the list lives

Change all four in the same commit:

- `install.sh` — one `*_SRC` / `*_DEST` block per tree
- `install.ps1` — the `foreach ($tree in @("hooks", "runbooks", "scripts"))` loop
- `cli/commands/init.js` — `sync*` calls in steps 3–4d
- `cli/commands/upgrade.js` — the matching `sync*` calls in the post-pull section

The CLI path shares one mechanism: `syncTree()` in `cli/commands/sync-assets.js`.
Adding a tree there is a one-line wrapper plus one call in each of `init.js` and
`upgrade.js`.

## Verifying a change

**CI does this on every push and PR to main** — `.github/workflows/installers.yml`
runs `install.sh` on `ubuntu-latest` and `install.ps1` on `windows-latest`, and each
job asserts: full skill count installed, every `{agency-root}/…` reference resolves,
`hooks/emit-metric.sh` writes a real event line, and a *second* install into a
different `AGENCY_HOME` resolves there and does not leak into `$HOME/.claude`.

That last one is the case that had no test before: it is what proves the deployed
scripts read from the same directory the installer wrote to.

To reproduce locally, both installers accept `AGENCY_HOME`, so a full install can be
dry-run into `/tmp` without touching a real `~/.claude`:

```bash
rm -rf /tmp/agency-verify
AGENCY_HOME=/tmp/agency-verify node cli/bin/agency.js init
AGENCY_HOME=/tmp/agency-verify-sh bash install.sh
```

Then run the same reference check CI runs — this is the check that catches a
missing tree, which a bare `ls` will not:

```bash
bash .github/scripts/verify-agency-refs.sh /tmp/agency-verify
bash .github/scripts/check-hardcoded-root.sh
```

`verify-agency-refs.sh` scans the deployed `agents/`, `core/`, `skills/` and
`runbooks/` trees for `{agency-root}/<tree>/…` and `~/.claude/<tree>/…` references
and asserts each one resolves to a real file. `verify-agency-refs.ps1` is its
Windows twin.

## Failure modes this file exists to prevent

Two real bugs motivated writing it down, both of which reported success while
shipping nothing:

- **Flat-skill layout drift.** `install.sh` and `install.ps1` globbed `skills/*.md`
  long after the repo moved to `skills/<name>/SKILL.md`. Both installed **zero**
  skills and still printed `✓ N skills installed` with `N=0`. Both now iterate skill
  *directories* and print a loud repo-vs-installed count mismatch — the same guard
  the CLI path already had.
- **Untracked trees.** `runbooks/` was deployed by nothing at all, and `hooks/` and
  `scripts/` were each deployed by only one of the two paths, so which references
  worked depended on which installer you happened to run.
- **Two roots in one install.** The installers honoured `AGENCY_HOME`; every script
  under `hooks/` and `scripts/` did not, hardcoding `$HOME/.claude` instead. A
  custom-root install therefore wrote to one directory and was read from another —
  hooks appended to the wrong log, `startup-sync.sh` git-synced the wrong repo, and
  `skill-audit.py` reported every deployed skill's references as dead. Nothing
  failed loudly, because a hook writing to the wrong file still exits 0.

The lesson in all three cases: a deploy step that cannot fail loudly will drift
silently. That is why the CI workflow asserts *outcomes* (a file exists, an event
line was written, nothing leaked) rather than exit codes.
Every tree in the matrix above should have a count printed after it, and any
count-vs-source mismatch should warn.

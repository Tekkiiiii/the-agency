# Install Layout — what each installer deploys

There are three installers, and they must agree. Every gap between them is not a
cosmetic difference: it is a class of **dangling reference**, because shipped agent
defs, runbooks, skills and scripts refer to their siblings by deployed path
(`{agency-root}/hooks/emit-metric.sh`, `{agency-root}/runbooks/service-lookups.md`,
`{agency-root}/scripts/save-state.py`). If a tree is not deployed, every reference
into it silently 404s at runtime — with no error, because most of those call sites
are fire-and-forget.

## The deploy matrix

`{agency-root}` = `$AGENCY_HOME` if set, else `~/.claude`.

| Repo tree | `install.sh` | `install.ps1` | `agency init` | `agency upgrade` | Notes |
|---|:--:|:--:|:--:|:--:|---|
| `skills/` | ✓ | ✓ | ✓ | ✓ | directory layout `skills/<name>/SKILL.md` + sibling assets |
| `agents/` | ✓ | ✓ | ✓ | ✓ | `.md` only in the CLI path |
| `core/` | ✓ | ✓ | ✓ | ✓ | |
| `hooks/` | ✓ | ✓ | ✓ | ✓ | incl. `hooks/lib/` and `hooks/fable/`; `+x` on `.sh` |
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

Both installers accept `AGENCY_HOME`, so a full install can be dry-run into `/tmp`
without touching a real `~/.claude`:

```bash
rm -rf /tmp/agency-verify
AGENCY_HOME=/tmp/agency-verify node cli/bin/agency.js init
AGENCY_HOME=/tmp/agency-verify-sh bash install.sh
```

Then check that references actually resolve in the deployed tree — this is the
check that catches a missing tree, which a bare `ls` will not:

```bash
cd /tmp/agency-verify
grep -rhoE '(\{agency-root\}|~/\.claude)/runbooks/[A-Za-z0-9._/-]+\.md' agents core skills \
  | sed -E 's|.*/runbooks/||' | sort -u \
  | while read -r r; do [ -f "runbooks/$r" ] || echo "MISSING: runbooks/$r"; done
```

Swap `runbooks` for `hooks` or `scripts` to check those trees.

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

The lesson in both cases: a deploy step that cannot fail loudly will drift silently.
Every tree in the matrix above should have a count printed after it, and any
count-vs-source mismatch should warn.

# Memory v2 — Schema, Read-Path Integrity, and Weekly Curation

Extends the base memory system (`core/memory/MEMORY.md`) with a typed schema,
an integrity canary for the read path, an external-stores registry, and a
weekly self-grading curation pipeline. Built incrementally as P0-P3; this doc
is the spec for all four.

**Scope note:** these scripts (`scripts/mem-*.py`, `scripts/mem-*.sh`,
`scripts/canary-*.sh`, `scripts/memory-frontmatter-*.py`) are written for a
Claude Code user's native `~/.claude/memory/` estate — they are optional,
standalone tooling, not wired into `agency init` or the `~/.agency/`
product-memory model described in the rest of `core/memory/`. Run them
directly (`bash ~/.claude/scripts/mem-gardener.sh`, `mem find <query>`, etc.)
against your own `~/.claude/` checkout; nothing here modifies the CLI's
generated `{agency-root}/memory/` scaffold.

## P0 — Read-path integrity canary (checks R1, R8)

A fixed, checksummed fixture file (`memory/.canary.md`) with a hash recorded
in `memory/.canary.sha256`. Two check modes:

- **Disk check** (`scripts/canary-check.sh`) — reads the file directly off
  disk and byte-compares against the recorded hash. Proves the file itself
  isn't corrupted or truncated.
- **Session check** (`scripts/canary-session-check.sh`) — a live agent reads
  the canary file through its own Read tool (i.e. through whatever
  hooks/proxies/context-optimization layers sit between disk and context),
  pipes the observed text in via stdin, and the script hashes and compares
  that. This is the check that actually matters: a lossy compression or
  proxy layer can pass the disk check while silently corrupting what agents
  see. Treat any session-check mismatch as a P0 incident.

Both checks log to `memory/metrics/canary-check.log` and the session check
also writes `memory/.canary-session.json` for `mem-scorecard.py`'s R1 check
to pick up.

## P1 — Typed frontmatter schema unification

Every memory file gets required YAML frontmatter: `name`, `type`,
`description`, `created`, `review-by` (optional), `links`. Two scripts:

- `scripts/memory-frontmatter-add.py` — prepends frontmatter to files that
  don't have any (pure delta edit, idempotent, never touches body content).
- `scripts/memory-frontmatter-migrate.py` — fills missing *required* fields
  on files that already have a frontmatter fence but are incomplete.

Both are scoped to `.md` files directly inside a target memory dir and its
`lessons/` subdir — they skip control/index files (`MEMORY.md`, `index.md`,
`decisions.md`, `next-session.md`, `CLAUDE.md`, etc. — see the scripts'
`EXCLUDE_NAMES` for the full list) since those are mechanically owned by
other tooling (save-state, recall, pd-resume) and schema changes would
collide with their format.

## D5 — External stores registry

Any knowledge store outside the flat-file memory estate (a vector DB, a
knowledge graph, a per-project code index, a research-notes tool, etc.)
gets one entry in `memory/external-stores.md`: what it holds, when to query
it instead of grepping memory files, who owns writing to it, and how it's
accessed. `lint-memory` (folded into the scorecard's Score step) cross-checks
memory-file mentions of external stores against this registry — anything
mentioned but not listed is "stranded" and fails D5. Template entry:

```markdown
## {Store Name}
- **Holds:** what kind of data lives here
- **Trigger:** when an agent should query this instead of grep
- **Owner:** which agent/pipeline writes to it
- **Access:** tool/API surface used to read it
```

## P2 — Knowledge graph + search

- `scripts/mem-graph-build.py` — walks the memory estate (global memory +
  Claude Code's per-cwd auto-memory folder), builds a graph of memory files
  as nodes and `[[wikilink]]`/`links:` frontmatter as edges, writes
  `memory/graphify-out/memory-graph.json` + `.html` (visual viewer) and a
  dead-links report.
- `scripts/mem-find.sh` — 4-tier ranked search across the memory estate:
  MEMORY.md/index.md title match → frontmatter match → body grep → 1-hop
  link expansion from tier 1-3 hits.
- `scripts/mem` — thin CLI wrapper: `mem graph` (rebuild + open the viewer),
  `mem find <query>`.

## P3 — Gardener (weekly curation) + 30-check scorecard

**Gardener** (`scripts/mem-gardener.sh`, full runbook in
`core/memory/gardener-runbook.md`): a six-step weekly pipeline — Lint,
Curate, Distill, Rebuild, Evaluate, Score. Delta edits only, one git commit
per run (rollback = `git revert HEAD`), destructive changes (merge/archive/
delete) always land in `memory/ops/approval-queue.md` for manual approval,
never auto-applied. Self-grading: if the post-run FAIL count is higher than
the pre-run count, the driver reverts its own memory changes and marks the
run `reverted_regression` instead of leaving a regression live.

**Scorecard** (`scripts/mem-scorecard.py`): 30 checks across three families
— **R** (Read-path, R1-R10: canary, compression integrity, retrieval
correctness...), **D** (Distillation/schema, D1-D10: frontmatter
completeness, decision-entry linkage, external-stores registry parity,
review-by expiry, contradiction queue...), **S** (Storage/structure,
S1-S10). Each check returns `PASS` / `FAIL` / `NOT_IMPLEMENTED` plus a
one-line evidence string. Honesty rule: MEASURED vs ESTIMATED vs PROXY vs
NOT_IMPLEMENTED must stay distinct in the evidence text — an honest partial
baseline beats an inflated one. Output: `memory/scorecard.md` (current
scores + per-check table + a rolling trend).

## Skill QA gate

`scripts/skill-audit.py` — a permanent gate: audits every installed skill
for structural validity (frontmatter, required sections, broken references).
Re-run after any skill install/upgrade, not just on a schedule.

## Directory layout this adds

```
memory/
├── .canary.md              ← P0 fixed fixture (do not edit)
├── .canary.sha256          ← P0 recorded hash
├── .canary-session.json    ← P0 last session-check result
├── external-stores.md      ← D5 registry
├── scorecard.md            ← P3 output (scores + trend)
├── graphify-out/           ← P2 output (graph json/html, dead-links)
├── ops/
│   ├── approval-queue.md       ← destructive curation changes, manual approval
│   ├── contradiction-queue.md  ← flagged contradictions, manual approval
│   └── gardener-last-run.json  ← P3 self-grading marker
└── qa/
    ├── dead-links.txt       ← P2 output
    └── recall-evals.md      ← D-family recall proxy evidence
```

See also: [[gardener-runbook]]

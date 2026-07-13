---
name: gardener-runbook
type: reference
description: Weekly Memory v2 curation pipeline — runbook for scripts/mem-gardener.sh
created: 2026-07-10
links: []
---
# Gardener Runbook

Weekly "sleep-time curation" pass over the memory estate. Spec:
`core/memory/memory-v2.md` §P3.

## What it does

Driver: `scripts/mem-gardener.sh`. Six-step pipeline, in order:

1. **Lint** — schema validity, index/file parity, dead links, orphan nodes, token
   budget, registry format, expired `review-by`, canary status. (Folded into the
   R-family checks inside step 6 — not a separate tool.)
2. **Curate** — flag near-duplicates and contradiction candidates; propose
   merges/archives as delta edits. Trivial fixes (missing index line, malformed
   row) auto-apply. Destructive changes (merge, archive, delete) go to
   `memory/ops/approval-queue.md` — **never auto-applied**. The bash driver only
   stubs this step (touches the queue file); real curation judgment requires an
   LLM pass — run your memory-maintenance PD (or equivalent agent) with
   "gardener curate pass".
3. **Distill** — oversized lesson files get principles extracted, append-preserving
   (never destructive rewrite). Same LLM-judgment constraint as Curate — bash
   driver stubs this step; run the same PD with "gardener distill pass" for the
   real step.
4. **Rebuild** — `scripts/mem-graph-build.py` regenerates `memory-graph.json` +
   `memory-graph.html` + `dead-links.txt`.
5. **Evaluate** — recall-eval mechanical proxy runs as part of D1 inside Score.
6. **Score** — `scripts/mem-scorecard.py` runs all 30 checks, writes
   `memory/scorecard.md` (current scores + trend), emits metric events.

## Safety rails

- **Delta edits only.** A full-file LLM rewrite of any memory store is a lint
  violation in itself.
- **One git commit per run.** Rollback is `git revert HEAD` — never a manual
  multi-file undo.
- **Destructive operations require explicit manual approval** via
  `memory/ops/approval-queue.md`. Never auto-applied, ever — no automatic
  memory deletion.
- **Self-grading revert.** The driver compares total FAIL-check count before vs
  after each run. If FAILs increased, it reverts (`git checkout -- memory`)
  and marks the run `reverted_regression` in the marker file instead of
  leaving a regression live.

## Manual run

```bash
bash ~/.claude/scripts/mem-gardener.sh
```

Writes a timestamped log to `memory/ops/gardener-run-{ts}.log`, a status marker
to `memory/ops/gardener-last-run.json` (read by scorecard check R10), and
emits a `gardener_run` metric event.

## Scheduled run (optional)

Point a `launchd` (macOS) or `cron`/systemd-timer (Linux) job at
`scripts/mem-gardener.sh` on whatever cadence fits — weekly is the reference
default. Activating a schedule is an operator decision, not something the
driver does for itself; the script and this runbook are ready to be pointed
at from any scheduler.

## Known gaps (honest, first-run baseline)

- Curate and Distill are stubs in the bash driver — the pipeline shape exists,
  the LLM-judgment steps do not run automatically yet. First real curate/distill
  pass should be a manual PD invocation, not a cron job, until there's a track
  record of trivial-fix auto-apply being safe.
- No near-duplicate/contradiction detector exists (needs embedding similarity
  or LLM judgment — see D7 in the scorecard).
- R10 (Gardener liveness) will legitimately FAIL until this has run at least
  once and the marker file exists.

See also: [[memory-v2]]

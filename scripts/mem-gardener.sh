#!/bin/bash
# mem-gardener.sh — weekly Memory v2 curation pipeline (L5 Gardener).
# Pipeline order (per core/memory/memory-v2.md §L5):
#   1. Lint  2. Curate  3. Distill  4. Rebuild  5. Evaluate  6. Score
# Safety rails: delta edits only, one git commit per run (one-command rollback),
# destructive ops (merge/archive/delete) never auto-applied — go to approval
# queue for the user. Self-grading: if total FAIL count increases post-run, revert
# and flag instead of leaving a regression live.
# Runbook: memory/gardener-runbook.md — read that first if this script surprises you.
# macOS bash 3.2 portable — no bash-4isms (matches canary-check.sh convention).

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
cd "$CLAUDE_DIR"

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OPS_DIR="$CLAUDE_DIR/memory/ops"
mkdir -p "$OPS_DIR"
LOG="$OPS_DIR/gardener-run-$(date -u +%Y%m%dT%H%M%SZ).log"
MARKER="$OPS_DIR/gardener-last-run.json"
APPROVAL_QUEUE="$OPS_DIR/approval-queue.md"
SCORECARD="$CLAUDE_DIR/memory/scorecard.md"
EMIT="$CLAUDE_DIR/memory/metrics/emit-metric.sh"

PYBIN="$HOME/.local/share/uv/tools/graphifyy/bin/python"
[ -x "$PYBIN" ] || PYBIN="python3"

exec > >(tee -a "$LOG") 2>&1
echo "=== Gardener run $TS ==="

PRE_FAILS=0
[ -f "$SCORECARD" ] && PRE_FAILS=$(grep -c '| FAIL |' "$SCORECARD" || true)
echo "Baseline FAIL count: $PRE_FAILS"

echo "--- 1. Lint ---"
# ponytail: lint (schema validity, index/file parity, dead links, orphan nodes,
# token budget, registry format, review-by, canary) is folded into the R-family
# checks inside step 6 (Score) rather than duplicated in a standalone tool —
# same 8 checks either way. Split out into scripts/mem-lint.py only if something
# other than the Score step ever needs lint results on their own.

echo "--- 2. Curate ---"
# Near-duplicate / contradiction detection needs embedding similarity or LLM
# judgment — not something a bash driver can do. This step only guarantees the
# approval queue file exists (so D7 has a real, checkable target). Real
# curation is an LLM task: run your memory-maintenance PD (or equivalent
# agent) with "gardener curate pass" to actually flag duplicates/contradictions
# and propose delta-edit merges. Trivial fixes (missing index line, malformed
# row) still auto-apply there; destructive changes (merge/archive/delete)
# always land in $APPROVAL_QUEUE for the user, never auto-applied.
touch "$APPROVAL_QUEUE"

echo "--- 3. Distill ---"
# Same constraint as Curate: extracting principles from oversized lesson files
# append-preserving needs LLM judgment. Stub only — run your memory-maintenance
# PD with "gardener distill pass" for the real step.

echo "--- 4. Rebuild ---"
"$PYBIN" "$CLAUDE_DIR/scripts/mem-graph-build.py"

echo "--- 5. Evaluate ---"
# The recall-eval mechanical proxy runs as part of D1 inside Score (step 6) —
# no separate invocation needed.

echo "--- 6. Score ---"
"$PYBIN" "$CLAUDE_DIR/scripts/mem-scorecard.py"

POST_FAILS=0
[ -f "$SCORECARD" ] && POST_FAILS=$(grep -c '| FAIL |' "$SCORECARD" || true)
echo "Post-run FAIL count: $POST_FAILS"

echo "--- Self-grading ---"
if [ "$POST_FAILS" -gt "$PRE_FAILS" ]; then
  echo "REGRESSION: FAIL count $PRE_FAILS -> $POST_FAILS. Reverting this run's memory changes."
  git checkout -- memory 2>/dev/null || true
  STATUS="reverted_regression"
else
  echo "OK: FAIL count $PRE_FAILS -> $POST_FAILS (no regression)."
  STATUS="ok"
fi

echo "--- Git commit (one-command rollback: git revert HEAD) ---"
git add memory 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "chore(gardener): weekly memory curation run $(date -u +%Y-%m-%d)" --quiet
  echo "Committed."
else
  echo "No changes to commit."
fi

cat > "$MARKER" <<EOF
{"ts":"$TS","status":"$STATUS","pre_fails":$PRE_FAILS,"post_fails":$POST_FAILS}
EOF

[ -x "$EMIT" ] && "$EMIT" "{\"ts\":\"$TS\",\"event\":\"gardener_run\",\"status\":\"$STATUS\",\"pre_fails\":$PRE_FAILS,\"post_fails\":$POST_FAILS}" 2>/dev/null || true

echo "=== Gardener run complete: $STATUS ==="

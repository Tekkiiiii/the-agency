#!/bin/bash
# startup-sync.sh — SessionStart hook: fast-forward the agency root from origin/main.
# Portable (macOS bash 3.2, no coreutils `timeout`). Never stashes, never merges:
#   - fetch is bounded by a background watchdog (SYNC_FETCH_TIMEOUT, default 5s)
#   - pull runs ONLY when the tracked tree is clean and the branch is main
#   - dirty tree -> one warning line, local work untouched
# Fail-open: any error prints a warning and exits 0 (never blocks session start).

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

TIMEOUT_SEC="${SYNC_FETCH_TIMEOUT:-5}"

cd "$AGENCY_ROOT" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || { echo "⚠️  $AGENCY_ROOT is not a git repo — skipping sync"; exit 0; }

# run_with_timeout SECONDS CMD... — returns CMD's exit code, or 124 on timeout.
run_with_timeout() {
  local secs="$1"; shift
  "$@" >/dev/null 2>&1 &
  local pid=$!
  ( sleep "$secs"; kill -TERM "$pid" 2>/dev/null ) >/dev/null 2>&1 &
  local watchdog=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  if kill -0 "$watchdog" 2>/dev/null; then
    kill -TERM "$watchdog" 2>/dev/null
    wait "$watchdog" 2>/dev/null
  else
    rc=124
  fi
  return $rc
}

if ! GIT_TERMINAL_PROMPT=0 run_with_timeout "$TIMEOUT_SEC" git fetch -q origin main; then
  echo "⚠️  Config sync: fetch failed or timed out (${TIMEOUT_SEC}s) — skipping"
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
LOCAL=$(git rev-parse @ 2>/dev/null)
REMOTE=$(git rev-parse origin/main 2>/dev/null)
BASE=$(git merge-base @ origin/main 2>/dev/null)

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "✅ Config up to date"
  exit 0
fi
if [ "$REMOTE" = "$BASE" ]; then
  echo "✅ Config ahead of remote (unpushed local commits) — no pull needed"
  exit 0
fi
if [ "$BRANCH" != "main" ]; then
  echo "⚠️  Config sync: on branch '$BRANCH', not main — skipping pull"
  exit 0
fi

DIRTY=$(git status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')
if [ "$DIRTY" != "0" ]; then
  BEHIND=$(git rev-list --count @..origin/main 2>/dev/null)
  echo "⚠️  Config sync skipped: ${DIRTY} uncommitted tracked change(s); remote is ${BEHIND} commit(s) ahead. Commit, then pull manually (no auto-stash)."
  exit 0
fi

if [ "$LOCAL" = "$BASE" ]; then
  if git pull --ff-only -q origin main >/dev/null 2>&1; then
    echo "✅ Config synced from GitHub"
  else
    echo "⚠️  Config sync: fast-forward pull failed — run 'git -C "$AGENCY_ROOT" pull --ff-only' manually"
  fi
else
  echo "⚠️  Config diverged from remote — manual merge needed (nothing changed locally)"
fi
exit 0

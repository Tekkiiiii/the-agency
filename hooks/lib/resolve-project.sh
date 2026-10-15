#!/usr/bin/env bash
# resolve-project.sh — shared function: resolve cwd to project path
# Source this file; call resolve_project_path; result in SPAWN_LOG_FILE var.
# Usage: source {agency-root}/hooks/lib/resolve-project.sh && resolve_project_path
#
# The matching itself lives in hooks/lib/spawn_project.py (the ONE resolver, also used by ledger.py, model-pin.py and
# scripts/skill-route.py): path-boundary prefix match (proj is not proj2), Windows drive paths (D:\x, D:/x, d:\X, /d/x),
# `~` expanded against the OS home, agency root = AGENCY_HOME -> CLAUDE_CONFIG_DIR -> ~/.claude. This file used to match with
# grep "^$path" and a POSIX $HOME, so proj matched proj2 and a Windows CLAUDE_PROJECT_DIR never matched anything.
# Table override for tests: SPAWN_MEDIUM_TERM.

. "$(dirname "${BASH_SOURCE[0]:-$0}")/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

resolve_project_path() {
  # Testability override: if the caller already exported SPAWN_LOG_FILE, honor it
  # and skip resolution entirely (used to point scripts at a /tmp copy in tests).
  if [ -n "${SPAWN_LOG_FILE:-}" ]; then
    return 0
  fi

  local FALLBACK="$AGENCY_ROOT/logs/spawns.jsonl"
  local LIB
  LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
  local PY="${CLAUDE_PYTHON:-}"
  [ -n "$PY" ] || PY="$(command -v python3 || command -v python || true)"

  local resolved=""
  if [ -n "$PY" ]; then
    # CLAUDE_PROJECT_DIR (else the cwd) is read by spawn_project itself. python on Windows prints CRLF: strip the CR.
    resolved="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import spawn_project; print(spawn_project.resolve_log_file())' "$LIB" 2>/dev/null)" || resolved=""
    resolved="${resolved%$'\r'}"
  fi
  [ -n "$resolved" ] || resolved="$FALLBACK"

  # Ensure the log dir exists (project or fallback)
  mkdir -p "$(dirname "$resolved")" 2>/dev/null || true
  SPAWN_LOG_FILE="$resolved"
  return 0
}

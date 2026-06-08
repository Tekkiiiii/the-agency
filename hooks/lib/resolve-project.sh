#!/usr/bin/env bash
# resolve-project.sh — shared function: resolve cwd to project path
# Source this file; call resolve_project_path; result in SPAWN_LOG_FILE var.
# Usage: source ~/.claude/hooks/lib/resolve-project.sh && resolve_project_path

resolve_project_path() {
  local MEDIUM_TERM="$HOME/.claude/memory/medium-term.md"
  local FALLBACK="$HOME/.claude/logs/spawns.jsonl"
  local CWD="${CLAUDE_PROJECT_DIR:-$PWD}"

  # Ensure fallback log dir exists
  mkdir -p "$(dirname "$FALLBACK")" 2>/dev/null || true

  if [ ! -f "$MEDIUM_TERM" ]; then
    SPAWN_LOG_FILE="$FALLBACK"
    return 0
  fi

  # Parse Active Projects table: extract paths from medium-term.md
  # Lines look like: | project | `/path/` | pd-name | ... |
  # or:              | project | `~/.claude/projects/...` | ...
  # We expand ~ and find the longest-prefix match against CWD
  local BEST_MATCH_LEN=0
  local BEST_PROJECT_PATH=""

  while IFS= read -r line; do
    # Match table rows with backtick-quoted path in 2nd column
    if printf '%s' "$line" | grep -qE '^\|[^|]+\|[[:space:]]*`[^`]+`'; then
      local raw_path
      raw_path=$(printf '%s' "$line" | sed -n 's/^|[^|]*|[[:space:]]*`\([^`]*\)`.*/\1/p' | head -1)
      if [ -z "$raw_path" ]; then
        continue
      fi
      # Expand ~ to home
      local expanded_path="${raw_path/#\~/$HOME}"
      # Remove trailing slash and /memory suffix — medium-term.md stores memory paths like
      # ~/.claude/projects/system-improvement/memory/ but we need the project root
      local normalized="${expanded_path%/}"
      normalized="${normalized%/memory}"

      # Check if CWD starts with this project root path
      if [ -n "$normalized" ] && printf '%s' "$CWD" | grep -q "^${normalized}"; then
        local path_len=${#normalized}
        if [ "$path_len" -gt "$BEST_MATCH_LEN" ]; then
          BEST_MATCH_LEN="$path_len"
          BEST_PROJECT_PATH="$normalized"
        fi
      fi
    fi
  done < "$MEDIUM_TERM"

  if [ -n "$BEST_PROJECT_PATH" ]; then
    local log_dir="${BEST_PROJECT_PATH}/memory"
    mkdir -p "$log_dir" 2>/dev/null || true
    SPAWN_LOG_FILE="${log_dir}/spawns.jsonl"
  else
    SPAWN_LOG_FILE="$FALLBACK"
  fi

  return 0
}

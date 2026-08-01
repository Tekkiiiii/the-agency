#!/usr/bin/env bash
# check-hardcoded-root.sh — regression guard for the Wave 13 AGENCY_HOME pass.
#
# Before Wave 13 every script under hooks/ and scripts/ resolved the agency root
# as a literal $HOME/.claude, so a user who installed with a custom AGENCY_HOME
# got an install in one directory read from another. The fix routes all of them
# through hooks/lib/resolve-root.sh (or its documented Python twin).
#
# This guard fails the build if a new hardcoded root sneaks back in. It scans
# executable code only — comments and prose are stripped first, because the
# repo legitimately writes "~/.claude" when describing the default install.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1

# Lines that are ALLOWED to contain the literal default root:
#   1. hooks/lib/resolve-root.sh          — the definition itself
#   2. the inline degraded fallback       — `... || AGENCY_ROOT="${AGENCY_HOME:-...}"`
#   3. the documented Python twin         — `or (Path.home() / ".claude")` etc.
#   4. skill-audit.py's content matchers  — they match the literal "~/.claude/"
#                                           TEXT authored inside SKILL.md files,
#                                           not a path this repo resolves.
#
# The twin's tail (`or os.path.join(home, ".claude")`) is allowed only when the
# expression ENDS there — i.e. it yields the root itself. The same call with a
# path glued on (`".claude/logs/spawns.jsonl"`) is the bug and must still fail.
ALLOW='resolve-root\.sh" 2>/dev/null \|\| AGENCY_ROOT=|or \(Path\.home\(\) / "\.claude"\)|or \(HOME / "\.claude"\)|or os\.path\.join\(home, .\.claude.\)[[:space:]]*$|RUNTIME_ROOTS|HOME_REF_RE|p\[len\("~/\.claude/"\):\]|"~/\.claude/state/"|"~/\.claude/\.context/"'

offenders=0

scan() {
  local f="$1"
  # strip full-line comments (# for sh/py, // for js) before matching
  local hits
  # NOTE: the .claude alternatives deliberately do NOT anchor a closing quote.
  # An earlier version matched only `home, ".claude"` and therefore walked
  # straight past `os.path.join(home, ".claude/logs/spawns.jsonl")` in
  # hooks/spawn-logger.sh — a real hardcoded root that shipped anyway. Match the
  # prefix, and let ALLOW carry the exemptions.
  hits=$(grep -nE '\$HOME/\.claude|~/\.claude|HOME / "\.claude|home, .?"\.claude|homedir\(\), .\.claude' "$f" 2>/dev/null \
         | grep -vE ':[[:space:]]*(#|//)' \
         | grep -vE "$ALLOW" || true)
  if [ -n "$hits" ]; then
    echo "--- $f"
    echo "$hits"
    offenders=$((offenders + 1))
  fi
}

for f in hooks/*.sh hooks/lib/*.sh scripts/*.sh scripts/*.py; do
  [ -f "$f" ] || continue
  case "$f" in
    hooks/lib/resolve-root.sh) continue ;;
  esac
  scan "$f"
done

if [ "$offenders" -ne 0 ]; then
  cat <<'EOF'

FAIL: the files above resolve the agency root by hardcoding the default.

Use the shared resolver instead:

  hooks/foo.sh      . "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
  hooks/lib/foo.sh  . "$(dirname "${BASH_SOURCE[0]:-$0}")/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
  scripts/foo.sh    . "$(dirname "${BASH_SOURCE[0]:-$0}")/../hooks/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

  *.py              AGENCY_ROOT = Path(os.environ.get("AGENCY_HOME")
                                       or os.environ.get("CLAUDE_CONFIG_DIR")
                                       or (Path.home() / ".claude"))

If a hit is genuinely prose or a content matcher rather than a path this repo
resolves, add it to ALLOW in this script with a one-line reason.
EOF
  exit 1
fi

echo "OK: no hardcoded agency root in hooks/ or scripts/"

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
#   5. the INLINED ladder in install.sh    — neither can source resolve-root.sh:
#      and rescue.sh                         install.sh may be the thing that
#                                           puts it there, and rescue.sh is run
#                                           as `curl ... | bash`, where there is
#                                           no script directory at all. Both
#                                           write the full three-level ladder
#                                           verbatim; the pattern below matches
#                                           only that exact expression.
#   6. rescue.sh's discovery candidate list — a list of places an EXISTING repo
#                                           may already sit (alongside
#                                           ~/the-agency), searched after
#                                           $AGENCY_ROOT. It adopts a repo, it
#                                           never resolves a root to write to.
#
# The twin's tail (`or os.path.join(home, ".claude")`) is allowed only when the
# expression ENDS there — i.e. it yields the root itself. The same call with a
# path glued on (`".claude/logs/spawns.jsonl"`) is the bug and must still fail.
ALLOW='resolve-root\.sh" 2>/dev/null \|\| AGENCY_ROOT=|or \(Path\.home\(\) / "\.claude"\)|or \(HOME / "\.claude"\)|or os\.path\.join\(home, .\.claude.\)[[:space:]]*$|RUNTIME_ROOTS|HOME_REF_RE|p\[len\("~/\.claude/"\):\]|"~/\.claude/state/"|"~/\.claude/\.context/"|="\$\{AGENCY_HOME:-\$\{CLAUDE_CONFIG_DIR:-\$HOME/\.claude\}\}"$|^[0-9]+:[[:space:]]*for loc in "\$AGENCY_ROOT" "\$HOME/\.claude" '

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
  #
  # The quote class is deliberately loose (`.{0,2}` rather than a literal `"`).
  # An earlier version required a double quote and was therefore blind to every
  # python block written inside a `python3 -c "..."` string — those must use
  # single quotes throughout, so a hardcoded root there could never be seen.
  # hooks/lib/log-spawn-from-agent.sh and log-spawn-end-from-agent.sh are both
  # that shape.
  hits=$(grep -nE '\$HOME/\.claude|~/\.claude|HOME / "\.claude|home, .{0,2}\.claude|homedir\(\), .\.claude' "$f" 2>/dev/null \
         | grep -vE ':[[:space:]]*(#|//)' \
         | grep -vE "$ALLOW" || true)
  if [ -n "$hits" ]; then
    echo "--- $f"
    echo "$hits"
    offenders=$((offenders + 1))
  fi
}

# install.sh and rescue.sh are in the list as of Wave 16. They are the two
# entry points a user runs BEFORE anything is deployed, so a hardcoded root
# there sends the whole install to the wrong directory — the loudest possible
# version of the defect, and the only two files that were never checked for it.
for f in hooks/*.sh hooks/lib/*.sh scripts/*.sh scripts/*.py install.sh rescue.sh; do
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

  *.py              copy the agency_root(home) twin from
                    hooks/lib/resolve-root.sh VERBATIM, then
                    AGENCY_ROOT = Path(agency_root(str(HOME)))

If a hit is genuinely prose or a content matcher rather than a path this repo
resolves, add it to ALLOW in this script with a one-line reason.
EOF
  exit 1
fi

echo "OK: no hardcoded agency root in hooks/, scripts/, install.sh or rescue.sh"

# ---------------------------------------------------------------------------
# Second guard: the Python twin must stay ONE idiom.
#
# Every python block under hooks/ — and, since Wave 16, every scripts/*.py —
# resolves the root through an inlined `agency_root(home)` whose nt branch
# rewrites an MSYS-style AGENCY_HOME (/c/Users/me/.claude) into a form native
# Windows python can open. The duplication is forced for the hooks — under Git
# Bash a hook's own directory is an MSYS path too, so an import bootstrap would
# trip over the very string format the helper exists to fix
# (hooks/lib/resolve-root.sh explains this in full). scripts/*.py could import
# it; they inline it anyway so that ONE form of this function exists in the repo
# and this check can see all of them.
#
# Forced duplication drifts. These two checks stop it:
#   A. every copy of agency_root() is byte-identical
#   B. no python block resolves the root any OTHER way — the count of raw twin
#      expressions in a file must equal its count of agency_root definitions,
#      so a second, unnormalised resolve cannot slip in beside it.
# ---------------------------------------------------------------------------
twin_text=""
twin_ref=""
twin_offenders=0

extract_twin() {
  awk '/def agency_root\(home\):/,/^    return root$/' "$1"
}

# scripts/*.py joined this list in Wave 16. Wave 15 had left them on the plain
# three-line twin, reasoning that a native python3 could not load their MSYS-form
# script path anyway so normalising the env read would not help. Measured on
# windows-latest (run 30689704116): under plain Git Bash the script loads fine —
# MSYS2 converts the path argument — and it is the ENV read that breaks, exactly
# as it did in the hooks (FileNotFoundError on '\d\a\_temp\...\skills'). The
# deferral rested on an inference; the inference was wrong.
for f in hooks/*.sh hooks/lib/*.sh scripts/*.py; do
  [ -f "$f" ] || continue
  case "$f" in
    hooks/lib/resolve-root.sh) continue ;;  # carries the twin as documentation
  esac

  # grep -c already prints 0 on no-match; a `|| echo 0` fallback would append a
  # SECOND zero and every later [ -eq ] would blow up on "0\n0".
  defs=$(grep -c 'def agency_root(home):' "$f" 2>/dev/null)
  raws=$(grep -cE "environ\.get\(.AGENCY_HOME.\).*environ\.get\(.CLAUDE_CONFIG_DIR.\)" "$f" 2>/dev/null)

  if [ "$raws" -ne "$defs" ]; then
    echo "--- $f"
    echo "    $raws raw root expressions but $defs agency_root() definitions"
    echo "    (a python block here resolves the agency root without the twin)"
    twin_offenders=$((twin_offenders + 1))
    continue
  fi

  [ "$defs" -eq 0 ] && continue

  # Compared as text, not as a digest — no shasum/sha256sum dependency, and the
  # failure message can show the actual diff instead of two unequal hashes.
  this_twin=$(extract_twin "$f")
  if [ -z "$twin_text" ]; then
    twin_text="$this_twin"
    twin_ref="$f"
  elif [ "$this_twin" != "$twin_text" ]; then
    echo "--- $f"
    echo "    agency_root() differs from the copy in $twin_ref"
    diff <(extract_twin "$twin_ref") <(extract_twin "$f") || true
    twin_offenders=$((twin_offenders + 1))
  fi
done

if [ "$twin_offenders" -ne 0 ]; then
  cat <<'EOF'

FAIL: the Python root twin has drifted into per-file variants.

Copy the canonical form from hooks/lib/resolve-root.sh verbatim. One idiom,
every site — a variant that looks equivalent on macOS can still write to the
wrong directory under Git Bash, silently and with exit code 0.
EOF
  exit 1
fi

echo "OK: python root twin identical across all hooks/ and scripts/ copies"

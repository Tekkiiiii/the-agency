#!/usr/bin/env bash
# check-mods-install.sh - regression guard for the mods wiring in install.sh and
# `agency upgrade` (the engine is cli/lib/mods-merge.js; its unit test is
# check-mods-merge.js). Every case runs against a fresh temp AGENCY_HOME inside
# one mktemp -d sandbox; the real HOME and ~/.claude are never touched.
#
#   A merge-with-existing  a user plugin dir named loop-guard + a pre-existing
#                          <root>/mods/context-band: both are skipped, the other
#                          three mods are appended AFTER the user's entry, other
#                          settings keys survive, hooks/lib/*.py|json deployed
#   B idempotent           a second install leaves settings.json byte-identical
#   C uninstall            `mods-merge.js remove` restores the user's value
#                          exactly and deletes only the dirs it made
#   D version gate         Claude Code 2.1.286 -> nothing written, one skip note
#   E upgrade deploys mods a root installed with AGENCY_NO_MODS=1, then
#                          `agency upgrade` run from a scratch git clone: the
#                          5 mods are wired (this failed before the wiring)
#
# Code under test: REPO (default this checkout). To check an older revision:
#   git worktree add /tmp/old <rev>; REPO=/tmp/old bash .github/scripts/check-mods-install.sh
# AGENCY_CLAUDE_VERSION stands in for `claude --version` (CI has no claude CLI).
#
# bash 3.2-safe (macOS /bin/bash). KEEP_TMP=1 keeps the sandbox for debugging.
set -u -o pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${REPO:-$SELF_DIR/../..}" && pwd)"

W="$(mktemp -d)"
if [ -n "${KEEP_TMP:-}" ]; then
  echo "sandbox kept: $W"
else
  trap 'rm -rf "$W"' EXIT
fi

export HOME="$W/home"
mkdir -p "$HOME"
unset AGENCY_HOME CLAUDE_CONFIG_DIR AGENCY_NO_MODS AGENCY_NO_HOOKS AGENCY_CLAUDE_VERSION \
  AGENCY_UPGRADE_REEXEC AGENCY_UPGRADE_HEAD_BEFORE 2>/dev/null || true
if command -v cygpath >/dev/null 2>&1; then
  USERPROFILE="$(cygpath -w "$HOME")"; export USERPROFILE
fi
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=ci GIT_AUTHOR_EMAIL=ci@example.invalid
export GIT_COMMITTER_NAME=ci GIT_COMMITTER_EMAIL=ci@example.invalid

SEP=':'
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) SEP=';' ;; esac

FAILS=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; FAILS=$((FAILS + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }

# jget <json-file> <dotted.path> -> string value, JSON for non-strings, __undef__ if absent
jget() {
  node -e '
    const fs = require("fs");
    let v;
    try { v = JSON.parse(fs.readFileSync(process.argv[1], "utf8")); } catch (e) { process.stdout.write("__undef__"); process.exit(0); }
    for (const k of process.argv[2].split(".")) v = v == null ? undefined : v[k];
    process.stdout.write(v === undefined ? "__undef__" : typeof v === "string" ? v : JSON.stringify(v));
  ' "$1" "$2"
}
contains()  { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }
lacks()     { ! contains "$1" "$2"; }
startswith() { case "$1" in "$2"*) return 0 ;; *) return 1 ;; esac; }

# install_into <root> <claude-version> <log> [repo-dir] - run the installer under test
install_into() {
  local root="$1" ver="$2" log="$3" src="${4:-$REPO}"
  AGENCY_HOME="$root" AGENCY_CLAUDE_VERSION="$ver" bash "$src/install.sh" > "$log" 2>&1
}

echo "check-mods-install: code under test = $REPO"
if [ ! -f "$REPO/install.sh" ]; then echo "  FAIL no install.sh in $REPO"; exit 1; fi

# ── case A: merge with a user's existing entries ─────────────────────────────
echo "case A: install.sh merges into an existing CLAUDE_CODE_PLUGIN_DIRS"
H="$W/a"; mkdir -p "$H/mods/context-band"
USERDIR="$W/userplug"
mkdir -p "$USERDIR/loop-guard/.claude-plugin"
printf '{ "name": "loop-guard", "version": "9.9.9" }\n' > "$USERDIR/loop-guard/.claude-plugin/plugin.json"
USERENTRY="$USERDIR/loop-guard"
printf 'keep\n' > "$H/mods/context-band/marker.txt"
node -e 'require("fs").writeFileSync(process.argv[1], JSON.stringify({ env: { OTHER: "x", CLAUDE_CODE_PLUGIN_DIRS: process.argv[2] } }, null, 2) + "\n")' "$H/settings.json" "$USERENTRY"
install_into "$H" 2.1.293 "$W/a.log"; CODE=$?
check "install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
VAL="$(jget "$H/settings.json" env.CLAUDE_CODE_PLUGIN_DIRS)"
echo "    | CLAUDE_CODE_PLUGIN_DIRS = $VAL"
check "value starts with the user's entry" startswith "$VAL" "$USERENTRY"
check "contains $H/mods/agent-ctx"     contains "$VAL" "$H/mods/agent-ctx"
check "contains $H/mods/spawn-ledger"  contains "$VAL" "$H/mods/spawn-ledger"
check "contains $H/mods/voice-compact" contains "$VAL" "$H/mods/voice-compact"
check "joined with '$SEP'" contains "$VAL" "${SEP}$H/mods/agent-ctx"
check "loop-guard NOT added (user provides that name)" lacks "$VAL" "$H/mods/loop-guard"
check "context-band NOT added (already on disk)"       lacks "$VAL" "$H/mods/context-band"
check "pre-existing context-band/marker.txt intact" [ "$(cat "$H/mods/context-band/marker.txt" 2>/dev/null)" = keep ]
check "env.OTHER still x" [ "$(jget "$H/settings.json" env.OTHER)" = x ]
check "hooks/lib/model-pin.py deployed"        [ -f "$H/hooks/lib/model-pin.py" ]
check "hooks/lib/claude_pricing.py deployed"   [ -f "$H/hooks/lib/claude_pricing.py" ]
check "hooks/lib/exec-model-map.json deployed" [ -f "$H/hooks/lib/exec-model-map.json" ]
check "no __pycache__ under hooks/lib"         [ ! -e "$H/hooks/lib/__pycache__" ]
check "state file records mods.installed of 3" [ "$(jget "$H/hooks/.agency-hooks-state.json" mods.installed.length)" = 3 ]
check "mod dirs copied: agent-ctx spawn-ledger voice-compact" bash -c '[ -d "$1/mods/agent-ctx" ] && [ -d "$1/mods/spawn-ledger" ] && [ -d "$1/mods/voice-compact" ]' _ "$H"
check "no loop-guard copy made" [ ! -e "$H/mods/loop-guard" ]

# ── case B: idempotent ───────────────────────────────────────────────────────
echo "case B: a second install.sh leaves settings.json byte-identical"
cp "$H/settings.json" "$W/a.settings.before"
install_into "$H" 2.1.293 "$W/a2.log"; CODE=$?
check "second install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "settings.json byte-identical" cmp -s "$W/a.settings.before" "$H/settings.json"

# ── case C: uninstall ────────────────────────────────────────────────────────
echo "case C: mods-merge.js remove restores the user's value exactly"
AGENCY_CLAUDE_VERSION=2.1.293 node "$REPO/cli/lib/mods-merge.js" remove --root "$H" > "$W/c.log" 2>&1; CODE=$?
sed 's/^/    | /' "$W/c.log"
check "remove exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "value == the user's entry exactly" [ "$(jget "$H/settings.json" env.CLAUDE_CODE_PLUGIN_DIRS)" = "$USERENTRY" ]
check "owned mod dirs gone" bash -c '[ ! -e "$1/mods/agent-ctx" ] && [ ! -e "$1/mods/spawn-ledger" ] && [ ! -e "$1/mods/voice-compact" ]' _ "$H"
check "context-band/marker.txt intact" [ "$(cat "$H/mods/context-band/marker.txt" 2>/dev/null)" = keep ]
check "env.OTHER still x" [ "$(jget "$H/settings.json" env.OTHER)" = x ]

# ── case D: version gate ─────────────────────────────────────────────────────
echo "case D: Claude Code 2.1.286 -> mods not wired, one skip note"
H="$W/d"
install_into "$H" 2.1.286 "$W/d.log"; CODE=$?
check "install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "no CLAUDE_CODE_PLUGIN_DIRS key" [ "$(jget "$H/settings.json" env.CLAUDE_CODE_PLUGIN_DIRS)" = __undef__ ]
check "no <root>/mods directory" [ ! -e "$H/mods" ]
check "skip note printed" grep -qE 'Mods: skipped \(needs Claude Code 2\.1\.287\+' "$W/d.log"

# ── case E: agency upgrade deploys the mods ──────────────────────────────────
# `agency upgrade` pulls a git clone and syncs it into AGENCY_HOME, so the code
# under test goes into a scratch bare origin + clone (a copy of REPO's working
# tree, uncommitted files included), the way check-upgrade-rewrite.sh does.
echo "case E: agency upgrade wires the mods into a root installed without them"
SEED="$W/seed"; ORIGIN="$W/origin/the-agency.git"; CLONE="$W/clone"
mkdir -p "$SEED" "$W/origin"
( cd "$REPO" && tar -cf - --exclude=.git --exclude=node_modules --exclude=__pycache__ . ) | tar -xf - -C "$SEED"
git -c init.defaultBranch=main init -q "$SEED"
git -C "$SEED" checkout -q -b main 2>/dev/null || true
( cd "$SEED" && git add -A && git commit -q -m "seed: code under test" )
git init -q --bare "$ORIGIN"
git -C "$ORIGIN" symbolic-ref HEAD refs/heads/main
git -C "$SEED" remote add origin "$ORIGIN"
git -C "$SEED" push -q origin main
git clone -q "$ORIGIN" "$CLONE"
H="$W/e"
AGENCY_NO_MODS=1 install_into "$H" 2.1.293 "$W/e1.log" "$CLONE"; CODE=$?
check "install with AGENCY_NO_MODS=1 exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "baseline: no mods wired" [ "$(jget "$H/settings.json" env.CLAUDE_CODE_PLUGIN_DIRS)" = __undef__ ]
check "baseline: no <root>/mods" [ ! -e "$H/mods" ]
( cd "$W" && AGENCY_HOME="$H" AGENCY_CLAUDE_VERSION=2.1.293 node "$CLONE/cli/bin/agency.js" upgrade ) > "$W/e2.log" 2>&1; CODE=$?
sed 's/^/    | /' "$W/e2.log" | grep -E 'Mods|Restart' || true
check "agency upgrade exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
VAL="$(jget "$H/settings.json" env.CLAUDE_CODE_PLUGIN_DIRS)"
echo "    | CLAUDE_CODE_PLUGIN_DIRS = $VAL"
for m in agent-ctx context-band loop-guard spawn-ledger voice-compact; do
  check "upgrade wired $m" contains "$VAL" "$H/mods/$m"
  check "upgrade copied $m" [ -f "$H/mods/$m/.claude-plugin/plugin.json" ]
done
check "state file records mods.installed of 5" [ "$(jget "$H/hooks/.agency-hooks-state.json" mods.installed.length)" = 5 ]
check "restart reminder in the upgrade summary" grep -q 'Restart Claude Code to load the mods' "$W/e2.log"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "PASS: check-mods-install ($REPO)"
  exit 0
fi
echo "FAIL: check-mods-install - $FAILS check(s) failed ($REPO)"
exit 1

#!/usr/bin/env bash
# check-retired-install.sh - regression guard for the retired-files prune wired into
# install.sh and `agency upgrade` (the engine is cli/lib/retired-prune.js; its unit
# test is check-retired-prune.js). Every case runs against a fresh temp AGENCY_HOME
# inside one mktemp -d sandbox; the real HOME and ~/.claude are never touched.
#
# The "old install" is built by the OLD installer from the pre-sunset tree
# (OLD_REV, default 723a223: it ships the 6 dept skills, 15 dept agents and
# runbooks/protocol-registry.md that the repo has since retired) with
# AGENCY_NO_MODS=1. Then the user edits skills/dept-status/SKILL.md and adds
# skills/my-own/SKILL.md, and the CURRENT code runs with no terminal:
#
#   I  installer      REPO/install.sh into the old install
#   U  upgrade        `agency upgrade` from a scratch git clone of REPO's working
#                     tree (the way check-mods-install.sh case E does)
#   For each of I and U:
#     - unedited retired files are gone (dept-resume, engineering-lead,
#       task-executor, protocol-registry); the edited dept-status is ARCHIVED under
#       archive/agency-retired-<date>/ and not deleted; the "You changed these" note
#       and logs/agency-retired.log are written; my-own is untouched
#     - a rerun prints "Retired files: none to remove"
#     - --retired=delete on a second fresh old install deletes the edited file too
#     - --retired=bogus exits 2 and changes nothing
#
# Code under test: REPO (default this checkout). The old tree is a `git worktree`
# of REPO, so REPO needs FULL history (CI: actions/checkout with fetch-depth: 0).
# To see the checks FAIL on a revision without the wiring (the old install is still
# built from OLD_REV):
#   git worktree add /tmp/before c74d025
#   REPO=/tmp/before bash .github/scripts/check-retired-install.sh
#
# bash 3.2-safe (macOS /bin/bash). KEEP_TMP=1 keeps the sandbox for debugging.
set -u -o pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${REPO:-$SELF_DIR/../..}" && pwd)"
OLD_REV="${OLD_REV:-723a223}"

W="$(mktemp -d)"
OLD="$W/old-tree"
cleanup() {
  git -C "$REPO" worktree remove --force "$OLD" >/dev/null 2>&1 || true
  git -C "$REPO" worktree prune >/dev/null 2>&1 || true
  [ -n "${KEEP_TMP:-}" ] || rm -rf "$W"
}
trap cleanup EXIT
[ -n "${KEEP_TMP:-}" ] && echo "sandbox kept: $W"

export HOME="$W/home"
mkdir -p "$HOME"
unset AGENCY_HOME CLAUDE_CONFIG_DIR AGENCY_NO_MODS AGENCY_NO_HOOKS AGENCY_CLAUDE_VERSION AGENCY_RETIRED \
  AGENCY_UPGRADE_REEXEC AGENCY_UPGRADE_HEAD_BEFORE 2>/dev/null || true
if command -v cygpath >/dev/null 2>&1; then
  USERPROFILE="$(cygpath -w "$HOME")"; export USERPROFILE
fi
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=ci GIT_AUTHOR_EMAIL=ci@example.invalid
export GIT_COMMITTER_NAME=ci GIT_COMMITTER_EMAIL=ci@example.invalid
# The mods step depends on whether the machine has a claude CLI; this check is not about it.
export AGENCY_NO_MODS=1

FAILS=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; FAILS=$((FAILS + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
contains() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }
absent()   { [ ! -e "$1" ]; }
present()  { [ -e "$1" ]; }
# archived_file <root> <relpath> -> first archive/agency-retired-*/<relpath>, or nothing
archived_file() {
  local f
  for f in "$1"/archive/agency-retired-*/"$2"; do
    if [ -f "$f" ]; then echo "$f"; return 0; fi
  done
  return 1
}
# tree_sum <root> -> one checksum line per file, sorted (change detector)
tree_sum() { ( cd "$1" && find . -type f -exec cksum {} + | sort ); }

echo "check-retired-install: code under test = $REPO, old install = $OLD_REV"
if [ ! -f "$REPO/install.sh" ]; then echo "  FAIL no install.sh in $REPO"; exit 1; fi

# ── the pre-sunset tree ──────────────────────────────────────────────────────
if ! git -C "$REPO" cat-file -e "${OLD_REV}^{commit}" 2>/dev/null; then
  echo "  FAIL commit $OLD_REV is not in $REPO: this check needs the full git history (actions/checkout fetch-depth: 0)"
  exit 1
fi
git -C "$REPO" worktree add -q --detach "$OLD" "$OLD_REV" || { echo "  FAIL git worktree add $OLD_REV"; exit 1; }
check "old tree ships skills/dept-status and the engineering-lead agent" \
  bash -c '[ -f "$1/skills/dept-status/SKILL.md" ] && [ -f "$1/agents/engineering/engineering-lead.md" ]' _ "$OLD"

EDIT_MARK="local edit by check-retired-install"

# old_install <root> - the OLD installer builds the "old install", then the user edits
old_install() {
  local root="$1"
  AGENCY_HOME="$root" bash "$OLD/install.sh" > "$root.old.log" 2>&1 </dev/null; local code=$?
  check "old install.sh exit 0 (got $code)" [ "$code" -eq 0 ]
  mkdir -p "$root/skills/my-own"
  printf 'my own skill\n' > "$root/skills/my-own/SKILL.md"
  printf '\n%s\n' "$EDIT_MARK" >> "$root/skills/dept-status/SKILL.md"
  check "old install has the retired files + the edit" bash -c '[ -f "$1/skills/dept-resume/SKILL.md" ] && [ -f "$1/agents/engineering/engineering-lead.md" ] && [ -f "$1/agents/specialized/task-executor.md" ] && [ -f "$1/runbooks/protocol-registry.md" ] && grep -q "$2" "$1/skills/dept-status/SKILL.md"' _ "$root" "$EDIT_MARK"
}

# assert_default <root> <log> - the archive-mode outcome shared by case I and case U
assert_default() {
  local H="$1" log="$2" arch
  check "unedited skills/dept-resume deleted"                absent "$H/skills/dept-resume"
  check "unedited agents/engineering/engineering-lead.md deleted" absent "$H/agents/engineering/engineering-lead.md"
  check "unedited agents/specialized/task-executor.md deleted"    absent "$H/agents/specialized/task-executor.md"
  check "unedited runbooks/protocol-registry.md deleted"     absent "$H/runbooks/protocol-registry.md"
  check "edited skills/dept-status no longer in the live tree" absent "$H/skills/dept-status/SKILL.md"
  arch="$(archived_file "$H" skills/dept-status/SKILL.md)" || arch=""
  check "edited dept-status ARCHIVED under archive/agency-retired-<date>/ (not deleted)" bash -c '[ -n "$1" ] && grep -q "$2" "$1"' _ "$arch" "$EDIT_MARK"
  check "the 'You changed these' note was printed" grep -q 'You changed these' "$log"
  check "logs/agency-retired.log written" bash -c '[ -s "$1/logs/agency-retired.log" ] && grep -q "dept-status" "$1/logs/agency-retired.log"' _ "$H"
  check "user skill my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"
  check "a still-shipped skill is intact (skills/recall)" present "$H/skills/recall/SKILL.md"
}

# ── case I: the current install.sh prunes an old install ─────────────────────
echo "case I: install.sh removes retired files (no terminal)"
H="$W/i"
old_install "$H"
AGENCY_HOME="$H" bash "$REPO/install.sh" > "$W/i.log" 2>&1 </dev/null; CODE=$?
grep -E 'Retired|retired|You changed' "$W/i.log" | sed 's/^/    | /' || true
check "install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
assert_default "$H" "$W/i.log"
AGENCY_HOME="$H" bash "$REPO/install.sh" > "$W/i2.log" 2>&1 </dev/null; CODE=$?
check "rerun install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "rerun prints 'Retired files: none to remove'" grep -q 'Retired files: none to remove' "$W/i2.log"
check "rerun leaves my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"

echo "case I-delete: install.sh --retired=delete also deletes the edited file"
H="$W/id"
old_install "$H"
AGENCY_HOME="$H" bash "$REPO/install.sh" --retired=delete > "$W/id.log" 2>&1 </dev/null; CODE=$?
check "install.sh --retired=delete exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "edited skills/dept-status deleted" absent "$H/skills/dept-status/SKILL.md"
check "nothing archived for dept-status" bash -c '! ls "$1"/archive/agency-retired-*/skills/dept-status/SKILL.md >/dev/null 2>&1' _ "$H"
check "unedited skills/dept-resume deleted" absent "$H/skills/dept-resume"
check "user skill my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"

echo "case I-bogus: install.sh --retired=bogus exits 2 before changing anything"
H="$W/ib"
old_install "$H"
tree_sum "$H" > "$W/ib.before"
AGENCY_HOME="$H" bash "$REPO/install.sh" --retired=bogus > "$W/ib.log" 2>&1 </dev/null; CODE=$?
sed 's/^/    | /' "$W/ib.log" | head -3
check "install.sh --retired=bogus exit 2 (got $CODE)" [ "$CODE" -eq 2 ]
tree_sum "$H" > "$W/ib.after"
check "the old install is byte-for-byte unchanged" cmp -s "$W/ib.before" "$W/ib.after"
check "the message names the bad value" grep -q 'bogus' "$W/ib.log"

# ── case U: agency upgrade prunes an old install ─────────────────────────────
# `agency upgrade` pulls a git clone and syncs it into AGENCY_HOME, so the code under
# test goes into a scratch bare origin + clone (a copy of REPO's working tree,
# uncommitted files included), as in check-mods-install.sh case E.
echo "case U: agency upgrade removes retired files (no terminal)"
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

# upgrade_into <root> <log> [args...] - run `agency upgrade` from the scratch clone
upgrade_into() {
  local root="$1" log="$2"; shift 2
  ( cd "$W" && AGENCY_HOME="$root" node "$CLONE/cli/bin/agency.js" upgrade "$@" ) > "$log" 2>&1 </dev/null
}

H="$W/u"
old_install "$H"
upgrade_into "$H" "$W/u.log"; CODE=$?
grep -E 'Retired|retired|You changed' "$W/u.log" | sed 's/^/    | /' || true
check "agency upgrade exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
assert_default "$H" "$W/u.log"
upgrade_into "$H" "$W/u2.log"; CODE=$?
check "rerun agency upgrade exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "rerun prints 'Retired files: none to remove'" grep -q 'Retired files: none to remove' "$W/u2.log"
check "rerun leaves my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"

echo "case U-delete: agency upgrade --retired=delete also deletes the edited file"
H="$W/ud"
old_install "$H"
upgrade_into "$H" "$W/ud.log" --retired=delete; CODE=$?
check "agency upgrade --retired=delete exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "edited skills/dept-status deleted" absent "$H/skills/dept-status/SKILL.md"
check "nothing archived for dept-status" bash -c '! ls "$1"/archive/agency-retired-*/skills/dept-status/SKILL.md >/dev/null 2>&1' _ "$H"
check "user skill my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"

echo "case U-bogus: agency upgrade --retired=bogus exits 2 before changing anything"
H="$W/ub"
old_install "$H"
tree_sum "$H" > "$W/ub.before"
HEAD_BEFORE="$(git -C "$CLONE" rev-parse HEAD)"
upgrade_into "$H" "$W/ub.log" --retired=bogus; CODE=$?
sed 's/^/    | /' "$W/ub.log" | head -3
check "agency upgrade --retired=bogus exit 2 (got $CODE)" [ "$CODE" -eq 2 ]
tree_sum "$H" > "$W/ub.after"
check "the old install is byte-for-byte unchanged" cmp -s "$W/ub.before" "$W/ub.after"
check "the clone was not touched" [ "$(git -C "$CLONE" rev-parse HEAD)" = "$HEAD_BEFORE" ]

echo
if [ "$FAILS" -eq 0 ]; then
  echo "PASS: check-retired-install ($REPO)"
  exit 0
fi
echo "FAIL: check-retired-install - $FAILS check(s) failed ($REPO)"
exit 1

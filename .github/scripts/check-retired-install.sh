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
#   L-B legacy clone, root != repo: the old install is a git clone of REPO at OLD_REV
#       (what `git clone ... ~/.claude` made) whose origin is REPO's origin; the
#       current install.sh prunes it with NO --force and says it found a legacy
#       install; a git root with some OTHER origin is still skipped
#   L-A legacy clone that is also the CLI's repo: the same clone is AGENCY_HOME and
#       `agency upgrade` runs from it; the pull removes the tracked retired files
#       (git renames carry a user's edit to its new agents-archive path), the prune
#       then has nothing left to do and says so once (no double handling, no archive)
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

# ── legacy git installs ──────────────────────────────────────────────────────
# The old `git clone <repo> ~/.claude` (and the old rescue.sh) made the Claude root
# itself a git clone of the repo. Such a root is a normal prune target, no --force.
# A throwaway node file lists the manifest paths still on disk under a root.
cat > "$W/left.js" <<'JS'
const fs = require('fs'), p = require('path');
const m = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).paths;
const left = Object.keys(m).filter((x) => fs.existsSync(p.join(process.argv[3], ...x.split('/'))));
console.log(left.length + ' ' + left.slice(0, 5).join(','));
JS
# legacy_edit <root> - the user's edit + own skill on top of an old clone
legacy_edit() {
  mkdir -p "$1/skills/my-own"
  printf 'my own skill\n' > "$1/skills/my-own/SKILL.md"
  printf '\n%s\n' "$EDIT_MARK" >> "$1/skills/dept-status/SKILL.md"
}

echo "case L-B: install.sh prunes a legacy git clone root with no --force"
RURL="$(git -C "$REPO" remote get-url origin 2>/dev/null)" || RURL=""
if [ -z "$RURL" ]; then
  echo "  skip REPO has no origin remote, so a clone of it cannot be told apart from another git root"
else
  H="$W/lb"
  git clone -q --no-checkout "$REPO" "$H" && git -C "$H" checkout -q --detach "$OLD_REV" && git -C "$H" remote set-url origin "$RURL"
  legacy_edit "$H"
  check "the legacy root is a git clone at $OLD_REV with the retired files tracked" bash -c 'git -C "$1" ls-files --error-unmatch skills/dept-resume/SKILL.md >/dev/null 2>&1' _ "$H"
  AGENCY_HOME="$H" bash "$REPO/install.sh" > "$W/lb.log" 2>&1 </dev/null; CODE=$?
  grep -E 'Retired|retired|You changed' "$W/lb.log" | sed 's/^/    | /' || true
  check "install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "the legacy install was announced" grep -q 'Retired files: legacy git install detected' "$W/lb.log"
  check "no 'git work tree' skip" bash -c '! grep -q "is a git work tree" "$1"' _ "$W/lb.log"
  assert_default "$H" "$W/lb.log"
  AGENCY_HOME="$H" bash "$REPO/install.sh" > "$W/lb2.log" 2>&1 </dev/null; CODE=$?
  check "rerun install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "rerun leaves my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"

  echo "case L-B-other: a git root with some other origin is still skipped without --force"
  H="$W/lbo"
  git clone -q --no-checkout "$REPO" "$H" && git -C "$H" checkout -q --detach "$OLD_REV" && git -C "$H" remote set-url origin "https://example.invalid/someone/dotfiles.git"
  legacy_edit "$H"
  AGENCY_HOME="$H" bash "$REPO/install.sh" > "$W/lbo.log" 2>&1 </dev/null; CODE=$?
  check "install.sh exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "skipped as a git work tree" grep -q 'is a git work tree; run: agency prune --force' "$W/lbo.log"
  check "the retired file is still there" present "$H/skills/dept-resume/SKILL.md"
  check "no legacy announcement" bash -c '! grep -q "legacy git install" "$1"' _ "$W/lbo.log"
fi

echo "case L-A: agency upgrade run from the legacy clone that IS the root"
# OLD_REV history + the code under test (REPO's working tree) as one new commit, in a
# bare origin. The root is a clone of it reset to OLD_REV, so `agency upgrade`
# pulls the retired-file removal exactly as a legacy user's upgrade would.
LASEED="$W/la-seed"; LAORIGIN="$W/origin/la.git"; H="$W/la"
git clone -q --no-checkout "$REPO" "$LASEED"
git -C "$LASEED" checkout -q -b la-main "$OLD_REV"
find "$LASEED" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
( cd "$SEED" && tar -cf - --exclude=.git . ) | tar -xf - -C "$LASEED"
( cd "$LASEED" && git add -A && git commit -q -m "seed: code under test" )
git init -q --bare "$LAORIGIN"
git -C "$LAORIGIN" symbolic-ref HEAD refs/heads/main
git -C "$LASEED" push -q "$LAORIGIN" la-main:main
git clone -q "$LAORIGIN" "$H"
git -C "$H" reset -q --hard "$OLD_REV"
legacy_edit "$H"
check "the root is a clone at $OLD_REV with the edit pending" bash -c '[ "$(git -C "$1" rev-parse --short HEAD)" = "$2" ] && ! git -C "$1" diff --quiet -- skills/dept-status/SKILL.md' _ "$H" "$OLD_REV"
( cd "$W" && AGENCY_HOME="$H" node "$H/cli/bin/agency.js" upgrade ) > "$W/la.log" 2>&1 </dev/null; CODE=$?
grep -E 'Retired|retired|You changed|Upgrade' "$W/la.log" | sed 's/^/    | /' | head -8 || true
check "agency upgrade exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "no retired manifest path left on disk (tracked or untracked): $(node "$W/left.js" "$H/retired-manifest.json" "$H")" bash -c '[ "$(node "$1" "$2/retired-manifest.json" "$2" | cut -d" " -f1)" = "0" ]' _ "$W/left.js" "$H"
check "the pull removed the tracked retired files" bash -c '[ ! -e "$1/skills/dept-resume" ] && [ ! -e "$1/agents/engineering/engineering-lead.md" ]' _ "$H"
check "the edited retired file survives at its renamed agents-archive path (no data loss)" bash -c 'grep -rl "$2" "$1/agents-archive" >/dev/null 2>&1' _ "$H" "$EDIT_MARK"
check "nothing was archived for files git removed" absent "$H/archive"
check "exactly one summary line, 'none to remove' (no double count)" bash -c '[ "$(grep -c "^Retired files:" "$1")" = "1" ] && grep -q "^Retired files: none to remove" "$1"' _ "$W/la.log"
check "the root was not skipped as the repo checkout" bash -c '! grep -q "agency repo checkout itself" "$1"' _ "$W/la.log"
check "user skill my-own untouched" bash -c '[ "$(cat "$1/skills/my-own/SKILL.md" 2>/dev/null)" = "my own skill" ]' _ "$H"
check "a still-shipped skill is intact (skills/recall)" present "$H/skills/recall/SKILL.md"
( cd "$W" && AGENCY_HOME="$H" node "$H/cli/bin/agency.js" upgrade ) > "$W/la2.log" 2>&1 </dev/null; CODE=$?
check "rerun agency upgrade exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "rerun prints 'Retired files: none to remove'" grep -q 'Retired files: none to remove' "$W/la2.log"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "PASS: check-retired-install ($REPO)"
  exit 0
fi
echo "FAIL: check-retired-install - $FAILS check(s) failed ($REPO)"
exit 1

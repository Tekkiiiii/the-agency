#!/usr/bin/env bash
# check-upgrade-rewrite.sh — regression guard for `agency upgrade` and rescue.sh
# on a clone whose origin/main was force-push-rewritten, while the clone also
# carries a stale .git/index.lock and a leftover unmerged (UU) file. It also
# covers rescue.sh's first-install (repo-not-found) path: the clone goes to
# ~/the-agency, never into an existing agency root (cases 8-9).
#
# That is the exact state of a real Windows clone after the 2026-10-08
# Pinecone-key history purge: `pull --rebase` replayed the pre-rewrite commits
# onto their rewritten twins and conflicted, `git stash` refused to run over the
# UU file, and the lock blocked every index write. The old rescue scripts then
# fell back to `git reset --hard` and silently dropped local work.
#
# Everything runs inside one mktemp -d sandbox: HOME, AGENCY_HOME, the bare
# origin and every clone. The code under test (cli/, CHANGELOG.md, rescue.sh) is
# COPIED from $CLI_SRC, default this checkout. To check an older revision
# without touching the live tree:
#   d=$(mktemp -d); git archive <rev> cli CHANGELOG.md rescue.sh | tar -x -C "$d"
#   CLI_SRC="$d" bash .github/scripts/check-upgrade-rewrite.sh
#
# bash 3.2-safe (macOS /bin/bash). KEEP_TMP=1 keeps the sandbox for debugging.
set -u -o pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
CLI_SRC="$(cd "${CLI_SRC:-$REPO_ROOT}" && pwd)"

W="$(mktemp -d)"
if [ -n "${KEEP_TMP:-}" ]; then
  echo "sandbox kept: $W"
else
  trap 'rm -rf "$W"' EXIT
fi

# Never let the code under test see the real home: upgrade.js re-links
# ~/.local/bin/agency and writes ~/.agency/backups.
export HOME="$W/home"
export AGENCY_HOME="$W/agency-home"
unset CLAUDE_CONFIG_DIR AGENCY_UPGRADE_REEXEC AGENCY_UPGRADE_HEAD_BEFORE 2>/dev/null || true
# This check is about git recovery, not mods: the mods step depends on whether the machine
# has a claude CLI (2.1.287+), so switch it off to keep the result machine-independent.
export AGENCY_NO_MODS=1
mkdir -p "$HOME" "$AGENCY_HOME"
# node's os.homedir() reads USERPROFILE on Windows, not HOME.
if command -v cygpath >/dev/null 2>&1; then
  USERPROFILE="$(cygpath -w "$HOME")"; export USERPROFILE
fi
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=ci GIT_AUTHOR_EMAIL=ci@example.invalid
export GIT_COMMITTER_NAME=ci GIT_COMMITTER_EMAIL=ci@example.invalid

FAILS=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; FAILS=$((FAILS + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
has()   { printf '%s\n' "$OUT" | grep -qE "$1"; }
hasnt() { ! printf '%s\n' "$OUT" | grep -qE "$1"; }
show()  { printf '%s\n' "$OUT" | sed 's/^/    | /'; }

commit_at() { # dir iso-date subject
  ( cd "$1" && git add -A && GIT_AUTHOR_DATE="$2" GIT_COMMITTER_DATE="$2" git commit -q -m "$3" )
}

# ── origin + seed history ────────────────────────────────────────────────────
# The origin path carries "Tekkiiiii/the-agency" so rescue.sh's remote-URL
# check accepts the clones.
ORIGIN="$W/Tekkiiiii/the-agency.git"
mkdir -p "$W/Tekkiiiii"
git init -q --bare "$ORIGIN"
git -C "$ORIGIN" symbolic-ref HEAD refs/heads/main

SEED="$W/seed"
git -c init.defaultBranch=main init -q "$SEED"
git -C "$SEED" checkout -q -b main 2>/dev/null || true
cp -R "$CLI_SRC/cli" "$SEED/cli"
rm -rf "$SEED/cli/node_modules"
cp "$CLI_SRC/CHANGELOG.md" "$SEED/"
[ -f "$CLI_SRC/rescue.sh" ] && cp "$CLI_SRC/rescue.sh" "$SEED/"
printf 'base\n' > "$SEED/notes.md"
commit_at "$SEED" 2026-10-01T10:00:00+07:00 "base: code under test"
printf 'b\n' > "$SEED/b.txt"
commit_at "$SEED" 2026-10-02T10:00:00+07:00 "feat: b"
printf 'KEY=leaked\n' > "$SEED/config.txt"
commit_at "$SEED" 2026-10-03T10:00:00+07:00 "chore: add config"
git -C "$SEED" remote add origin "$ORIGIN"
git -C "$SEED" push -q origin main
OLD_SECRET="$(git -C "$SEED" rev-parse HEAD)"

# Clones made BEFORE the rewrite, each with one genuine local commit on top.
make_clone() {
  local c="$W/$1"
  git clone -q "$ORIGIN" "$c"
  printf 'mine\n' > "$c/local.txt"
  commit_at "$c" 2026-10-04T10:00:00+07:00 "feat: my genuine local work"
}
make_clone up; make_clone fresh; make_clone rescue; make_clone upstashfail; make_clone rescuestashfail

# ── the rewrite: same author date + subject, different content, force-pushed ─
git -C "$SEED" reset -q --hard HEAD~1
printf 'KEY=REDACTED\n' > "$SEED/config.txt"
commit_at "$SEED" 2026-10-03T10:00:00+07:00 "chore: add config"
printf 'post\n' > "$SEED/post.txt"
commit_at "$SEED" 2026-10-08T10:00:00+07:00 "chore: re-pin after purge"
git -C "$SEED" push -q -f origin main
NEW_MAIN="$(git -C "$ORIGIN" rev-parse main)"

# A real UU entry (stages 1/2/3) with conflict markers in the working tree, an
# untracked file that must ride along, and a lock file of the given age.
plant_mess() { # clone lock-mode(stale|fresh)
  local c="$1" b1 b2 b3
  printf 'scratch\n' > "$c/untracked-mine.txt"
  b1=$(printf 'base\n'   | git -C "$c" hash-object -w --stdin)
  b2=$(printf 'ours\n'   | git -C "$c" hash-object -w --stdin)
  b3=$(printf 'theirs\n' | git -C "$c" hash-object -w --stdin)
  printf '0 %s\tnotes.md\n100644 %s 1\tnotes.md\n100644 %s 2\tnotes.md\n100644 %s 3\tnotes.md\n' \
    0000000000000000000000000000000000000000 "$b1" "$b2" "$b3" | git -C "$c" update-index --index-info
  printf '<<<<<<< Updated upstream\nours\n=======\ntheirs\n>>>>>>> Stashed changes\n' > "$c/notes.md"
  : > "$c/.git/index.lock"
  if [ "$2" = stale ]; then touch -t 202001010000 "$c/.git/index.lock"; fi
}

# Make `git stash` fail at the "store" step (before it touches the working
# tree): refs/stash cannot be created while a ref refs/stash/<x> exists (a
# directory/file conflict). An empty directory is not enough; git prunes it.
break_stash() { git -C "$1" update-ref refs/stash/blocked HEAD; }
backup_has_untracked() { [ -f "$(ls -d "$HOME"/.agency/backups/*/ 2>/dev/null | head -1)untracked-mine.txt" ]; }

backup_branch_at() { # clone sha
  git -C "$1" for-each-ref --format='%(objectname)' 'refs/heads/agency-backup/' | grep -qx "$2"
}
no_backup_branch() { [ -z "$(git -C "$1" for-each-ref 'refs/heads/agency-backup/')" ]; }
backup_has_notes() { grep -qx ours "$HOME"/.agency/backups/*/notes.md 2>/dev/null; }
no_unmerged() { [ -z "$(git -C "$1" diff --name-only --diff-filter=U)" ]; }

# ── case 1: agency upgrade on the rewritten clone ────────────────────────────
echo "case 1: agency upgrade — rewritten origin + stale index.lock + UU file"
UP="$W/up"
plant_mess "$UP" stale
OLD_HEAD="$(git -C "$UP" rev-parse HEAD)"
OUT="$(cd "$W" && node "$UP/cli/bin/agency.js" upgrade 2>&1)"; CODE=$?
show
check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "backup branch agency-backup/* at the old HEAD" backup_branch_at "$UP" "$OLD_HEAD"
check "HEAD == rewritten origin/main" [ "$(git -C "$UP" rev-parse HEAD)" = "$NEW_MAIN" ]
check "genuine local commit offered as 'git cherry-pick <sha>'" has "git cherry-pick $OLD_HEAD"
check "rewritten commit NOT offered for cherry-pick" hasnt "git cherry-pick $OLD_SECRET"
check "purged content not re-introduced" grep -qx 'KEY=REDACTED' "$UP/config.txt"
check "unmerged file copied to ~/.agency/backups/<ts>/" backup_has_notes
check "unmerged file content kept in the working tree" grep -qx ours "$UP/notes.md"
check "no unmerged entries left" no_unmerged "$UP"
check "untracked file rode along in the stash" [ -f "$UP/untracked-mine.txt" ]
check "stale index.lock removed" [ ! -e "$UP/.git/index.lock" ]
check "stale-lock notice printed" has "[Ss]tale .*index\.lock|index\.lock.*[Ss]tale"
check "sync root + source printed" has "Sync root: .*\(from AGENCY_HOME\)"

# ── case 2: a FRESH lock may be a live git process — stop, touch nothing ─────
echo "case 2: agency upgrade — fresh index.lock"
FR="$W/fresh"
: > "$FR/.git/index.lock"
FR_HEAD="$(git -C "$FR" rev-parse HEAD)"
OUT="$(cd "$W" && node "$FR/cli/bin/agency.js" upgrade 2>&1)"; CODE=$?
show
check "non-zero exit (got $CODE)" [ "$CODE" -ne 0 ]
check "prints the exact removal command" has "(^|[[:space:]])(rm|del|Remove-Item)[[:space:]].*index\.lock"
check "HEAD untouched" [ "$(git -C "$FR" rev-parse HEAD)" = "$FR_HEAD" ]
check "lock left in place" [ -e "$FR/.git/index.lock" ]
check "no backup branch created" no_backup_branch "$FR"
rm -f "$FR/.git/index.lock"

# ── case 3: rescue.sh on the same mess ───────────────────────────────────────
RS="$W/rescue"
if [ -f "$RS/rescue.sh" ]; then
  echo "case 3: rescue.sh — rewritten origin + stale index.lock + UU file"
  rm -rf "$HOME/.agency"
  plant_mess "$RS" stale
  # While origin/main's reflog still remembers the pre-rewrite tip, `pull
  # --rebase` uses it as the fork point and skips the pre-rewrite commit, so the
  # pull succeeds and no reset happens. Without that reflog (expired, or a clone
  # whose tracking ref never held the old tip) the rebase replays the old commit
  # onto its rewritten twin and conflicts, as on the real clone. Force that.
  git -C "$RS" config core.logAllRefUpdates false
  git -C "$RS" reflog expire --expire=now --all
  RS_HEAD="$(git -C "$RS" rev-parse HEAD)"
  OUT="$(cd "$RS" && bash "$RS/rescue.sh" 2>&1)"; CODE=$?
  show
  check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "backup branch agency-backup/* at the old HEAD" backup_branch_at "$RS" "$RS_HEAD"
  check "HEAD == rewritten origin/main" [ "$(git -C "$RS" rev-parse HEAD)" = "$NEW_MAIN" ]
  check "unmerged file copied to ~/.agency/backups/<ts>/" backup_has_notes
  check "unmerged file content kept in the working tree" grep -qx ours "$RS/notes.md"
  check "untracked file restored" [ -f "$RS/untracked-mine.txt" ]
  check "stale index.lock removed" [ ! -e "$RS/.git/index.lock" ]
else
  echo "case 3: skipped (no rescue.sh in $CLI_SRC)"
fi

# ── case 4: upgrade on a rewrite where `git stash` itself fails ──────────────
# The reset --hard must not run over changes that are not backed up anywhere.
echo "case 4: agency upgrade — rewritten origin, git stash fails"
rm -rf "$HOME/.agency"
US="$W/upstashfail"
plant_mess "$US" stale
break_stash "$US"
US_HEAD="$(git -C "$US" rev-parse HEAD)"
OUT="$(cd "$W" && node "$US/cli/bin/agency.js" upgrade 2>&1)"; CODE=$?
show
check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
check "backup branch agency-backup/* at the old HEAD" backup_branch_at "$US" "$US_HEAD"
check "HEAD == rewritten origin/main" [ "$(git -C "$US" rev-parse HEAD)" = "$NEW_MAIN" ]
check "uncommitted content copied to ~/.agency/backups/<ts>/" backup_has_notes
check "untracked file copied to ~/.agency/backups/<ts>/" backup_has_untracked
check "copy location printed" has "Copied your uncommitted changes to: .*\.agency"

# ── case 5: rescue.sh where `git stash` fails — the old silent-loss path ─────
RF="$W/rescuestashfail"
if [ -f "$RF/rescue.sh" ]; then
  echo "case 5: rescue.sh — git stash fails, falls back to reset --hard"
  rm -rf "$HOME/.agency"
  plant_mess "$RF" stale
  break_stash "$RF"
  RF_HEAD="$(git -C "$RF" rev-parse HEAD)"
  OUT="$(cd "$RF" && bash "$RF/rescue.sh" 2>&1)"; CODE=$?
  show
  check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "uncommitted content copied to ~/.agency/backups/<ts>/" backup_has_notes
  check "untracked file copied to ~/.agency/backups/<ts>/" backup_has_untracked
  check "backup folder printed" has "Backed up your local changes to: .*\.agency"
  check "backup branch agency-backup/* at the old HEAD" backup_branch_at "$RF" "$RF_HEAD"
  check "HEAD == rewritten origin/main" [ "$(git -C "$RF" rev-parse HEAD)" = "$NEW_MAIN" ]
else
  echo "case 5: skipped (no rescue.sh in $CLI_SRC)"
fi

# ── cases 8-9: rescue.sh first install (repo not found anywhere) ─────────────
# The agency root already exists for every Claude Code user (~/.claude holds
# settings.json etc.), so rescue.sh must clone to ~/the-agency (same as
# rescue.ps1 and the README) and leave the root to the installer — it used to
# merge the repo and its .git INTO the root. The hardcoded GitHub URL is
# redirected to the sandbox origin with a git url rewrite, so rescue.sh itself
# needs no test hook; HOME is the sandbox, so this writes $W/home/.gitconfig.
hasf() { printf '%s\n' "$OUT" | grep -qF -- "$1"; }
root_listing() { ls -A "$1" 2>/dev/null | tr '\n' ' '; }
fresh_first_install() { # root-dir — only settings.json in the root, nothing else anywhere
  rm -rf "$HOME/the-agency" "$HOME/.claude" "$HOME/.agency/the-agency" "$1"
  mkdir -p "$1"
  printf '{}\n' > "$1/settings.json"
}
if [ -f "$CLI_SRC/rescue.sh" ]; then
  git config --global url."$ORIGIN".insteadOf https://github.com/Tekkiiiii/the-agency.git

  echo "case 8: rescue.sh first install — root already exists (a Claude Code user)"
  CC="$W/cc-root"
  fresh_first_install "$CC"
  OUT="$(cd "$HOME" && AGENCY_HOME="$CC" bash "$CLI_SRC/rescue.sh" 2>&1)"; CODE=$?
  show
  check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "cloned to ~/the-agency" [ -d "$HOME/the-agency/.git" ]
  check "clone HEAD == origin/main" [ "$(git -C "$HOME/the-agency" rev-parse HEAD 2>/dev/null)" = "$NEW_MAIN" ]
  check "no .git merged into the root" [ ! -e "$CC/.git" ]
  check "root holds only its pre-existing file" [ "$(root_listing "$CC")" = "settings.json " ]
  check "root's pre-existing file untouched" [ "$(cat "$CC/settings.json")" = "{}" ]
  check "clone path printed" hasf "$HOME/the-agency"
  check "next step ./install.sh printed" hasf "install.sh"
  check "says the installer syncs into the root" hasf "syncs into $CC"

  echo "case 9: rescue.sh first install — ~/the-agency exists, non-empty, not the repo"
  fresh_first_install "$CC"
  mkdir -p "$HOME/the-agency"
  printf 'mine\n' > "$HOME/the-agency/mine.txt"
  OUT="$(cd "$HOME" && AGENCY_HOME="$CC" bash "$CLI_SRC/rescue.sh" 2>&1)"; CODE=$?
  show
  check "non-zero exit (got $CODE)" [ "$CODE" -ne 0 ]
  check "user file untouched" [ "$(cat "$HOME/the-agency/mine.txt" 2>/dev/null)" = "mine" ]
  check "~/the-agency left as it was (no .git, only mine.txt)" \
    sh -c '[ ! -e "$1/.git" ] && [ "$(ls -A "$1" | tr "\n" " ")" = "mine.txt " ]' _ "$HOME/the-agency"
  check "nothing written to the root" [ "$(root_listing "$CC")" = "settings.json " ]
  check "names the blocking directory" hasf "$HOME/the-agency"
  check "prints the manual git clone command" hasf "git clone"

  rm -rf "$HOME/the-agency" "$CC"
  git config --global --unset-all url."$ORIGIN".insteadOf
else
  echo "cases 8-9: skipped (no rescue.sh in $CLI_SRC)"
fi

# ── cases 6-7: the ordinary paths must be unchanged ──────────────────────────
# A clone one commit behind (fast-forward), and one with genuine local work on
# top of a non-rewritten base (diverged, no twins): both keep `pull --rebase`.
for kind in ff genuine; do
  echo "case $([ "$kind" = ff ] && echo 6 || echo 7): agency upgrade — $kind (no rewrite)"
  rm -rf "$HOME/.agency"
  C="$W/$kind"
  git clone -q "$ORIGIN" "$C"
  git -C "$C" reset -q --hard HEAD~1
  if [ "$kind" = genuine ]; then
    printf 'mine\n' > "$C/local.txt"
    commit_at "$C" 2026-10-09T10:00:00+07:00 "feat: work on the current history"
  fi
  OUT="$(cd "$W" && node "$C/cli/bin/agency.js" upgrade 2>&1)"; CODE=$?
  check "exit 0 (got $CODE)" [ "$CODE" -eq 0 ]
  check "no backup branch" no_backup_branch "$C"
  check "no backup folder" [ ! -d "$HOME/.agency/backups" ]
  check "no rewrite reported" hasnt "history was rewritten"
  if [ "$kind" = ff ]; then
    check "HEAD == origin/main" [ "$(git -C "$C" rev-parse HEAD)" = "$NEW_MAIN" ]
  else
    check "local commit rebased onto origin/main" [ "$(git -C "$C" rev-parse HEAD~1)" = "$NEW_MAIN" ]
  fi
  [ "$FAILS" -eq 0 ] || show
done

echo ""
if [ "$FAILS" -eq 0 ]; then
  echo "PASS: check-upgrade-rewrite"
else
  echo "FAIL: check-upgrade-rewrite — $FAILS assertion(s) failed"
  exit 1
fi

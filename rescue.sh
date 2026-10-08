#!/usr/bin/env bash
set -euo pipefail

# The Agency — Rescue Script
# Safely pulls the latest code when `agency upgrade` is broken.
# Pure bash + git. Zero Node dependency.
# Works from inside the repo, from anywhere via curl | bash, or as a first-time clone
# (to ~/the-agency, never into the agency root; the installer syncs into the root).

AGENCY_REPO="https://github.com/Tekkiiiii/the-agency.git"

# Root precedence must match hooks/lib/resolve-root.sh exactly:
#   $AGENCY_HOME -> $CLAUDE_CONFIG_DIR -> $HOME/.claude
#
# Inlined rather than sourced, deliberately, and for a reason specific to this
# script: rescue.sh is meant to run as `curl ... | bash`, where there is no
# script directory to resolve a sibling from — ${BASH_SOURCE[0]} is not a path
# at all. install.sh makes the same inline mirror on its line 9;
# hooks/lib/resolve-root.sh remains the place the precedence is DEFINED.
#
# Before this existed, rescue.sh addressed $HOME/.claude unconditionally: a user
# who installed with AGENCY_HOME=/opt/agency and then ran the rescue got a
# SECOND clone in a directory their install does not read from, and was told it
# had been rescued.
AGENCY_ROOT="${AGENCY_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"

echo ""
echo "The Agency — Rescue"
echo "==================="
echo ""
if [ -n "${AGENCY_HOME:-}" ]; then
    echo "  Agency root: $AGENCY_ROOT (from AGENCY_HOME)"
    echo ""
elif [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    echo "  Agency root: $AGENCY_ROOT (from CLAUDE_CONFIG_DIR)"
    echo ""
fi

is_agency_repo() {
    local dir="$1"
    [ -d "$dir/.git" ] || return 1
    local url
    url="$(git -C "$dir" remote get-url origin 2>/dev/null || true)"
    [[ "$url" == *"Tekkiiiii/the-agency"* ]] || [[ "$url" == *"the-agency/the-agency"* ]]
}

# ─── Backups before anything destructive ─────────────────────────────────────
# Every `git reset --hard` below used to run unguarded: when the stash failed it
# silently deleted local changes, and on a force-pushed (rewritten) origin it
# silently dropped local COMMITS. Now nothing is reset until (a) every changed
# or untracked file is copied to ~/.agency/backups/<ts>/ (outside the repo,
# relative paths kept) and (b) a HEAD that origin/main does not contain is kept
# on a branch agency-backup/<ts>. If the copy fails, nothing is reset.
BACKUP_TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=""       # created lazily, only when there is something to copy
BACKUP_BRANCH=""

ensure_backup_dir() {
    [ -n "$BACKUP_DIR" ] && return 0
    local base="$HOME/.agency/backups" d n=2
    d="$base/$BACKUP_TS"
    while [ -e "$d" ]; do d="$base/$BACKUP_TS-$n"; n=$((n + 1)); done
    mkdir -p "$d" || return 1
    BACKUP_DIR="$d"
}

# copy_to_backup <repo-relative path> — a path that no longer exists (a
# deletion) has nothing to copy and is skipped.
copy_to_backup() {
    local rel="$1"
    [ -e "$rel" ] || [ -L "$rel" ] || return 0
    ensure_backup_dir || return 1
    mkdir -p "$BACKUP_DIR/$(dirname "$rel")" || return 1
    cp -pR "$rel" "$BACKUP_DIR/$rel"
}

# Copies every changed/staged/untracked file. -z output is unquoted, and a
# rename/copy entry is "XY new<NUL>old<NUL>": keep the new path, skip the old.
backup_worktree() {
    local list entry skip=0 rc=0
    list="$(mktemp)" || return 1
    if ! git status --porcelain=v1 -z --untracked-files=all > "$list" 2>/dev/null; then
        rm -f "$list"; return 1
    fi
    while IFS= read -r -d '' entry; do
        if [ "$skip" = 1 ]; then skip=0; continue; fi
        case "$entry" in R*|C*) skip=1 ;; esac
        copy_to_backup "${entry:3}" || rc=1
    done < "$list"
    rm -f "$list"
    return $rc
}

make_backup_branch() {
    local sha="$1" name n=2
    [ -n "$BACKUP_BRANCH" ] && return 0
    name="agency-backup/$BACKUP_TS"
    while git show-ref --verify --quiet "refs/heads/$name"; do
        name="agency-backup/$BACKUP_TS-$n"; n=$((n + 1))
    done
    git branch "$name" "$sha" || return 1
    BACKUP_BRANCH="$name"
    echo "  Backup branch: $name (your old HEAD $sha)"
    echo "  To recover a commit from it: git log $name, then git cherry-pick <sha>"
}

# Call immediately before EVERY `git reset --hard`. Exits instead of returning
# when anything could not be backed up.
backup_before_reset() {
    local head
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        if ! backup_worktree; then
            echo "  Error: could not back up your local changes. NOT resetting."
            [ -n "$BACKUP_DIR" ] && echo "  Partial copy: $BACKUP_DIR"
            exit 1
        fi
        [ -n "$BACKUP_DIR" ] && echo "  Backed up your local changes to: $BACKUP_DIR"
    fi
    head="$(git rev-parse -q --verify HEAD 2>/dev/null || true)"
    if [ -n "$head" ] && ! git merge-base --is-ancestor "$head" origin/main 2>/dev/null; then
        if ! make_backup_branch "$head"; then
            echo "  Error: could not create a backup branch for your local commits. NOT resetting."
            exit 1
        fi
    fi
}

# Unmerged (UU) paths, NUL-separated, into the file named by $1.
list_unmerged() {
    git diff --name-only -z --diff-filter=U > "$1" 2>/dev/null
}

# 1. Find the-agency repo (verify by remote URL, not just any git repo)
REPO_DIR=""

# a) Check if we're already inside the-agency repo
CANDIDATE="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$CANDIDATE" ] && is_agency_repo "$CANDIDATE"; then
    REPO_DIR="$CANDIDATE"
fi

# b) Check common install locations, resolved root FIRST.
#    The remaining three are legacy/alternate layouts kept as a courtesy: this
#    is a rescue tool, and finding an existing verified repo is always better
#    than cloning a duplicate. They are only ever ADOPTED, never written to as
#    a root. Everything after this point writes only inside the repo found
#    here; a first-time clone (block c) goes to ~/the-agency, never into
#    $AGENCY_ROOT.
if [ -z "$REPO_DIR" ]; then
    for loc in "$AGENCY_ROOT" "$HOME/.claude" "$HOME/the-agency" "$HOME/.agency/the-agency"; do
        if [ -d "$loc" ] && is_agency_repo "$loc"; then
            REPO_DIR="$loc"
            break
        fi
    done
fi

# c) Not found — clone it to ~/the-agency, NEVER into $AGENCY_ROOT.
#    The root (~/.claude by default) already exists for every Claude Code user,
#    so cloning "into" it meant merging the repo and its .git over a live config
#    folder. The documented install is: clone somewhere else, then run the
#    installer, which syncs into the root (rescue.ps1 and the README say the
#    same: ~/the-agency). Nothing below writes to $AGENCY_ROOT.
if [ -z "$REPO_DIR" ]; then
    CLONE_TARGET="$HOME/the-agency"

    # git clone accepts a missing or EMPTY directory. Anything else here is not
    # ours (discovery above already adopted it if it were the repo): leave it be.
    if [ -e "$CLONE_TARGET" ] && { [ ! -d "$CLONE_TARGET" ] || [ -n "$(ls -A "$CLONE_TARGET" 2>/dev/null)" ]; }; then
        echo "  The Agency repo not found locally."
        echo "  Error: $CLONE_TARGET already exists and is not the-agency repo. Not touching it."
        echo "  Clone the repo into a different folder, then run the installer from there:"
        echo "    git clone $AGENCY_REPO <other-dir>"
        echo "    cd <other-dir> && ./install.sh"
        exit 1
    fi

    echo "  The Agency repo not found locally. Cloning to $CLONE_TARGET/ ..."
    if git clone "$AGENCY_REPO" "$CLONE_TARGET" 2>&1; then
        REPO_DIR="$CLONE_TARGET"
        echo "  Cloned to $REPO_DIR"
    else
        echo "  Error: git clone failed. Check your network connection."
        exit 1
    fi

    echo ""
    echo "  First-time install — run the installer next. It syncs into $AGENCY_ROOT:"
    echo "    cd \"$REPO_DIR\" && ./install.sh"
    echo ""
    exit 0
fi

echo "  Repo: $REPO_DIR"
cd "$REPO_DIR"

# 2a. A stale .git/index.lock (crashed git process) blocks every index write.
#     Older than 10 minutes: remove it. Younger: it may belong to a live git
#     process or an editor — stop and say exactly how to remove it.
if [ -e ".git/index.lock" ]; then
    if [ -n "$(find .git/index.lock -mmin +10 2>/dev/null)" ]; then
        rm -f .git/index.lock
        echo "  Removed stale $REPO_DIR/.git/index.lock (older than 10 minutes, left by a crashed git process)."
    else
        echo "  Error: $REPO_DIR/.git/index.lock exists and is less than 10 minutes old."
        echo "  Another git process (or an editor) may still be running. If none is, remove it and re-run:"
        echo "    rm \"$REPO_DIR/.git/index.lock\""
        exit 1
    fi
fi

# 2b. Files left unmerged by an earlier conflict: copy them out first (an
#     in-progress merge abort below would otherwise discard their content).
UNMERGED_LIST="$(mktemp)"
list_unmerged "$UNMERGED_LIST" || true
if [ -s "$UNMERGED_LIST" ]; then
    echo "  Found files left unmerged by an earlier conflict:"
    while IFS= read -r -d '' p; do
        echo "    $p"
        if ! copy_to_backup "$p"; then
            echo "  Error: could not back up $p. Stopping without changes."
            rm -f "$UNMERGED_LIST"
            exit 1
        fi
    done < "$UNMERGED_LIST"
    echo "  Backup copy: $BACKUP_DIR"
fi

# 2c. Detect and clean up in-progress rebase/merge
if [ -f ".git/REBASE_HEAD" ] || [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    echo "  Detected rebase in progress — aborting it..."
    git rebase --abort 2>/dev/null || true
    echo "  Done."
fi

if [ -f ".git/MERGE_HEAD" ]; then
    echo "  Detected merge in progress — aborting it..."
    git merge --abort 2>/dev/null || true
    echo "  Done."
fi

if [ -f ".git/CHERRY_PICK_HEAD" ]; then
    echo "  Detected cherry-pick in progress — aborting it..."
    git cherry-pick --abort 2>/dev/null || true
    echo "  Done."
fi

# 2d. Unmerged paths still left (no operation in progress, e.g. a conflicted
#     stash pop): clear the conflict state but KEEP the working-tree content,
#     so `git stash` can run and the content rides along in it.
list_unmerged "$UNMERGED_LIST" || true
if [ -s "$UNMERGED_LIST" ]; then
    while IFS= read -r -d '' p; do
        GIT_LITERAL_PATHSPECS=1 git reset -q -- "$p" 2>/dev/null || true
    done < "$UNMERGED_LIST"
    list_unmerged "$UNMERGED_LIST" || true
    if [ -s "$UNMERGED_LIST" ]; then
        rm -f "$UNMERGED_LIST"
        echo "  Error: could not clear the unmerged state. Check: git status"
        exit 1
    fi
    echo "  Cleared the conflict state (content kept in your working tree)."
fi
rm -f "$UNMERGED_LIST"

# 3. Fetch latest
echo ""
echo "  Fetching origin/main..."
if ! git fetch origin main 2>&1; then
    echo ""
    echo "  Error: git fetch failed. Check your network connection."
    exit 1
fi

# 4. Stash local changes
STASHED=false
DIRTY="$(git status --porcelain 2>/dev/null || true)"
if [ -n "$DIRTY" ]; then
    echo "  Stashing local changes..."
    if git stash --include-untracked 2>&1; then
        STASHED=true
        echo "  Stashed successfully."
    else
        echo ""
        echo "  Warning: git stash failed. Trying hard reset to origin/main instead."
        backup_before_reset
        echo "  Your local changes will be removed from the working tree (the copies above stay)."
        echo "  Press Ctrl+C within 5 seconds to cancel."
        sleep 5
        git reset --hard origin/main
        echo "  Reset complete."
        STASHED=false
    fi
fi

# 5. Pull latest
echo ""
echo "  Pulling latest from origin/main..."
if git pull --rebase origin main 2>&1; then
    echo "  Pull successful."
else
    echo ""
    echo "  Pull failed. Forcing reset to origin/main..."
    git rebase --abort 2>/dev/null || true
    backup_before_reset
    git reset --hard origin/main
    echo "  Reset to origin/main."
fi

# 6. Restore stashed changes
if [ "$STASHED" = true ]; then
    echo ""
    echo "  Restoring your local changes..."
    if git stash pop 2>&1; then
        echo "  Restored successfully."
    else
        echo ""
        echo "  Stash pop had conflicts. Your changes are safe in the stash."
        echo "  To see them:   git stash show -p"
        echo "  To drop them:  git stash drop"
        echo "  To retry:      git checkout -- . && git stash pop"
    fi
fi

# 7. Show what changed
echo ""
CHANGES="$(git log ORIG_HEAD..HEAD --oneline 2>/dev/null || true)"
if [ -n "$CHANGES" ]; then
    echo "  Updated commits:"
    echo "$CHANGES" | while IFS= read -r line; do echo "    $line"; done
else
    echo "  Already up to date."
fi

# 8. Next steps
echo ""
echo "  Rescue complete. Next steps:"
echo ""
echo "    agency upgrade       Sync skills and agents to $AGENCY_ROOT/"
echo "    agency onboard       Interactive setup wizard (if first time)"
echo "    ./install.sh         Full reinstall (if agency command not found)"
echo ""

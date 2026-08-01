#!/usr/bin/env bash
set -euo pipefail

# The Agency — Rescue Script
# Safely pulls the latest code when `agency upgrade` is broken.
# Pure bash + git. Zero Node dependency.
# Works from inside the repo, from anywhere via curl | bash, or as a first-time clone.

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
#    a root — every write below goes to $AGENCY_ROOT.
if [ -z "$REPO_DIR" ]; then
    for loc in "$AGENCY_ROOT" "$HOME/.claude" "$HOME/the-agency" "$HOME/.agency/the-agency"; do
        if [ -d "$loc" ] && is_agency_repo "$loc"; then
            REPO_DIR="$loc"
            break
        fi
    done
fi

# c) Not found — clone it
if [ -z "$REPO_DIR" ]; then
    CLONE_TARGET="$AGENCY_ROOT"
    echo "  The Agency repo not found locally. Cloning to $CLONE_TARGET/ ..."

    if [ -d "$CLONE_TARGET" ] && [ "$(ls -A "$CLONE_TARGET" 2>/dev/null)" ]; then
        # the root exists with files — clone into it without overwriting
        TEMP_DIR="$(mktemp -d)"
        if git clone "$AGENCY_REPO" "$TEMP_DIR/the-agency" 2>&1; then
            cp -rn "$TEMP_DIR/the-agency/"* "$CLONE_TARGET/" 2>/dev/null || true
            cp -rn "$TEMP_DIR/the-agency/".git "$CLONE_TARGET/" 2>/dev/null || true
            rm -rf "$TEMP_DIR"
            REPO_DIR="$CLONE_TARGET"
            echo "  Merged into existing $REPO_DIR"
        else
            rm -rf "$TEMP_DIR"
            echo "  Error: git clone failed. Check your network connection."
            exit 1
        fi
    elif git clone "$AGENCY_REPO" "$CLONE_TARGET" 2>&1; then
        REPO_DIR="$CLONE_TARGET"
        echo "  Cloned to $REPO_DIR"
    else
        echo "  Error: git clone failed. Check your network connection."
        exit 1
    fi

    echo ""
    echo "  First-time install — run the installer next:"
    echo "    cd $REPO_DIR && ./install.sh"
    echo ""
    exit 0
fi

echo "  Repo: $REPO_DIR"
cd "$REPO_DIR"

# 2. Detect and clean up in-progress rebase/merge
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
        echo "  Your local changes will be lost. Press Ctrl+C within 5 seconds to cancel."
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

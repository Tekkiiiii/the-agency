#!/usr/bin/env bash
set -euo pipefail

# The Agency — Rescue Script
# Safely pulls the latest code when `agency upgrade` is broken.
# Pure bash + git. Zero Node dependency.
# Works from inside the repo, from anywhere via curl | bash, or as a first-time clone.

AGENCY_REPO="https://github.com/Tekkiiiii/the-agency.git"

echo ""
echo "The Agency — Rescue"
echo "==================="
echo ""

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

# b) Check common install locations
if [ -z "$REPO_DIR" ]; then
    for loc in "$HOME/the-agency" "$HOME/.claude/the-agency" "$HOME/.agency/the-agency"; do
        if [ -d "$loc" ] && is_agency_repo "$loc"; then
            REPO_DIR="$loc"
            break
        fi
    done
fi

# c) Not found — clone it
if [ -z "$REPO_DIR" ]; then
    echo "  The Agency repo not found locally. Cloning..."
    CLONE_TARGET="$HOME/the-agency"
    if git clone "$AGENCY_REPO" "$CLONE_TARGET" 2>&1; then
        REPO_DIR="$CLONE_TARGET"
        echo "  Cloned to $REPO_DIR"
        echo ""
        echo "  First-time install — run the installer next:"
        echo "    cd $REPO_DIR && ./install.sh"
        echo ""
        exit 0
    else
        echo "  Error: git clone failed. Check your network connection."
        exit 1
    fi
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
echo "    agency upgrade       Sync skills and agents to ~/.claude/"
echo "    agency onboard       Interactive setup wizard (if first time)"
echo "    ./install.sh         Full reinstall (if agency command not found)"
echo ""

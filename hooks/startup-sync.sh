#!/bin/bash
# Auto-sync ~/.claude config on Claude Code startup

cd ~/.claude
timeout 5 git fetch origin main 2>/dev/null || { echo "⚠️  Not a git repo yet or fetch timed out — skipping sync"; exit 0; }

LOCAL=$(git rev-parse @ 2>/dev/null)
REMOTE=$(git rev-parse origin/main 2>/dev/null)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "🔄 Syncing config from remote..."
    git stash -u -q 2>/dev/null
    if git pull --ff-only -q 2>/dev/null; then
        git stash pop -q 2>/dev/null
        echo "✅ Config synced from GitHub"
    else
        git stash pop -q 2>/dev/null
        echo "⚠️  Config diverged from remote — manual merge needed (local changes preserved)"
    fi
else
    echo "✅ Config up to date"
fi

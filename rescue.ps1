# The Agency — Rescue Script (Windows PowerShell)
# Safely pulls the latest code when `agency upgrade` is broken.
# Pure PowerShell + git. Zero Node dependency.

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "The Agency — Rescue"
Write-Host "==================="
Write-Host ""

# 1. Find repo root
$RepoDir = git rev-parse --show-toplevel 2>$null
if (-not $RepoDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (Test-Path (Join-Path $ScriptDir ".git")) {
        $RepoDir = $ScriptDir
    } else {
        Write-Host "  Error: not inside a git repository."
        Write-Host "  Run this from inside the-agency repo."
        exit 1
    }
}

Write-Host "  Repo: $RepoDir"
Set-Location $RepoDir

# 2. Detect and clean up in-progress rebase/merge
if ((Test-Path ".git/REBASE_HEAD") -or (Test-Path ".git/rebase-merge") -or (Test-Path ".git/rebase-apply")) {
    Write-Host "  Detected rebase in progress — aborting it..."
    git rebase --abort 2>$null
}

if (Test-Path ".git/MERGE_HEAD") {
    Write-Host "  Detected merge in progress — aborting it..."
    git merge --abort 2>$null
}

if (Test-Path ".git/CHERRY_PICK_HEAD") {
    Write-Host "  Detected cherry-pick in progress — aborting it..."
    git cherry-pick --abort 2>$null
}

# 3. Fetch latest
Write-Host ""
Write-Host "  Fetching origin/main..."
$fetchResult = git fetch origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Error: git fetch failed. Check your network connection."
    exit 1
}

# 4. Stash local changes
$Stashed = $false
$Dirty = git status --porcelain 2>$null
if ($Dirty) {
    Write-Host "  Stashing local changes..."
    git stash --include-untracked 2>&1
    if ($LASTEXITCODE -eq 0) {
        $Stashed = $true
        Write-Host "  Stashed successfully."
    } else {
        Write-Host "  Warning: stash failed. Resetting to origin/main..."
        git reset --hard origin/main
    }
}

# 5. Pull latest
Write-Host ""
Write-Host "  Pulling latest from origin/main..."
git pull --rebase origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Pull failed. Forcing reset to origin/main..."
    git rebase --abort 2>$null
    git reset --hard origin/main
}

# 6. Restore stashed changes
if ($Stashed) {
    Write-Host ""
    Write-Host "  Restoring your local changes..."
    git stash pop 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  Stash pop had conflicts. Your changes are safe in the stash."
        Write-Host "  To see them:   git stash show -p"
        Write-Host "  To drop them:  git stash drop"
    }
}

# 7. Show what changed
Write-Host ""
$Changes = git log ORIG_HEAD..HEAD --oneline 2>$null
if ($Changes) {
    Write-Host "  Updated commits:"
    foreach ($line in $Changes) { Write-Host "    $line" }
} else {
    Write-Host "  Already up to date."
}

# 8. Next steps
Write-Host ""
Write-Host "  Rescue complete. Next steps:"
Write-Host ""
Write-Host "    agency upgrade       Sync skills and agents"
Write-Host "    agency onboard       Interactive setup wizard (if first time)"
Write-Host "    .\install.ps1        Full reinstall (if agency command not found)"
Write-Host ""

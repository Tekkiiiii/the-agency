# The Agency — Rescue Script (Windows PowerShell)
# Safely pulls the latest code when `agency upgrade` is broken.
# Pure PowerShell + git. Zero Node dependency.

$ErrorActionPreference = "Continue"

# Root precedence must match hooks/lib/resolve-root.sh and install.ps1 exactly:
#   $env:AGENCY_HOME -> $env:CLAUDE_CONFIG_DIR -> $env:USERPROFILE\.claude
# This is the PowerShell equivalent of the ladder rescue.sh inlines; there is no
# .sh to source from a native PowerShell session, so it is written out the same
# way install.ps1 writes it.
$AgencyRoot = if ($env:AGENCY_HOME) { $env:AGENCY_HOME }
              elseif ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR }
              else { Join-Path $env:USERPROFILE ".claude" }

Write-Host ""
Write-Host "The Agency — Rescue"
Write-Host "==================="
Write-Host ""

# Verify a directory is THE agency repo by its remote, not by "has a .git".
# rescue.sh has always done this; rescue.ps1 did not, and step 5 below can
# `git reset --hard origin/main`. Run from inside an unrelated repository, the
# old version would have reset THAT repository. The check is the fix.
function Test-AgencyRepo {
    param([string]$Dir)
    if (-not $Dir) { return $false }
    if (-not (Test-Path (Join-Path $Dir ".git"))) { return $false }
    $url = git -C $Dir remote get-url origin 2>$null
    if (-not $url) { return $false }
    return ($url -like "*Tekkiiiii/the-agency*") -or ($url -like "*the-agency/the-agency*")
}

# 1. Find the-agency repo
$RepoDir = $null

# a) already inside it?
$Candidate = git rev-parse --show-toplevel 2>$null
if (Test-AgencyRepo $Candidate) { $RepoDir = $Candidate }

# b) the script's own directory
if (-not $RepoDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (Test-AgencyRepo $ScriptDir) { $RepoDir = $ScriptDir }
}

# c) the resolved root first, then the legacy/alternate layouts rescue.sh also
#    searches. Adopted only — never written to as a root.
if (-not $RepoDir) {
    foreach ($loc in @($AgencyRoot,
                       (Join-Path $env:USERPROFILE ".claude"),
                       (Join-Path $env:USERPROFILE "the-agency"),
                       (Join-Path $env:USERPROFILE ".agency\the-agency"))) {
        if (Test-AgencyRepo $loc) { $RepoDir = $loc; break }
    }
}

if (-not $RepoDir) {
    Write-Host "  Error: the-agency repo not found."
    Write-Host "  Searched: the current directory, this script's directory,"
    Write-Host "            $AgencyRoot"
    Write-Host "            $(Join-Path $env:USERPROFILE 'the-agency')"
    Write-Host "            $(Join-Path $env:USERPROFILE '.agency\the-agency')"
    Write-Host ""
    Write-Host "  Clone it, then run the installer:"
    Write-Host "    git clone https://github.com/Tekkiiiii/the-agency.git `"$AgencyRoot`""
    Write-Host "    cd `"$AgencyRoot`"; .\install.ps1"
    exit 1
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
Write-Host "    agency upgrade       Sync skills and agents to $AgencyRoot"
Write-Host "    agency onboard       Interactive setup wizard (if first time)"
Write-Host "    .\install.ps1        Full reinstall (if agency command not found)"
Write-Host ""

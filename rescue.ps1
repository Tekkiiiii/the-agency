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

# ─── Backups before anything destructive ─────────────────────────────────────
# Mirrors rescue.sh. Every `git reset --hard` below used to run unguarded: when
# the stash failed it silently deleted local changes, and on a force-pushed
# (rewritten) origin it silently dropped local COMMITS. Now nothing is reset
# until (a) every changed or untracked file is copied to
# %USERPROFILE%\.agency\backups\<ts>\ (outside the repo, relative paths kept)
# and (b) a HEAD that origin/main does not contain is kept on a branch
# agency-backup/<ts>. If the copy fails, nothing is reset.
$BackupTs = Get-Date -Format "yyyyMMdd-HHmmss"
$script:BackupDir = $null       # created lazily, only when there is something to copy
$script:BackupBranch = $null

function Get-BackupDir {
    if ($script:BackupDir) { return $script:BackupDir }
    $base = Join-Path $env:USERPROFILE ".agency\backups"
    $d = Join-Path $base $BackupTs
    $n = 2
    while (Test-Path -LiteralPath $d) { $d = Join-Path $base "$BackupTs-$n"; $n++ }
    New-Item -ItemType Directory -Force -Path $d -ErrorAction Stop | Out-Null
    $script:BackupDir = $d
    return $d
}

# git prints unusual paths C-quoted ("a \"b\".txt") even with
# core.quotePath=false; undo the common escapes.
function ConvertFrom-GitQuoted {
    param([string]$P)
    if ($P.Length -ge 2 -and $P.StartsWith('"') -and $P.EndsWith('"')) {
        $P = $P.Substring(1, $P.Length - 2) -replace '\\"', '"' -replace '\\\\', '\'
    }
    return $P
}

# Copies one repo-relative path, keeping its relative layout. A path that no
# longer exists (a deletion) has nothing to copy. Returns $false on failure.
function Copy-ToBackup {
    param([string]$Rel)
    $src = Join-Path (Get-Location).Path $Rel
    if (-not (Test-Path -LiteralPath $src)) { return $true }
    try {
        $dest = Join-Path (Get-BackupDir) $Rel
        $parent = Split-Path -Parent $dest
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent -ErrorAction Stop | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force -ErrorAction Stop
        return $true
    } catch {
        Write-Host "  Could not back up ${Rel}: $_"
        return $false
    }
}

# Every changed/staged/untracked path; $null if git status itself failed.
# A rename/copy line is "R  old -> new": keep the new path.
function Get-ChangedPaths {
    $lines = git -c core.quotePath=false status --porcelain=v1 --untracked-files=all 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $paths = @()
    foreach ($line in @($lines)) {
        if (-not $line -or $line.Length -lt 4) { continue }
        $p = $line.Substring(3)
        if ($line[0] -eq 'R' -or $line[0] -eq 'C') {
            $i = $p.IndexOf(' -> ')
            if ($i -ge 0) { $p = $p.Substring($i + 4) }
        }
        $paths += (ConvertFrom-GitQuoted $p)
    }
    return ,$paths
}

function Get-UnmergedPaths {
    $lines = git -c core.quotePath=false diff --name-only --diff-filter=U 2>$null
    $paths = @()
    foreach ($line in @($lines)) { if ($line) { $paths += (ConvertFrom-GitQuoted $line) } }
    return ,$paths
}

function New-BackupBranch {
    param([string]$Sha)
    if ($script:BackupBranch) { return }
    $name = "agency-backup/$BackupTs"
    $n = 2
    while ($true) {
        git show-ref --verify --quiet "refs/heads/$name" 2>$null
        if ($LASTEXITCODE -ne 0) { break }
        $name = "agency-backup/$BackupTs-$n"; $n++
    }
    git branch $name $Sha 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Error: could not create a backup branch for your local commits. NOT resetting."
        exit 1
    }
    $script:BackupBranch = $name
    Write-Host "  Backup branch: $name (your old HEAD $Sha)"
    Write-Host "  To recover a commit from it: git log $name, then git cherry-pick <sha>"
}

# Call immediately before EVERY `git reset --hard`. Exits when anything could
# not be backed up.
function Backup-BeforeReset {
    $dirty = git status --porcelain 2>$null
    if ($dirty) {
        $paths = Get-ChangedPaths
        if ($null -eq $paths) { Write-Host "  Error: could not list your local changes. NOT resetting."; exit 1 }
        foreach ($p in $paths) {
            if (-not (Copy-ToBackup $p)) {
                Write-Host "  Error: could not back up your local changes. NOT resetting."
                if ($script:BackupDir) { Write-Host "  Partial copy: $script:BackupDir" }
                exit 1
            }
        }
        if ($script:BackupDir) { Write-Host "  Backed up your local changes to: $script:BackupDir" }
    }
    $head = git rev-parse -q --verify HEAD 2>$null
    if ($head) {
        git merge-base --is-ancestor $head origin/main 2>$null
        if ($LASTEXITCODE -ne 0) { New-BackupBranch $head }
    }
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

# 2a. A stale .git\index.lock (crashed git process) blocks every index write.
#     Older than 10 minutes: remove it. Younger: it may belong to a live git
#     process or an editor — stop and say exactly how to remove it.
$LockPath = Join-Path $RepoDir ".git\index.lock"
if (Test-Path -LiteralPath $LockPath) {
    $lockAge = (Get-Date) - (Get-Item -LiteralPath $LockPath).LastWriteTime
    if ($lockAge.TotalMinutes -gt 10) {
        Remove-Item -LiteralPath $LockPath -Force
        Write-Host "  Removed stale $LockPath ($([int]$lockAge.TotalMinutes) min old, left by a crashed git process)."
    } else {
        Write-Host "  Error: $LockPath exists and is less than 10 minutes old."
        Write-Host "  Another git process (or an editor) may still be running. If none is, remove it and re-run:"
        Write-Host "    Remove-Item `"$LockPath`""
        Write-Host "    (cmd.exe: del `"$LockPath`")"
        exit 1
    }
}

# 2b. Files left unmerged by an earlier conflict: copy them out first (an
#     in-progress merge abort below would otherwise discard their content).
$Unmerged = Get-UnmergedPaths
if ($Unmerged.Count -gt 0) {
    Write-Host "  Found files left unmerged by an earlier conflict:"
    foreach ($p in $Unmerged) {
        Write-Host "    $p"
        if (-not (Copy-ToBackup $p)) { Write-Host "  Error: could not back up $p. Stopping without changes."; exit 1 }
    }
    Write-Host "  Backup copy: $script:BackupDir"
}

# 2c. Detect and clean up in-progress rebase/merge
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

# 2d. Unmerged paths still left (no operation in progress, e.g. a conflicted
#     stash pop): clear the conflict state but KEEP the working-tree content,
#     so `git stash` can run and the content rides along in it.
$Unmerged = Get-UnmergedPaths
if ($Unmerged.Count -gt 0) {
    $env:GIT_LITERAL_PATHSPECS = "1"
    foreach ($p in $Unmerged) { git reset -q -- $p 2>$null | Out-Null }
    Remove-Item Env:GIT_LITERAL_PATHSPECS -ErrorAction SilentlyContinue
    if ((Get-UnmergedPaths).Count -gt 0) {
        Write-Host "  Error: could not clear the unmerged state. Check: git status"
        exit 1
    }
    Write-Host "  Cleared the conflict state (content kept in your working tree)."
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
        Backup-BeforeReset
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
    Backup-BeforeReset
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

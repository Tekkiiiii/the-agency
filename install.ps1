# The Agency — Install script for Windows (PowerShell)
# Copies skills and agents into ~/.claude/ for Claude Code

$ErrorActionPreference = "Stop"

# Root precedence must match hooks/lib/resolve-root.sh exactly — otherwise the
# installer writes to one directory and the deployed scripts read from another.
$ClaudeHome = if ($env:AGENCY_HOME) { $env:AGENCY_HOME }
              elseif ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR }
              else { Join-Path $env:USERPROFILE ".claude" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "The Agency - Installing to $ClaudeHome"
Write-Host "========================================="
Write-Host ""

# Create directories
foreach ($dir in @("skills", "agents", "projects", "sessions", "memory")) {
    $path = Join-Path $ClaudeHome $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# --- Skills ---
$SkillsSrc = Join-Path $ScriptDir "skills"
$SkillsDest = Join-Path $ClaudeHome "skills"
$skillCount = 0

if (Test-Path $SkillsSrc) {
    # Canonical skill layout is directory-only: skills/<name>/SKILL.md, plus any
    # supporting assets alongside it. This loop previously globbed skills/*.md —
    # the flat layout the repo abandoned and now fails CI on
    # (scripts/check-flat-skills.js) — so install.ps1 silently installed ZERO
    # skills while printing a success line. Copy whole skill directories.
    $skillDirs = Get-ChildItem -Path $SkillsSrc -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }

    foreach ($dir in $skillDirs) {
        $skillDir = Join-Path $SkillsDest $dir.Name

        if (-not (Test-Path $skillDir)) {
            New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
        }

        Copy-Item -Path (Join-Path $dir.FullName "*") -Destination $skillDir -Recurse -Force
        $pyCache = Join-Path $skillDir "__pycache__"
        if (Test-Path $pyCache) { Remove-Item -Path $pyCache -Recurse -Force }
        $skillCount++
    }

    # Copy INDEX.md
    $indexSrc = Join-Path $SkillsSrc "INDEX.md"
    if (Test-Path $indexSrc) {
        Copy-Item -Path $indexSrc -Destination (Join-Path $SkillsDest "INDEX.md") -Force
    }

    Write-Host "  ✓ $skillCount skills installed"

    # Loud mismatch check — a silent repo-vs-installed gap is exactly the
    # failure mode that hid the flat-layout bug above for this long.
    $repoSkillCount = (Get-ChildItem -Path $SkillsSrc -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }).Count
    if ($skillCount -ne $repoSkillCount) {
        Write-Host "  ⚠ Skill count mismatch: repo has $repoSkillCount, installed $skillCount"
    }
} else {
    Write-Host "  ⚠ No skills/ directory found"
}

# --- Agents ---
$AgentsSrc = Join-Path $ScriptDir "agents"
$AgentsDest = Join-Path $ClaudeHome "agents"
$agentCount = 0

function Copy-AgentDir {
    param([string]$Src, [string]$Dest)

    if (-not (Test-Path $Src)) { return }

    foreach ($item in Get-ChildItem -Path $Src) {
        $destPath = Join-Path $Dest $item.Name

        if ($item.PSIsContainer) {
            if (-not (Test-Path $destPath)) {
                New-Item -ItemType Directory -Path $destPath -Force | Out-Null
            }
            Copy-AgentDir -Src $item.FullName -Dest $destPath
        } elseif ($item.Extension -eq ".md") {
            Copy-Item -Path $item.FullName -Destination $destPath -Force
            $script:agentCount++
        }
    }
}

if (Test-Path $AgentsSrc) {
    if (-not (Test-Path $AgentsDest)) {
        New-Item -ItemType Directory -Path $AgentsDest -Force | Out-Null
    }
    Copy-AgentDir -Src $AgentsSrc -Dest $AgentsDest
    Write-Host "  ✓ $agentCount agents installed"
} else {
    Write-Host "  ⚠ No agents/ directory found"
}

# --- Core docs ---
$CoreSrc = Join-Path $ScriptDir "core"
$CoreDest = Join-Path $ClaudeHome "core"
if (Test-Path $CoreSrc) {
    Copy-Item -Path $CoreSrc -Destination $CoreDest -Recurse -Force
    Write-Host "  ✓ Core docs installed"
}

# --- Hooks, runbooks, scripts, design-system ---
# These four trees carry paths that shipped agent defs, runbooks and skills
# reference as `{agency-root}/hooks/...`, `{agency-root}/runbooks/...`,
# `{agency-root}/scripts/...` and `{agency-root}/design-system/...`.
# install.ps1 previously shipped none of them, so every such reference dangled
# on a Windows install. Keep this list in sync with install.sh and
# cli/commands/init.js — see docs/INSTALL-LAYOUT.md.
foreach ($tree in @("hooks", "runbooks", "scripts", "design-system")) {
    $TreeSrc = Join-Path $ScriptDir $tree
    $TreeDest = Join-Path $ClaudeHome $tree
    if (Test-Path $TreeSrc) {
        if (-not (Test-Path $TreeDest)) {
            New-Item -ItemType Directory -Path $TreeDest -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $TreeSrc "*") -Destination $TreeDest -Recurse -Force
        $PyCache = Join-Path $TreeDest "__pycache__"
        if (Test-Path $PyCache) { Remove-Item -Path $PyCache -Recurse -Force }
        Write-Host "  ✓ $tree installed"
    } else {
        Write-Host "  ⚠ No $tree/ directory found"
    }
}

# --- CLI command ---
$CliSrc = Join-Path $ScriptDir "cli\bin\agency.js"
if (Test-Path $CliSrc) {
    # Create a batch shim in a directory on PATH
    $ShimDir = Join-Path $env:USERPROFILE ".local\bin"
    if (-not (Test-Path $ShimDir)) {
        New-Item -ItemType Directory -Path $ShimDir -Force | Out-Null
    }

    $ShimPath = Join-Path $ShimDir "agency.cmd"
    Set-Content -Path $ShimPath -Value "@node `"$CliSrc`" %*"
    Write-Host "  ✓ CLI shim created → $ShimPath"

    # Add to user PATH if not already there
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$ShimDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$ShimDir;$UserPath", "User")
        $env:Path = "$ShimDir;$env:Path"
        Write-Host "  ✓ Added $ShimDir to user PATH"
        Write-Host "    (restart your terminal for PATH changes to take effect)"
    }
}

Write-Host ""
Write-Host "✓ The Agency installed to $ClaudeHome"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  agency onboard                      Interactive setup wizard"
Write-Host '  agency new my-app "description"      Create your first project'
Write-Host "  agency status                       See all projects"
Write-Host ""

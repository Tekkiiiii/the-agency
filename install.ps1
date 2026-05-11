# The Agency — Install script for Windows (PowerShell)
# Copies skills and agents into ~/.claude/ for Claude Code

$ErrorActionPreference = "Stop"

$ClaudeHome = if ($env:AGENCY_HOME) { $env:AGENCY_HOME } else { Join-Path $env:USERPROFILE ".claude" }
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
    $skillFiles = Get-ChildItem -Path $SkillsSrc -Filter "*.md" |
        Where-Object { $_.Name -notin @("INDEX.md", "README.md") }

    foreach ($file in $skillFiles) {
        $name = $file.BaseName
        $skillDir = Join-Path $SkillsDest $name
        $destFile = Join-Path $skillDir "SKILL.md"

        if (-not (Test-Path $skillDir)) {
            New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
        }

        Copy-Item -Path $file.FullName -Destination $destFile -Force
        $skillCount++
    }

    # Copy INDEX.md
    $indexSrc = Join-Path $SkillsSrc "INDEX.md"
    if (Test-Path $indexSrc) {
        Copy-Item -Path $indexSrc -Destination (Join-Path $SkillsDest "INDEX.md") -Force
    }

    Write-Host "  ✓ $skillCount skills installed"
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

Write-Host ""
Write-Host "✓ The Agency installed to $ClaudeHome"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open Claude Code in any project"
Write-Host "  2. Skills are available as /skill-name"
Write-Host '  3. Run: agency new my-app "description"'
Write-Host ""

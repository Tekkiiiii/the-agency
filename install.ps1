# The Agency — Install script for Windows (PowerShell)
# Copies skills and agents into ~/.claude/ for Claude Code

$ErrorActionPreference = "Stop"

# Root precedence must match hooks/lib/resolve-root.sh exactly — otherwise the
# installer writes to one directory and the deployed scripts read from another.
$ClaudeHome = if ($env:AGENCY_HOME) { $env:AGENCY_HOME }
              elseif ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR }
              else { Join-Path $env:USERPROFILE ".claude" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Which rung of the ladder above resolved the root, and whether settings.json
# existed BEFORE this script runs. Real case: a Windows user with config on D:
# synced into $env:USERPROFILE\.claude, which Claude Code never read, unwarned.
$RootSource = if ($env:AGENCY_HOME) { "AGENCY_HOME" }
              elseif ($env:CLAUDE_CONFIG_DIR) { "CLAUDE_CONFIG_DIR" }
              else { "default" }
$RootWarn = ($RootSource -eq "default") -and -not (Test-Path -LiteralPath (Join-Path $ClaudeHome "settings.json"))
function Write-RootWarning {
    Write-Host "  ⚠ No settings.json at $ClaudeHome, and neither AGENCY_HOME nor CLAUDE_CONFIG_DIR is set."
    Write-Host "    If your Claude Code config lives elsewhere (e.g. D:\claude or a custom folder),"
    Write-Host "    set CLAUDE_CONFIG_DIR or AGENCY_HOME to that folder and re-run."
}

Write-Host ""
Write-Host "The Agency - Installing to $ClaudeHome"
Write-Host "========================================="
if ($RootSource -eq "default") {
    Write-Host "  Sync root: $ClaudeHome (from default - neither AGENCY_HOME nor CLAUDE_CONFIG_DIR is set)"
} else {
    Write-Host "  Sync root: $ClaudeHome (from $RootSource)"
}
if ($RootWarn) { Write-RootWarning }
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
# NOT a blind recursive copy. A few files under core/memory/ ship as empty
# scaffolds that the running system appends rows to AT THEIR INSTALLED PATH —
# the project registry, the delegator route cache, the operator's quality
# thresholds. Overwriting them destroyed those rows on every reinstall,
# silently. core/.preserve lists them; the rule is skip-if-exists, so a fresh
# install still seeds them and everything else still refreshes. That one list
# is also read by install.sh and by syncCore() in cli/commands/sync-assets.js.
#
# This also copies core's CONTENTS rather than the directory itself. The old
# `Copy-Item -Path $CoreSrc -Destination $CoreDest -Recurse` only did the right
# thing when $CoreDest did not exist yet; on a second install into the same
# root PowerShell copies the directory INTO the target and you get
# {root}\core\core\. CI never caught it because its second install used a
# different AGENCY_HOME. install.sh and the CLI path always copied contents.
$CoreSrc = Join-Path $ScriptDir "core"
$CoreDest = Join-Path $ClaudeHome "core"
if (Test-Path $CoreSrc) {
    if (-not (Test-Path $CoreDest)) {
        New-Item -ItemType Directory -Path $CoreDest -Force | Out-Null
    }

    $CorePreserve = @()
    $CorePreserveList = Join-Path $CoreSrc ".preserve"
    if (Test-Path $CorePreserveList) {
        # @() forced: a one-entry list would otherwise collapse to a scalar
        # string, and the -contains below would then be a substring-free
        # equality on the wrong shape.
        $CorePreserve = @(Get-Content $CorePreserveList |
            ForEach-Object { ($_ -replace '#.*$', '').Trim() } |
            Where-Object { $_ -ne '' })
    }

    $CoreSynced = 0
    $CorePreserved = 0
    $CoreSrcRoot = (Resolve-Path $CoreSrc).Path
    # -Force so dotfiles (.preserve itself) are enumerated, matching the other
    # two installers, which both copy them.
    foreach ($CoreFile in (Get-ChildItem -Path $CoreSrc -Recurse -File -Force)) {
        # Compare and match in forward-slash form — that is what .preserve uses.
        $CoreRel = $CoreFile.FullName.Substring($CoreSrcRoot.Length).TrimStart('\', '/').Replace('\', '/')
        if ($CoreRel -eq '.DS_Store' -or $CoreRel -like '*/.DS_Store' -or
            $CoreRel -like '__pycache__/*' -or $CoreRel -like '*/__pycache__/*' -or
            $CoreRel -like '*.pyc') { continue }

        $CoreTarget = Join-Path $CoreDest $CoreRel
        if ((Test-Path $CoreTarget) -and ($CorePreserve -contains $CoreRel)) {
            $CorePreserved++
            continue
        }
        $CoreTargetDir = Split-Path -Parent $CoreTarget
        if (-not (Test-Path $CoreTargetDir)) {
            New-Item -ItemType Directory -Path $CoreTargetDir -Force | Out-Null
        }
        Copy-Item -Path $CoreFile.FullName -Destination $CoreTarget -Force
        $CoreSynced++
    }
    Write-Host "  ✓ Core docs installed ($CoreSynced synced, $CorePreserved preserved)"
}

# --- Hooks, runbooks, scripts, design-system, agents-archive ---
# These five trees carry paths that shipped agent defs, runbooks and skills
# reference as `{agency-root}/hooks/...`, `{agency-root}/runbooks/...`,
# `{agency-root}/scripts/...`, `{agency-root}/design-system/...` and
# `{agency-root}/agents-archive/...` (role files + ROLE-MAP.md, plain copy,
# never under agents/ so nothing registers).
# install.ps1 previously shipped none of them, so every such reference dangled
# on a Windows install. Keep this list in sync with install.sh and
# cli/commands/init.js — see docs/INSTALL-LAYOUT.md.
foreach ($tree in @("hooks", "runbooks", "scripts", "design-system", "agents-archive")) {
    $TreeSrc = Join-Path $ScriptDir $tree
    $TreeDest = Join-Path $ClaudeHome $tree
    if (Test-Path $TreeSrc) {
        if (-not (Test-Path $TreeDest)) {
            New-Item -ItemType Directory -Path $TreeDest -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $TreeSrc "*") -Destination $TreeDest -Recurse -Force
        # Recursive: scripts\skill-route\ (and any future subdir) must not ship bytecode either.
        @(Get-ChildItem -Path $TreeDest -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue) |
            ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
        Write-Host "  ✓ $tree installed"
    } else {
        Write-Host "  ⚠ No $tree/ directory found"
    }
}

# --- Wire hooks into settings.json ---
# Same merge as install.sh, `agency init` and `agency upgrade`:
# cli\lib\hooks-merge.js reads hooks\hooks.json and merges it into
# settings.json on EVERY install. It adds missing hooks, updates or prunes only
# entries it owns, never touches the user's own hooks or other keys, copies the
# file to settings.json.bak-<timestamp> next to itself before any change, and
# writes nothing when nothing changed. It also checks for bash (Git Bash):
# Claude Code runs these hooks with bash, so without it wiring is skipped and
# the command to finish later is printed. This step never fails the install.
# Opt out with AGENCY_NO_HOOKS=1. Hook paths are written with forward slashes.
$HooksMerge = Join-Path $ScriptDir "cli\lib\hooks-merge.js"
function Write-HooksManual {
    Write-Host "    agency hooks sync"
    Write-Host "  or, without the agency command:"
    Write-Host "    node `"$HooksMerge`" sync --root `"$ClaudeHome`""
    Write-Host "  Then: Restart Claude Code to activate the hooks."
}
if ($env:AGENCY_NO_HOOKS -and $env:AGENCY_NO_HOOKS -ne "0") {
    Write-Host "  Hooks: NOT wired: AGENCY_NO_HOOKS=1 is set. To set them up, run:"
    Write-HooksManual
} elseif (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "  Hooks: NOT wired: Node.js (node) was not found. Install Node.js, then run:"
    Write-HooksManual
} elseif (-not (Test-Path $HooksMerge) -or -not (Test-Path (Join-Path $ScriptDir "hooks\hooks.json"))) {
    Write-Host "  Hooks: NOT wired: cli\lib\hooks-merge.js or hooks\hooks.json is missing from $ScriptDir."
} else {
    try {
        # stdout only: under $ErrorActionPreference = "Stop", redirecting a
        # native command's stderr can turn a warning line into a terminating error.
        $HooksOut = & node $HooksMerge sync --root $ClaudeHome --auto
        foreach ($line in $HooksOut) { Write-Host "  $line" }
    } catch {
        Write-Host "  Hooks: NOT wired: $($_.Exception.Message). To set them up, run:"
        Write-HooksManual
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
# One line: the optional skill router ships DISABLED. Read-only: enabled iff
# AGENCY_SKILL_ROUTER is exactly "1" in this environment OR in the "env" block of
# settings.json (where Claude Code users set it; a terminal does not inherit that).
# Any read/parse error means "not set". Same rule as cli/lib/skill-router.js; never
# creates the Jev key file.
$RouterOn = ($env:AGENCY_SKILL_ROUTER -eq "1")
if (-not $RouterOn) {
    try {
        $RouterSettings = Join-Path $ClaudeHome "settings.json"
        if (Test-Path $RouterSettings) {
            $RouterJson = Get-Content $RouterSettings -Raw | ConvertFrom-Json
            $RouterVal = $RouterJson.env.AGENCY_SKILL_ROUTER
            if (($RouterVal -is [string]) -and ($RouterVal -eq "1")) { $RouterOn = $true }
        }
    } catch { $RouterOn = $false }
}
if ($RouterOn) {
    Write-Host "Skill router: enabled (AGENCY_SKILL_ROUTER=1)"
} else {
    $RouterRoot = $ClaudeHome
    try { $RouterRoot = (Resolve-Path $ClaudeHome).Path } catch { }
    $RouterDoc = Join-Path $RouterRoot 'scripts\skill-route\README.md'
    Write-Host "Skill router: disabled (see $RouterDoc to enable)"
}
if ($RootWarn) { Write-RootWarning }
Write-Host ""
Write-Host "Next steps:"
Write-Host "  agency onboard                      Interactive setup wizard"
Write-Host '  agency new my-app "description"      Create your first project'
Write-Host "  agency status                       See all projects"
Write-Host ""

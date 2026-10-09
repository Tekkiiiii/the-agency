# check-mods-install.ps1 - regression guard for the mods wiring in install.ps1 and
# `agency upgrade` on Windows. Line-for-line parallel to check-mods-install.sh
# (read that header for the case list A-E); the engine is cli\lib\mods-merge.js
# and its unit test is check-mods-merge.js.
#
# Every case runs against a fresh temp AGENCY_HOME inside one sandbox directory;
# USERPROFILE/HOME point into it so nothing outside is touched. The installer
# runs in a child of the SAME PowerShell host that runs this script, so the
# windows job exercises both pwsh and Windows PowerShell 5.1.
#
# Code under test: $env:REPO (default: this checkout). AGENCY_CLAUDE_VERSION
# stands in for `claude --version` (CI has no claude CLI).
# ASCII only (check-ps1-ascii.js); Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Continue'

$Repo = $env:REPO
if (-not $Repo) { $Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$Repo = (Resolve-Path $Repo).Path
$PsExe = (Get-Process -Id $PID).Path

$Base = $env:RUNNER_TEMP
if (-not $Base) { $Base = [System.IO.Path]::GetTempPath() }
$W = Join-Path $Base ('mods-install-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $W -Force | Out-Null

$FakeHome = Join-Path $W 'home'
New-Item -ItemType Directory -Path $FakeHome -Force | Out-Null
$env:HOME = $FakeHome
$env:USERPROFILE = $FakeHome
foreach ($v in @('AGENCY_HOME', 'CLAUDE_CONFIG_DIR', 'AGENCY_NO_MODS', 'AGENCY_NO_HOOKS', 'AGENCY_CLAUDE_VERSION',
                 'AGENCY_UPGRADE_REEXEC', 'AGENCY_UPGRADE_HEAD_BEFORE')) {
    Remove-Item -Path "Env:\$v" -ErrorAction SilentlyContinue
}
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_AUTHOR_NAME = 'ci'; $env:GIT_AUTHOR_EMAIL = 'ci@example.invalid'
$env:GIT_COMMITTER_NAME = 'ci'; $env:GIT_COMMITTER_EMAIL = 'ci@example.invalid'

$Sep = ';'
$script:Fails = 0
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Ok([string]$msg) { Write-Host "  ok   $msg" }
function Bad([string]$msg) { Write-Host "  FAIL $msg"; $script:Fails++ }
function Check([string]$desc, [bool]$cond) { if ($cond) { Ok $desc } else { Bad $desc } }
function Has([string]$hay, [string]$needle) { return ($hay.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) }
function StartsWithCI([string]$hay, [string]$needle) { return $hay.StartsWith($needle, [System.StringComparison]::OrdinalIgnoreCase) }

function Read-Json([string]$file) {
    if (-not (Test-Path -LiteralPath $file)) { return $null }
    try { return (Get-Content -LiteralPath $file -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}
# Value of env.CLAUDE_CODE_PLUGIN_DIRS in <root>\settings.json, or $null when absent.
function Get-PluginDirs([string]$root) {
    $s = Read-Json (Join-Path $root 'settings.json')
    if ($null -eq $s -or $null -eq $s.env) { return $null }
    return $s.env.CLAUDE_CODE_PLUGIN_DIRS
}
function Get-State([string]$root) { return (Read-Json (Join-Path $root 'hooks\.agency-hooks-state.json')) }
function Count-Installed([string]$root) {
    $st = Get-State $root
    if ($null -eq $st -or $null -eq $st.mods -or $null -eq $st.mods.installed) { return -1 }
    return @($st.mods.installed).Count
}
function Write-Text([string]$file, [string]$text) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $file) -Force | Out-Null
    [System.IO.File]::WriteAllText($file, $text, $Utf8NoBom)
}

# Run the installer under test in a child of this host; returns its exit code.
function Install-Into([string]$root, [string]$ver, [string]$log, [string]$src) {
    if (-not $src) { $src = $Repo }
    $env:AGENCY_HOME = $root
    $env:AGENCY_CLAUDE_VERSION = $ver
    $out = & $PsExe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $src 'install.ps1') 2>&1 | Out-String
    $code = $LASTEXITCODE
    [System.IO.File]::WriteAllText($log, $out, $Utf8NoBom)
    return $code
}

Write-Host "check-mods-install: code under test = $Repo"
if (-not (Test-Path (Join-Path $Repo 'install.ps1'))) { Write-Host "  FAIL no install.ps1 in $Repo"; exit 1 }

# -- case A: merge with a user's existing entries -----------------------------
Write-Host "case A: install.ps1 merges into an existing CLAUDE_CODE_PLUGIN_DIRS"
$H = Join-Path $W 'a'
New-Item -ItemType Directory -Path (Join-Path $H 'mods\context-band') -Force | Out-Null
$UserDir = Join-Path $W 'userplug'
$UserEntry = Join-Path $UserDir 'loop-guard'
Write-Text (Join-Path $UserEntry '.claude-plugin\plugin.json') ('{ "name": "loop-guard", "version": "9.9.9" }' + "`n")
Write-Text (Join-Path $H 'mods\context-band\marker.txt') 'keep'
$seed = @{ env = @{ OTHER = 'x'; CLAUDE_CODE_PLUGIN_DIRS = $UserEntry } } | ConvertTo-Json -Depth 5
Write-Text (Join-Path $H 'settings.json') ($seed + "`n")
$code = Install-Into $H '2.1.293' (Join-Path $W 'a.log') $null
Check "install.ps1 exit 0 (got $code)" ($code -eq 0)
$val = [string](Get-PluginDirs $H)
Write-Host "    | CLAUDE_CODE_PLUGIN_DIRS = $val"
Check "value starts with the user's entry" (StartsWithCI $val $UserEntry)
Check "contains $H\mods\agent-ctx" (Has $val (Join-Path $H 'mods\agent-ctx'))
Check "contains $H\mods\spawn-ledger" (Has $val (Join-Path $H 'mods\spawn-ledger'))
Check "contains $H\mods\voice-compact" (Has $val (Join-Path $H 'mods\voice-compact'))
Check "joined with '$Sep'" (Has $val ($Sep + (Join-Path $H 'mods\agent-ctx')))
Check "loop-guard NOT added (user provides that name)" (-not (Has $val (Join-Path $H 'mods\loop-guard')))
Check "context-band NOT added (already on disk)" (-not (Has $val (Join-Path $H 'mods\context-band')))
Check "pre-existing context-band\marker.txt intact" ((Test-Path (Join-Path $H 'mods\context-band\marker.txt')) -and ((Get-Content -LiteralPath (Join-Path $H 'mods\context-band\marker.txt') -Raw).Trim() -eq 'keep'))
$s = Read-Json (Join-Path $H 'settings.json')
Check "env.OTHER still x" ($s.env.OTHER -eq 'x')
Check "hooks\lib\model-pin.py deployed" (Test-Path (Join-Path $H 'hooks\lib\model-pin.py'))
Check "hooks\lib\claude_pricing.py deployed" (Test-Path (Join-Path $H 'hooks\lib\claude_pricing.py'))
Check "hooks\lib\exec-model-map.json deployed" (Test-Path (Join-Path $H 'hooks\lib\exec-model-map.json'))
Check "no __pycache__ under hooks\lib" (-not (Test-Path (Join-Path $H 'hooks\lib\__pycache__')))
Check "state file records mods.installed of 3" ((Count-Installed $H) -eq 3)
Check "mod dirs copied: agent-ctx spawn-ledger voice-compact" ((Test-Path (Join-Path $H 'mods\agent-ctx')) -and (Test-Path (Join-Path $H 'mods\spawn-ledger')) -and (Test-Path (Join-Path $H 'mods\voice-compact')))
Check "no loop-guard copy made" (-not (Test-Path (Join-Path $H 'mods\loop-guard')))

# -- case B: idempotent -------------------------------------------------------
Write-Host "case B: a second install.ps1 leaves settings.json byte-identical"
$hashBefore = (Get-FileHash -LiteralPath (Join-Path $H 'settings.json') -Algorithm SHA256).Hash
$code = Install-Into $H '2.1.293' (Join-Path $W 'a2.log') $null
Check "second install.ps1 exit 0 (got $code)" ($code -eq 0)
$hashAfter = (Get-FileHash -LiteralPath (Join-Path $H 'settings.json') -Algorithm SHA256).Hash
Check "settings.json byte-identical" ($hashBefore -eq $hashAfter)

# -- case C: uninstall --------------------------------------------------------
Write-Host "case C: mods-merge.js remove restores the user's value exactly"
$env:AGENCY_CLAUDE_VERSION = '2.1.293'
$cOut = & node (Join-Path $Repo 'cli\lib\mods-merge.js') remove --root $H 2>&1 | Out-String
$code = $LASTEXITCODE
foreach ($l in ($cOut -split "`r?`n")) { if ($l) { Write-Host "    | $l" } }
Check "remove exit 0 (got $code)" ($code -eq 0)
Check "value == the user's entry exactly" ([string](Get-PluginDirs $H) -ceq $UserEntry)
Check "owned mod dirs gone" ((-not (Test-Path (Join-Path $H 'mods\agent-ctx'))) -and (-not (Test-Path (Join-Path $H 'mods\spawn-ledger'))) -and (-not (Test-Path (Join-Path $H 'mods\voice-compact'))))
Check "context-band\marker.txt intact" ((Test-Path (Join-Path $H 'mods\context-band\marker.txt')) -and ((Get-Content -LiteralPath (Join-Path $H 'mods\context-band\marker.txt') -Raw).Trim() -eq 'keep'))
$s = Read-Json (Join-Path $H 'settings.json')
Check "env.OTHER still x" ($s.env.OTHER -eq 'x')

# -- case D: version gate -----------------------------------------------------
Write-Host "case D: Claude Code 2.1.286 -> mods not wired, one skip note"
$H = Join-Path $W 'd'
$code = Install-Into $H '2.1.286' (Join-Path $W 'd.log') $null
Check "install.ps1 exit 0 (got $code)" ($code -eq 0)
Check "no CLAUDE_CODE_PLUGIN_DIRS key" ($null -eq (Get-PluginDirs $H))
Check "no <root>\mods directory" (-not (Test-Path (Join-Path $H 'mods')))
$dLog = Get-Content -LiteralPath (Join-Path $W 'd.log') -Raw
Check "skip note printed" ($dLog -match 'Mods: skipped \(needs Claude Code 2\.1\.287\+')

# -- case E: agency upgrade deploys the mods ----------------------------------
# `agency upgrade` pulls a git clone and syncs it into AGENCY_HOME, so the code
# under test goes into a scratch bare origin + clone (a copy of the working tree,
# uncommitted files included), the way check-upgrade-rewrite.sh does.
Write-Host "case E: agency upgrade wires the mods into a root installed without them"
$Seed = Join-Path $W 'seed'; $Origin = Join-Path $W 'origin\the-agency.git'; $Clone = Join-Path $W 'clone'
New-Item -ItemType Directory -Path $Seed -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $Origin) -Force | Out-Null
$files = @(& git -C $Repo -c core.quotepath=off ls-files -co --exclude-standard)
foreach ($rel in $files) {
    if ($rel -like 'node_modules/*' -or $rel -like '*/node_modules/*' -or $rel -like '*__pycache__*') { continue }
    $src = Join-Path $Repo $rel
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { continue }
    $dst = Join-Path $Seed $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
}
& git -c init.defaultBranch=main init -q $Seed 2>&1 | Out-Null
& git -C $Seed checkout -q -b main 2>&1 | Out-Null
# Seed blobs must be LF like real history; a CRLF working-tree copy (actions/checkout autocrlf=true) would make every file look rewritten upstream.
& git -C $Seed -c core.autocrlf=input add -A 2>&1 | Out-Null
& git -C $Seed -c core.autocrlf=false commit -q -m 'seed: code under test' 2>&1 | Out-Null
& git init -q --bare $Origin 2>&1 | Out-Null
& git -C $Origin symbolic-ref HEAD refs/heads/main 2>&1 | Out-Null
& git -C $Seed remote add origin $Origin 2>&1 | Out-Null
& git -C $Seed push -q origin main 2>&1 | Out-Null
& git -c core.autocrlf=false clone -q $Origin $Clone 2>&1 | Out-Null
Check "scratch clone has install.ps1" (Test-Path (Join-Path $Clone 'install.ps1'))

$H = Join-Path $W 'e'
$env:AGENCY_NO_MODS = '1'
$code = Install-Into $H '2.1.293' (Join-Path $W 'e1.log') $Clone
Remove-Item -Path 'Env:\AGENCY_NO_MODS' -ErrorAction SilentlyContinue
Check "install with AGENCY_NO_MODS=1 exit 0 (got $code)" ($code -eq 0)
Check "baseline: no mods wired" ($null -eq (Get-PluginDirs $H))
Check "baseline: no <root>\mods" (-not (Test-Path (Join-Path $H 'mods')))

$env:AGENCY_HOME = $H
$env:AGENCY_CLAUDE_VERSION = '2.1.293'
Push-Location $W
$eOut = & node (Join-Path $Clone 'cli\bin\agency.js') upgrade 2>&1 | Out-String
$code = $LASTEXITCODE
Pop-Location
foreach ($l in ($eOut -split "`r?`n")) { if ($l -match 'Mods|Restart|rror') { Write-Host "    | $l" } }
Check "agency upgrade exit 0 (got $code)" ($code -eq 0)
$val = [string](Get-PluginDirs $H)
Write-Host "    | CLAUDE_CODE_PLUGIN_DIRS = $val"
foreach ($m in @('agent-ctx', 'context-band', 'loop-guard', 'spawn-ledger', 'voice-compact')) {
    Check "upgrade wired $m" (Has $val (Join-Path $H "mods\$m"))
    Check "upgrade copied $m" (Test-Path (Join-Path $H "mods\$m\.claude-plugin\plugin.json"))
}
Check "state file records mods.installed of 5" ((Count-Installed $H) -eq 5)
Check "restart reminder in the upgrade summary" ($eOut -match 'Restart Claude Code to load the mods')

Remove-Item -Recurse -Force $W -ErrorAction SilentlyContinue
Write-Host ""
if ($script:Fails -eq 0) {
    Write-Host "PASS: check-mods-install ($Repo)"
    exit 0
}
Write-Host "FAIL: check-mods-install - $($script:Fails) check(s) failed ($Repo)"
exit 1

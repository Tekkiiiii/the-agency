# check-retired-install.ps1 - regression guard for the retired-files prune wired into
# install.ps1 and `agency upgrade` on Windows. Line-for-line parallel to
# check-retired-install.sh (read that header for the case list I, I-delete, I-bogus,
# U, U-delete, U-bogus, plus the legacy git installs L-B, L-B-other and L-A); the
# engine is cli\lib\retired-prune.js and its unit test is check-retired-prune.js.
#
# Every case runs against a fresh temp AGENCY_HOME inside one sandbox directory;
# USERPROFILE/HOME point into it so nothing outside is touched. The installer runs
# in a child of the SAME PowerShell host that runs this script, so the windows job
# exercises both pwsh and Windows PowerShell 5.1. The flag is passed as
# `-Retired delete|bogus` to install.ps1 and as `--retired=...` to `agency upgrade`.
#
# The "old install" is built by the OLD installer from the pre-sunset tree
# ($env:OLD_REV, default 723a223) with AGENCY_NO_MODS=1; it is a `git worktree` of
# the code under test, so that checkout needs FULL history (fetch-depth: 0).
#
# Code under test: $env:REPO (default: this checkout).
# ASCII only (check-ps1-ascii.js); Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Continue'

$Repo = $env:REPO
if (-not $Repo) { $Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$Repo = (Resolve-Path $Repo).Path
$OldRev = $env:OLD_REV
if (-not $OldRev) { $OldRev = '723a223' }
$PsExe = (Get-Process -Id $PID).Path

$Base = $env:RUNNER_TEMP
if (-not $Base) { $Base = [System.IO.Path]::GetTempPath() }
$W = Join-Path $Base ('retired-install-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $W -Force | Out-Null
$Old = Join-Path $W 'old-tree'

$FakeHome = Join-Path $W 'home'
New-Item -ItemType Directory -Path $FakeHome -Force | Out-Null
$env:HOME = $FakeHome
$env:USERPROFILE = $FakeHome
foreach ($v in @('AGENCY_HOME', 'CLAUDE_CONFIG_DIR', 'AGENCY_NO_MODS', 'AGENCY_NO_HOOKS', 'AGENCY_CLAUDE_VERSION', 'AGENCY_RETIRED',
                 'AGENCY_UPGRADE_REEXEC', 'AGENCY_UPGRADE_HEAD_BEFORE')) {
    Remove-Item -Path "Env:\$v" -ErrorAction SilentlyContinue
}
$env:GIT_CONFIG_NOSYSTEM = '1'
$env:GIT_AUTHOR_NAME = 'ci'; $env:GIT_AUTHOR_EMAIL = 'ci@example.invalid'
$env:GIT_COMMITTER_NAME = 'ci'; $env:GIT_COMMITTER_EMAIL = 'ci@example.invalid'
# The mods step depends on whether the machine has a claude CLI; this check is not about it.
$env:AGENCY_NO_MODS = '1'

$script:Fails = 0
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$EditMark = 'local edit by check-retired-install'

function Ok([string]$msg) { Write-Host "  ok   $msg" }
function Bad([string]$msg) { Write-Host "  FAIL $msg"; $script:Fails++ }
function Check([string]$desc, [bool]$cond) { if ($cond) { Ok $desc } else { Bad $desc } }
function Has([string]$hay, [string]$needle) { return ($hay.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) }
function Absent([string]$p) { return (-not (Test-Path -LiteralPath $p)) }
function Present([string]$p) { return (Test-Path -LiteralPath $p) }
function Read-Raw([string]$file) {
    if (-not (Test-Path -LiteralPath $file)) { return '' }
    return [string](Get-Content -LiteralPath $file -Raw -Encoding UTF8)
}
function Write-Text([string]$file, [string]$text) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $file) -Force | Out-Null
    [System.IO.File]::WriteAllText($file, $text, $Utf8NoBom)
}
# First archive\agency-retired-*\<rel> file under the root, or $null.
function Archived-File([string]$root, [string]$rel) {
    $arch = Join-Path $root 'archive'
    if (-not (Test-Path -LiteralPath $arch)) { return $null }
    foreach ($d in @(Get-ChildItem -LiteralPath $arch -Directory -Filter 'agency-retired-*' -ErrorAction SilentlyContinue)) {
        $f = Join-Path $d.FullName $rel
        if (Test-Path -LiteralPath $f -PathType Leaf) { return $f }
    }
    return $null
}
# One "<hash> <relative path>" line per file, sorted (change detector).
function Tree-Sum([string]$root) {
    $lines = @()
    $prefix = $root.TrimEnd('\') + '\'
    foreach ($f in @(Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction SilentlyContinue)) {
        $h = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
        $lines += ($h + ' ' + $f.FullName.Substring($prefix.Length))
    }
    return (($lines | Sort-Object) -join "`n")
}
function Cleanup {
    & git -C $Repo worktree remove --force $Old 2>&1 | Out-Null
    & git -C $Repo worktree prune 2>&1 | Out-Null
    Remove-Item -Recurse -Force $W -ErrorAction SilentlyContinue
}

# Run an installer (src\install.ps1) in a child of this host; returns its exit code.
# $extra is an array of arguments for install.ps1 (e.g. '-Retired','delete').
function Install-Into([string]$root, [string]$log, [string]$src, [string[]]$extra) {
    $env:AGENCY_HOME = $root
    $out = & $PsExe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $src 'install.ps1') @extra 2>&1 | Out-String
    $code = $LASTEXITCODE
    [System.IO.File]::WriteAllText($log, $out, $Utf8NoBom)
    return $code
}
# Run `agency upgrade` from the scratch clone; returns the exit code (log written).
function Upgrade-Into([string]$root, [string]$log, [string[]]$extra) {
    $env:AGENCY_HOME = $root
    Push-Location $W
    $out = & node (Join-Path $Clone 'cli\bin\agency.js') upgrade @extra 2>&1 | Out-String
    $code = $LASTEXITCODE
    Pop-Location
    [System.IO.File]::WriteAllText($log, $out, $Utf8NoBom)
    return $code
}

Write-Host "check-retired-install: code under test = $Repo, old install = $OldRev"
if (-not (Test-Path (Join-Path $Repo 'install.ps1'))) { Write-Host "  FAIL no install.ps1 in $Repo"; exit 1 }

# -- the pre-sunset tree ------------------------------------------------------
& git -C $Repo cat-file -e "$OldRev^{commit}" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  FAIL commit $OldRev is not in $Repo: this check needs the full git history (actions/checkout fetch-depth: 0)"
    Remove-Item -Recurse -Force $W -ErrorAction SilentlyContinue
    exit 1
}
& git -C $Repo worktree add -q --detach $Old $OldRev 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "  FAIL git worktree add $OldRev"; Cleanup; exit 1 }
Check "old tree ships skills\dept-status and the engineering-lead agent" ((Present (Join-Path $Old 'skills\dept-status\SKILL.md')) -and (Present (Join-Path $Old 'agents\engineering\engineering-lead.md')))

# Old-Install <root> - the OLD installer builds the "old install", then the user edits.
function Old-Install([string]$root) {
    $code = Install-Into $root ($root + '.old.log') $Old @()
    Check "old install.ps1 exit 0 (got $code)" ($code -eq 0)
    Write-Text (Join-Path $root 'skills\my-own\SKILL.md') 'my own skill'
    [System.IO.File]::AppendAllText((Join-Path $root 'skills\dept-status\SKILL.md'), ("`n" + $EditMark + "`n"), $Utf8NoBom)
    Check "old install has the retired files + the edit" ((Present (Join-Path $root 'skills\dept-resume\SKILL.md')) -and (Present (Join-Path $root 'agents\engineering\engineering-lead.md')) -and (Present (Join-Path $root 'agents\specialized\task-executor.md')) -and (Present (Join-Path $root 'runbooks\protocol-registry.md')) -and (Has (Read-Raw (Join-Path $root 'skills\dept-status\SKILL.md')) $EditMark))
}

# Assert-Default <root> <log> - the archive-mode outcome shared by case I and case U.
function Assert-Default([string]$H, [string]$log) {
    Check "unedited skills\dept-resume deleted" (Absent (Join-Path $H 'skills\dept-resume'))
    Check "unedited agents\engineering\engineering-lead.md deleted" (Absent (Join-Path $H 'agents\engineering\engineering-lead.md'))
    Check "unedited agents\specialized\task-executor.md deleted" (Absent (Join-Path $H 'agents\specialized\task-executor.md'))
    Check "unedited runbooks\protocol-registry.md deleted" (Absent (Join-Path $H 'runbooks\protocol-registry.md'))
    Check "edited skills\dept-status no longer in the live tree" (Absent (Join-Path $H 'skills\dept-status\SKILL.md'))
    $arch = Archived-File $H 'skills\dept-status\SKILL.md'
    Check "edited dept-status ARCHIVED under archive\agency-retired-<date>\ (not deleted)" (($null -ne $arch) -and (Has (Read-Raw $arch) $EditMark))
    Check "the 'You changed these' note was printed" (Has (Read-Raw $log) 'You changed these')
    $lg = Read-Raw (Join-Path $H 'logs\agency-retired.log')
    Check "logs\agency-retired.log written" (($lg.Length -gt 0) -and (Has $lg 'dept-status'))
    Check "user skill my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')
    Check "a still-shipped skill is intact (skills\recall)" (Present (Join-Path $H 'skills\recall\SKILL.md'))
}
function Print-Retired([string]$log) {
    foreach ($l in ((Read-Raw $log) -split "`r?`n")) { if ($l -match 'Retired|retired|You changed') { Write-Host "    | $l" } }
}

# -- case I: the current install.ps1 prunes an old install --------------------
Write-Host "case I: install.ps1 removes retired files (no terminal)"
$H = Join-Path $W 'i'
Old-Install $H
$code = Install-Into $H (Join-Path $W 'i.log') $Repo @()
Print-Retired (Join-Path $W 'i.log')
Check "install.ps1 exit 0 (got $code)" ($code -eq 0)
Assert-Default $H (Join-Path $W 'i.log')
$code = Install-Into $H (Join-Path $W 'i2.log') $Repo @()
Check "rerun install.ps1 exit 0 (got $code)" ($code -eq 0)
Check "rerun prints 'Retired files: none to remove'" (Has (Read-Raw (Join-Path $W 'i2.log')) 'Retired files: none to remove')
Check "rerun leaves my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')

Write-Host "case I-delete: install.ps1 -Retired delete also deletes the edited file"
$H = Join-Path $W 'id'
Old-Install $H
$code = Install-Into $H (Join-Path $W 'id.log') $Repo @('-Retired', 'delete')
Check "install.ps1 -Retired delete exit 0 (got $code)" ($code -eq 0)
Check "edited skills\dept-status deleted" (Absent (Join-Path $H 'skills\dept-status\SKILL.md'))
Check "nothing archived for dept-status" ($null -eq (Archived-File $H 'skills\dept-status\SKILL.md'))
Check "unedited skills\dept-resume deleted" (Absent (Join-Path $H 'skills\dept-resume'))
Check "user skill my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')

Write-Host "case I-bogus: install.ps1 -Retired bogus exits 2 before changing anything"
$H = Join-Path $W 'ib'
Old-Install $H
$before = Tree-Sum $H
$code = Install-Into $H (Join-Path $W 'ib.log') $Repo @('-Retired', 'bogus')
$ibLog = Read-Raw (Join-Path $W 'ib.log')
foreach ($l in (($ibLog -split "`r?`n") | Select-Object -First 3)) { if ($l) { Write-Host "    | $l" } }
Check "install.ps1 -Retired bogus exit 2 (got $code)" ($code -eq 2)
Check "the old install is byte-for-byte unchanged" ($before -ceq (Tree-Sum $H))
Check "the message names the bad value" (Has $ibLog 'bogus')

# -- case U: agency upgrade prunes an old install -----------------------------
# `agency upgrade` pulls a git clone and syncs it into AGENCY_HOME, so the code
# under test goes into a scratch bare origin + clone (a copy of the working tree,
# uncommitted files included), as in check-mods-install.ps1 case E.
Write-Host "case U: agency upgrade removes retired files (no terminal)"
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
& git -C $Seed -c core.autocrlf=false add -A 2>&1 | Out-Null
& git -C $Seed -c core.autocrlf=false commit -q -m 'seed: code under test' 2>&1 | Out-Null
& git init -q --bare $Origin 2>&1 | Out-Null
& git -C $Origin symbolic-ref HEAD refs/heads/main 2>&1 | Out-Null
& git -C $Seed remote add origin $Origin 2>&1 | Out-Null
& git -C $Seed push -q origin main 2>&1 | Out-Null
& git -c core.autocrlf=false clone -q $Origin $Clone 2>&1 | Out-Null
Check "scratch clone has install.ps1" (Test-Path (Join-Path $Clone 'install.ps1'))

$H = Join-Path $W 'u'
Old-Install $H
$code = Upgrade-Into $H (Join-Path $W 'u.log') @()
Print-Retired (Join-Path $W 'u.log')
Check "agency upgrade exit 0 (got $code)" ($code -eq 0)
Assert-Default $H (Join-Path $W 'u.log')
$code = Upgrade-Into $H (Join-Path $W 'u2.log') @()
Check "rerun agency upgrade exit 0 (got $code)" ($code -eq 0)
Check "rerun prints 'Retired files: none to remove'" (Has (Read-Raw (Join-Path $W 'u2.log')) 'Retired files: none to remove')
Check "rerun leaves my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')

Write-Host "case U-delete: agency upgrade --retired=delete also deletes the edited file"
$H = Join-Path $W 'ud'
Old-Install $H
$code = Upgrade-Into $H (Join-Path $W 'ud.log') @('--retired=delete')
Check "agency upgrade --retired=delete exit 0 (got $code)" ($code -eq 0)
Check "edited skills\dept-status deleted" (Absent (Join-Path $H 'skills\dept-status\SKILL.md'))
Check "nothing archived for dept-status" ($null -eq (Archived-File $H 'skills\dept-status\SKILL.md'))
Check "user skill my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')

Write-Host "case U-bogus: agency upgrade --retired=bogus exits 2 before changing anything"
$H = Join-Path $W 'ub'
Old-Install $H
$before = Tree-Sum $H
$headBefore = (& git -C $Clone rev-parse HEAD | Out-String).Trim()
$code = Upgrade-Into $H (Join-Path $W 'ub.log') @('--retired=bogus')
foreach ($l in (((Read-Raw (Join-Path $W 'ub.log')) -split "`r?`n") | Select-Object -First 3)) { if ($l) { Write-Host "    | $l" } }
Check "agency upgrade --retired=bogus exit 2 (got $code)" ($code -eq 2)
Check "the old install is byte-for-byte unchanged" ($before -ceq (Tree-Sum $H))
Check "the clone was not touched" ((& git -C $Clone rev-parse HEAD | Out-String).Trim() -eq $headBefore)

# -- legacy git installs ------------------------------------------------------
# The old `git clone <repo> ~/.claude` (and the old rescue.sh) made the Claude root
# itself a git clone of the repo. Such a root is a normal prune target, no -Force.
# A throwaway node file lists the manifest paths still on disk under a root.
$LeftJs = Join-Path $W 'left.js'
Write-Text $LeftJs @'
const fs = require('fs'), p = require('path');
const m = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).paths;
const left = Object.keys(m).filter((x) => fs.existsSync(p.join(process.argv[3], ...x.split('/'))));
console.log(left.length + ' ' + left.slice(0, 5).join(','));
'@
function Left-Count([string]$root) {
    $o = (& node $LeftJs (Join-Path $root 'retired-manifest.json') $root | Out-String).Trim()
    return $o
}
# Legacy-Edit <root> - the user's edit + own skill on top of an old clone
function Legacy-Edit([string]$root) {
    Write-Text (Join-Path $root 'skills\my-own\SKILL.md') 'my own skill'
    [System.IO.File]::AppendAllText((Join-Path $root 'skills\dept-status\SKILL.md'), ("`n" + $EditMark + "`n"), $Utf8NoBom)
}
# Legacy-Clone <dir> <origin url> - a git clone of the code under test, at OldRev
function Legacy-Clone([string]$dir, [string]$url) {
    & git -c core.autocrlf=false clone -q --no-checkout $Repo $dir 2>&1 | Out-Null
    & git -C $dir -c core.autocrlf=false checkout -q --detach $OldRev 2>&1 | Out-Null
    & git -C $dir remote set-url origin $url 2>&1 | Out-Null
}

Write-Host "case L-B: install.ps1 prunes a legacy git clone root with no -Force"
$RUrl = (& git -C $Repo remote get-url origin 2>$null | Out-String).Trim()
if (-not $RUrl) {
    Write-Host "  skip REPO has no origin remote, so a clone of it cannot be told apart from another git root"
} else {
    $H = Join-Path $W 'lb'
    Legacy-Clone $H $RUrl
    Legacy-Edit $H
    & git -C $H ls-files --error-unmatch 'skills/dept-resume/SKILL.md' 2>&1 | Out-Null
    Check "the legacy root is a git clone at $OldRev with the retired files tracked" ($LASTEXITCODE -eq 0)
    $code = Install-Into $H (Join-Path $W 'lb.log') $Repo @()
    Print-Retired (Join-Path $W 'lb.log')
    $lbLog = Read-Raw (Join-Path $W 'lb.log')
    Check "install.ps1 exit 0 (got $code)" ($code -eq 0)
    Check "the legacy install was announced" (Has $lbLog 'Retired files: legacy git install detected')
    Check "no 'git work tree' skip" (-not (Has $lbLog 'is a git work tree'))
    Assert-Default $H (Join-Path $W 'lb.log')
    $code = Install-Into $H (Join-Path $W 'lb2.log') $Repo @()
    Check "rerun install.ps1 exit 0 (got $code)" ($code -eq 0)
    Check "rerun leaves my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')

    Write-Host "case L-B-other: a git root with some other origin is still skipped without -Force"
    $H = Join-Path $W 'lbo'
    Legacy-Clone $H 'https://example.invalid/someone/dotfiles.git'
    Legacy-Edit $H
    $code = Install-Into $H (Join-Path $W 'lbo.log') $Repo @()
    $lboLog = Read-Raw (Join-Path $W 'lbo.log')
    Check "install.ps1 exit 0 (got $code)" ($code -eq 0)
    Check "skipped as a git work tree" (Has $lboLog 'is a git work tree; run: agency prune --force')
    Check "the retired file is still there" (Present (Join-Path $H 'skills\dept-resume\SKILL.md'))
    Check "no legacy announcement" (-not (Has $lboLog 'legacy git install'))
}

Write-Host "case L-A: agency upgrade run from the legacy clone that IS the root"
# OldRev history + the code under test (the working-tree copy in $Seed) as one new
# commit, in a bare origin. The root is a clone of it reset to OldRev, so
# `agency upgrade` pulls the retired-file removal as a legacy user's upgrade would.
$LaSeed = Join-Path $W 'la-seed'; $LaOrigin = Join-Path $W 'origin\la.git'; $H = Join-Path $W 'la'
& git -c core.autocrlf=false clone -q --no-checkout $Repo $LaSeed 2>&1 | Out-Null
& git -C $LaSeed -c core.autocrlf=false checkout -q -b la-main $OldRev 2>&1 | Out-Null
foreach ($item in @(Get-ChildItem -LiteralPath $LaSeed -Force | Where-Object { $_.Name -ne '.git' })) {
    Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
foreach ($item in @(Get-ChildItem -LiteralPath $Seed -Force | Where-Object { $_.Name -ne '.git' })) {
    Copy-Item -LiteralPath $item.FullName -Destination $LaSeed -Recurse -Force
}
& git -C $LaSeed -c core.autocrlf=false add -A 2>&1 | Out-Null
& git -C $LaSeed -c core.autocrlf=false commit -q -m 'seed: code under test' 2>&1 | Out-Null
& git init -q --bare $LaOrigin 2>&1 | Out-Null
& git -C $LaOrigin symbolic-ref HEAD refs/heads/main 2>&1 | Out-Null
& git -C $LaSeed push -q $LaOrigin 'la-main:main' 2>&1 | Out-Null
& git -c core.autocrlf=false clone -q $LaOrigin $H 2>&1 | Out-Null
& git -C $H reset -q --hard $OldRev 2>&1 | Out-Null
Legacy-Edit $H
& git -C $H diff --quiet -- 'skills/dept-status/SKILL.md' 2>&1 | Out-Null
Check "the root is a clone at $OldRev with the edit pending" (($LASTEXITCODE -eq 1) -and ((& git -C $H rev-parse --short HEAD | Out-String).Trim() -eq $OldRev))
$Clone = $H
$code = Upgrade-Into $H (Join-Path $W 'la.log') @()
Print-Retired (Join-Path $W 'la.log')
$laLog = Read-Raw (Join-Path $W 'la.log')
Check "agency upgrade exit 0 (got $code)" ($code -eq 0)
$left = Left-Count $H
Check "no retired manifest path left on disk (tracked or untracked): $left" ($left -like '0*')
Check "the pull removed the tracked retired files" ((Absent (Join-Path $H 'skills\dept-resume')) -and (Absent (Join-Path $H 'agents\engineering\engineering-lead.md')))
$kept = $false
$arch = Join-Path $H 'agents-archive'
if (Test-Path -LiteralPath $arch) {
    foreach ($f in @(Get-ChildItem -LiteralPath $arch -Recurse -File -ErrorAction SilentlyContinue)) {
        if (Has (Read-Raw $f.FullName) $EditMark) { $kept = $true; break }
    }
}
Check "the edited retired file survives at its renamed agents-archive path (no data loss)" $kept
Check "nothing was archived for files git removed" (Absent (Join-Path $H 'archive'))
$sumLines = @(($laLog -split "`r?`n") | Where-Object { $_ -like 'Retired files:*' })
Check "exactly one summary line, 'none to remove' (no double count)" (($sumLines.Count -eq 1) -and ($sumLines[0] -like 'Retired files: none to remove*'))
Check "the root was not skipped as the repo checkout" (-not (Has $laLog 'agency repo checkout itself'))
Check "user skill my-own untouched" ((Read-Raw (Join-Path $H 'skills\my-own\SKILL.md')).Trim() -ceq 'my own skill')
Check "a still-shipped skill is intact (skills\recall)" (Present (Join-Path $H 'skills\recall\SKILL.md'))
$code = Upgrade-Into $H (Join-Path $W 'la2.log') @()
Check "rerun agency upgrade exit 0 (got $code)" ($code -eq 0)
Check "rerun prints 'Retired files: none to remove'" (Has (Read-Raw (Join-Path $W 'la2.log')) 'Retired files: none to remove')

Cleanup
Write-Host ""
if ($script:Fails -eq 0) {
    Write-Host "PASS: check-retired-install ($Repo)"
    exit 0
}
Write-Host "FAIL: check-retired-install - $($script:Fails) check(s) failed ($Repo)"
exit 1

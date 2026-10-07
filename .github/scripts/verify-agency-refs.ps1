# verify-agency-refs.ps1 — Windows twin of verify-agency-refs.sh.
#
# Asserts that every {agency-root}/<tree>/... reference emitted by a DEPLOYED
# agency tree resolves to a real file in that install. install.ps1 shipped none
# of hooks/, runbooks/ or scripts/ before Wave 12, which made every such
# reference dangle on Windows — and nothing caught it, because the installer
# still printed success. This is what catches it now.

param(
    [Parameter(Mandatory = $true)]
    [string]$AgencyRoot
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $AgencyRoot)) { throw "$AgencyRoot is not a directory" }

$trees   = @("runbooks", "hooks", "scripts", "core", "design-system", "agents-archive")
$sources = @("agents", "core", "skills", "runbooks")

$missingTotal = 0

$scanDirs = @()
foreach ($s in $sources) {
    $p = Join-Path $AgencyRoot $s
    if (Test-Path $p) { $scanDirs += $p }
}
if ($scanDirs.Count -eq 0) { throw "no source trees deployed to scan" }

# Read every scanned file once; the per-tree regexes then run in memory.
$corpus = Get-ChildItem -Path $scanDirs -Recurse -File -Include *.md, *.sh, *.py, *.js, *.json -ErrorAction SilentlyContinue |
    ForEach-Object { Get-Content -Raw -ErrorAction SilentlyContinue $_.FullName }

foreach ($tree in $trees) {
    $treePath = Join-Path $AgencyRoot $tree
    if (-not (Test-Path $treePath)) {
        Write-Host "FAIL: deployed tree missing entirely: $tree"
        $missingTotal++
        continue
    }

    # Extension alternation is ordered LONGEST-FIRST, and it must stay that way.
    # .NET regex alternation is leftmost-FIRST: with `js` ahead of `json`, the
    # path `.../brands/neutral.json` matched `js` and captured `neutral.js` — a
    # file that does not exist — so this guard reported a dangling reference for
    # a reference that was perfectly valid. Its twin, verify-agency-refs.sh, uses
    # POSIX ERE via `grep -E`, which is leftmost-LONGEST and matched `json`
    # correctly. So the two scripts silently disagreed: every `.json` reference
    # passed the Linux job and failed the Windows one. The pair only looked like
    # twins because no `{agency-root}/<tree>/....json` reference existed in the
    # tree until wave 18 added one. Keep both lists longest-first so the two
    # engines cannot diverge again.
    $pattern = '(?:\{agency-root\}|~/\.claude)/' + [regex]::Escape($tree) + '/([A-Za-z0-9._/-]+\.(?:json|md|sh|py|js))'
    $refs = @{}
    foreach ($text in $corpus) {
        if (-not $text) { continue }
        foreach ($m in [regex]::Matches($text, $pattern)) {
            $refs[$m.Groups[1].Value] = $true
        }
    }

    $miss = 0
    foreach ($r in $refs.Keys) {
        $target = Join-Path $treePath ($r -replace '/', '\')
        if (-not (Test-Path $target)) {
            Write-Host "MISSING: $tree/$r"
            $miss++
        }
    }
    Write-Host ("  {0}: {1} referenced, {2} missing" -f $tree, $refs.Count, $miss)
    $missingTotal += $miss
}

# The resolver itself must be deployed — every sourcing script silently falls
# back to a degraded root without it.
if (-not (Test-Path (Join-Path $AgencyRoot "hooks\lib\resolve-root.sh"))) {
    Write-Host "FAIL: hooks/lib/resolve-root.sh not deployed"
    $missingTotal++
}

if ($missingTotal -ne 0) {
    throw "$missingTotal dangling reference(s) in the deployed tree at $AgencyRoot"
}

Write-Host "OK: all referenced paths resolve under $AgencyRoot"

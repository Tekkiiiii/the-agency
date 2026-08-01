#!/usr/bin/env bash
# verify-agency-refs.sh — assert that every {agency-root}/<tree>/... reference
# emitted by a DEPLOYED agency tree actually resolves to a file in that install.
#
# This is the check docs/INSTALL-LAYOUT.md describes, lifted out of prose and
# into something CI runs. A bare `ls` does not catch a missing tree; this does,
# because the dangling references are the actual user-visible symptom (a skill
# tells an agent to read {agency-root}/runbooks/x.md and there is no such file).
#
# Usage: verify-agency-refs.sh <agency-root>
set -euo pipefail

ROOT="${1:?usage: verify-agency-refs.sh <agency-root>}"
[ -d "$ROOT" ] || { echo "FAIL: $ROOT is not a directory"; exit 1; }

# Trees that shipped content is allowed to point into.
TREES="runbooks hooks scripts core design-system"
# Trees that are scanned for references.
SOURCES="agents core skills runbooks"

missing_total=0

for tree in $TREES; do
  if [ ! -d "$ROOT/$tree" ]; then
    echo "FAIL: deployed tree missing entirely: $tree"
    missing_total=$((missing_total + 1))
    continue
  fi

  scan_dirs=""
  for s in $SOURCES; do
    [ -d "$ROOT/$s" ] && scan_dirs="$scan_dirs $ROOT/$s"
  done
  [ -n "$scan_dirs" ] || { echo "FAIL: no source trees deployed to scan"; exit 1; }

  # Both placeholder styles the repo uses for a deployed sibling path.
  # shellcheck disable=SC2086
  refs=$(grep -rhoE "(\{agency-root\}|~/\.claude)/$tree/[A-Za-z0-9._/-]+\.(md|sh|py|js|json)" \
           $scan_dirs 2>/dev/null | sed -E "s|.*/$tree/||" | sort -u || true)

  count=0
  miss=0
  while IFS= read -r r; do
    [ -n "$r" ] || continue
    count=$((count + 1))
    if [ ! -f "$ROOT/$tree/$r" ]; then
      echo "MISSING: $tree/$r"
      miss=$((miss + 1))
    fi
  done <<EOF
$refs
EOF

  echo "  $tree: $count referenced, $miss missing"
  missing_total=$((missing_total + miss))
done

# The resolver itself must be deployed — every sourcing script silently falls
# back to a degraded root without it, which is precisely the drift this wave
# exists to remove.
if [ ! -f "$ROOT/hooks/lib/resolve-root.sh" ]; then
  echo "FAIL: hooks/lib/resolve-root.sh not deployed"
  missing_total=$((missing_total + 1))
fi

if [ "$missing_total" -ne 0 ]; then
  echo "FAIL: $missing_total dangling reference(s) in the deployed tree at $ROOT"
  exit 1
fi

echo "OK: all referenced paths resolve under $ROOT"

#!/bin/bash
# mem-find.sh — ranked search across the ~/.claude memory estate.
# Ranking: 1) MEMORY.md/index.md title match  2) frontmatter (name/description/type)
#          3) body grep  4) 1-hop links (links:/[[wikilinks]] from tier 1-3 hits)
# Usage: mem-find.sh <query>
# Portable /bin/bash (macOS bash 3.2) — no associative arrays, no bash4isms.
# Self-logs one mem_find event per invocation (D9) via the standard emit-metric
# path — fire-and-forget, backgrounded so it never adds to search latency (S9).

QUERY="$1"
if [ -z "$QUERY" ]; then
  echo "Usage: mem-find.sh <query>" >&2
  exit 1
fi

CLAUDE_DIR="$HOME/.claude"
( "$CLAUDE_DIR/memory/metrics/emit-metric.sh" \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"mem_find","query_len":'"${#QUERY}"'}' \
  >/dev/null 2>&1 & )
BUNDLES="$CLAUDE_DIR/memory $CLAUDE_DIR/projects/-Users-Tekki--claude/memory"
MEMORY_INDEXES="$CLAUDE_DIR/memory/MEMORY.md $CLAUDE_DIR/projects/-Users-Tekki--claude/memory/MEMORY.md $CLAUDE_DIR/projects/-Users-Tekki--claude/memory/index.md"

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

echo "=== Tier 1: MEMORY.md / index.md title match ==="
FOUND1=0
for f in $MEMORY_INDEXES; do
  [ -f "$f" ] || continue
  hits=$(grep -in -- "$QUERY" "$f")
  if [ -n "$hits" ]; then
    printf '%s\n' "$hits" | sed "s|^|  [$f] |"
    FOUND1=1
  fi
done
[ "$FOUND1" = "0" ] && echo "  (no match)"

echo ""
echo "=== Tier 2: frontmatter match (name/description/type) ==="
FOUND2=0
for d in $BUNDLES; do
  [ -d "$d" ] || continue
  while IFS= read -r f; do
    fm=$(awk '/^---$/{c++; next} c==1' "$f")
    if printf '%s\n' "$fm" | grep -qi -- "$QUERY"; then
      echo "  $f"
      echo "$f" >> "$TMP"
      FOUND2=1
    fi
  done < <(find "$d" -maxdepth 3 -name "*.md" ! -name "MEMORY.md" ! -name "index.md" 2>/dev/null)
done
[ "$FOUND2" = "0" ] && echo "  (no match)"

echo ""
echo "=== Tier 3: body grep ==="
FOUND3=0
for d in $BUNDLES; do
  [ -d "$d" ] || continue
  while IFS= read -r f; do
    if grep -qi -- "$QUERY" "$f" 2>/dev/null && ! grep -qxF "$f" "$TMP" 2>/dev/null; then
      echo "  $f"
      echo "$f" >> "$TMP"
      FOUND3=1
    fi
  done < <(find "$d" -maxdepth 3 -name "*.md" ! -name "MEMORY.md" ! -name "index.md" 2>/dev/null)
done
[ "$FOUND3" = "0" ] && echo "  (no match)"

echo ""
echo "=== Tier 4: 1-hop links from matched files (top 5) ==="
if [ -s "$TMP" ]; then
  while IFS= read -r f; do
    links=$(grep -oE '\[\[[a-zA-Z0-9_-]+\]\]' "$f" 2>/dev/null | tr -d '[]' | sort -u)
    lf=$(awk '/^---$/{c++; next} c==1 && /^links:/' "$f")
    if [ -n "$links" ] || [ -n "$lf" ]; then
      echo "  from $f:"
      [ -n "$links" ] && echo "$links" | sed 's/^/    see also: /'
      [ -n "$lf" ] && echo "    $lf"
    fi
  done < <(sort -u "$TMP" | head -5)
else
  echo "  (no source files to expand)"
fi

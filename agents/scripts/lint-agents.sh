#!/usr/bin/env bash
#
# Validates agent markdown files:
#   1. YAML frontmatter must exist with name and description (ERROR)
#   2. Recommended frontmatter (color) and sections are checked but only warned (WARN)
#   3. File must have meaningful content
#
# Usage: agents/scripts/lint-agents.sh [--verbose] [file ...]
#   WARNs are summarised one line per rule (count + first files); --verbose lists each.
#   Works from any directory (it locates agents/ from its own path).
#   If no files given, scans every department: each agents/<dir>/ that has an
#   INDEX.md, derived from the tree so a new department is linted automatically.
#   Not agent files, so skipped: INDEX/README/CONTRIBUTING docs, memory/
#   (department knowledge notes) and protocols/ (protocol docs).

set -euo pipefail

AGENTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# color is WARN-only: Claude Code treats it as optional and the 2026 agent
# frontmatter (department/role/model) dropped it, so the dept-coords, leads and
# vendored understand-* agents legitimately have none.
REQUIRED_FRONTMATTER=("name" "description")
RECOMMENDED_FRONTMATTER=("color")
RECOMMENDED_SECTIONS=("Identity" "Core Mission" "Critical Rules")

VERBOSE=0
if [[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]]; then
  VERBOSE=1
  shift
fi

errors=0
warnings=0
WARN_LOG="$(mktemp "${TMPDIR:-/tmp}/lint-agents.XXXXXX")"
trap 'rm -f "$WARN_LOG"' EXIT

# warn FILE MESSAGE: count it, print it now (verbose) or log it for the summary.
warn() {
  warnings=$((warnings + 1))
  if [[ $VERBOSE -eq 1 ]]; then
    echo "WARN  $1: $2"
  else
    printf '%s\t%s\n' "$2" "$1" >> "$WARN_LOG"
  fi
}

lint_file() {
  local file="$1"

  # 1. Check frontmatter delimiters
  local first_line
  first_line=$(head -1 "$file")
  if [[ "$first_line" != "---" ]]; then
    echo "ERROR $file: missing frontmatter opening ---"
    errors=$((errors + 1))
    return
  fi

  # Extract frontmatter (between first and second ---)
  local frontmatter
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")

  if [[ -z "$frontmatter" ]]; then
    echo "ERROR $file: empty or malformed frontmatter"
    errors=$((errors + 1))
    return
  fi

  # 2. Check required frontmatter fields
  for field in "${REQUIRED_FRONTMATTER[@]}"; do
    if ! grep -qE "^${field}:" <<<"$frontmatter"; then
      echo "ERROR $file: missing frontmatter field '${field}'"
      errors=$((errors + 1))
    fi
  done
  for field in "${RECOMMENDED_FRONTMATTER[@]}"; do
    if ! grep -qE "^${field}:" <<<"$frontmatter"; then
      warn "$file" "missing recommended frontmatter field '${field}'"
    fi
  done

  # 3. Check recommended sections (warn only)
  local body
  body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$file")

  for section in "${RECOMMENDED_SECTIONS[@]}"; do
    if ! grep -qi "$section" <<<"$body"; then
      warn "$file" "missing recommended section '${section}'"
    fi
  done

  # 4. Check file has meaningful content
  if [[ $(echo "$body" | wc -w) -lt 50 ]]; then
    warn "$file" "body seems very short (< 50 words)"
  fi
}

# Collect files to lint
files=()
if [[ $# -gt 0 ]]; then
  files=("$@")
else
  cd "$AGENTS_DIR"
  for index in */INDEX.md; do
    [[ -f "$index" ]] || continue
    dir="${index%/INDEX.md}"
    while IFS= read -r f; do
      files+=("$f")
    done < <(find "$dir" -name "*.md" -type f \
      ! -name INDEX.md ! -name README.md ! -name CONTRIBUTING.md \
      ! -path "*/memory/*" ! -path "*/protocols/*" | sort)
  done
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No agent files found under ${AGENTS_DIR}."
  exit 1
fi

echo "Linting ${#files[@]} agent files..."
echo ""

for file in "${files[@]}"; do
  lint_file "$file"
done

if [[ -s "$WARN_LOG" ]]; then
  sort "$WARN_LOG" | awk -F'\t' '
    { n[$1]++; if (n[$1] <= 3) ex[$1] = ex[$1] (n[$1] > 1 ? ", " : "") $2; if (!($1 in seen)) { seen[$1] = 1; order[++k] = $1 } }
    END { for (i = 1; i <= k; i++) { m = order[i]; more = n[m] > 3 ? sprintf(" (+%d more)", n[m] - 3) : ""
            printf "WARN  %d file(s): %s -- e.g. %s%s\n", n[m], m, ex[m], more } }'
fi

echo ""
echo "Results: ${errors} error(s), ${warnings} warning(s) in ${#files[@]} files."

if [[ $errors -gt 0 ]]; then
  echo "FAILED: fix the errors above before merging."
  exit 1
else
  echo "PASSED"
  exit 0
fi

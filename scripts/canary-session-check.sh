#!/bin/bash
# canary-session-check.sh — Memory v2 R1 in-session read-path check.
# Companion to canary-check.sh (disk-only). This variant is invoked by a LIVE
# AGENT after it has read ~/.claude/memory/.canary.md via its own Read tool
# (i.e. through the real context/compression pipeline, not a raw disk read).
# The agent pipes exactly the text it saw via stdin; this script hashes it
# and compares to the recorded .canary.sha256, then records the result to
# .canary-session.json so mem-scorecard.py's R1 check can pick it up.
#
# Why this exists: canary-check.sh (disk-based) only proves the FILE is
# intact on disk. It does NOT prove an agent's Read tool call returns that
# same content — a lossy hook/compression layer between disk and context
# would still pass the disk check while silently corrupting what an agent
# actually sees. This is exactly the failure mode a real memory-v2 rollout
# hit in the wild — a compression/proxy layer between disk and context that
# passed disk-level canary checks but corrupted what agents actually read.
#
# Usage: an agent that has just Read()'d .canary.md pipes that exact text in:
#   printf '%s' "$OBSERVED_CONTENT" | scripts/canary-session-check.sh
# macOS bash 3.2 compatible — no bash-4isms.

set -euo pipefail

HASH_FILE="$HOME/.claude/memory/.canary.sha256"
RECORD_FILE="$HOME/.claude/memory/.canary-session.json"
LOG_FILE="$HOME/.claude/memory/metrics/canary-check.log"
EMIT="$HOME/.claude/memory/metrics/emit-metric.sh"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ ! -f "$HASH_FILE" ]; then
  echo "$TS canary_session_check FAIL missing_hash_file" >> "$LOG_FILE"
  exit 1
fi

EXPECTED=$(cat "$HASH_FILE" | tr -d '[:space:]')

# Capture stdin to a temp file rather than a $() var — command substitution
# strips trailing newlines, which would corrupt the hash of a file whose
# content legitimately ends in \n (exactly the bug that bit the first draft
# of this script: observed hash never matched because of stripped trailing
# newlines, not because of any real read-path corruption).
TMP_OBS=$(mktemp)
trap 'rm -f "$TMP_OBS"' EXIT
cat - > "$TMP_OBS"
ACTUAL=$(shasum -a 256 "$TMP_OBS" | awk '{print $1}')

if [ "$EXPECTED" = "$ACTUAL" ]; then
  RESULT="pass"
else
  RESULT="fail"
fi

cat > "$RECORD_FILE" <<EOF
{"ts":"$TS","result":"$RESULT","expected_hash":"$EXPECTED","observed_hash":"$ACTUAL","mechanism":"agent_read_tool"}
EOF

RESULT_UPPER=$(echo "$RESULT" | tr '[:lower:]' '[:upper:]')
echo "$TS canary_session_check $RESULT_UPPER observed=$ACTUAL" >> "$LOG_FILE"
[ -x "$EMIT" ] && "$EMIT" "{\"ts\":\"$TS\",\"event\":\"canary_session_check\",\"result\":\"$RESULT\"}" 2>/dev/null || true

[ "$RESULT" = "pass" ] && exit 0 || exit 1

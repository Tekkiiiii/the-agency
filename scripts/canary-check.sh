#!/bin/bash
# canary-check.sh — Memory v2 R1/R8 read-path integrity check.
# Reads ~/.claude/memory/.canary.md straight off disk, hashes it, and
# compares to the recorded ~/.claude/memory/.canary.sha256. A mismatch
# means something in the read path (hook, proxy, context-optimization
# layer) mutated a memory-path read — file corruption or wrong disk
# state would also trip this, so treat any FAIL as a P0 incident.
# macOS bash 3.2 compatible — no bash-4isms.

set -euo pipefail

CANARY_FILE="$HOME/.claude/memory/.canary.md"
HASH_FILE="$HOME/.claude/memory/.canary.sha256"
LOG_FILE="$HOME/.claude/memory/metrics/canary-check.log"
EMIT="$HOME/.claude/memory/metrics/emit-metric.sh"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ ! -f "$CANARY_FILE" ] || [ ! -f "$HASH_FILE" ]; then
  echo "$TS canary_check FAIL missing_file" >> "$LOG_FILE"
  [ -x "$EMIT" ] && "$EMIT" canary_check result=fail reason=missing_file 2>/dev/null || true
  exit 1
fi

EXPECTED=$(cat "$HASH_FILE" | tr -d '[:space:]')
ACTUAL=$(shasum -a 256 "$CANARY_FILE" | awk '{print $1}')

if [ "$EXPECTED" = "$ACTUAL" ]; then
  echo "$TS canary_check PASS" >> "$LOG_FILE"
  [ -x "$EMIT" ] && "$EMIT" canary_check result=pass 2>/dev/null || true
  exit 0
else
  echo "$TS canary_check FAIL hash_mismatch expected=$EXPECTED actual=$ACTUAL" >> "$LOG_FILE"
  [ -x "$EMIT" ] && "$EMIT" canary_check result=fail reason=hash_mismatch 2>/dev/null || true
  exit 1
fi

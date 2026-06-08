#!/usr/bin/env bash
# emit-metric.sh — Append one event line to the F13-A metrics log.
# Usage: emit-metric.sh '{"event":"save_state","mode":"delta","reads_skipped":4}'
# The script adds "ts" automatically. Safe to call from hooks or agent self-log.
# FAILURE ISOLATION: errors never block the caller (set +e).
set +e

METRICS_FILE="$HOME/.claude/memory/metrics/events.jsonl"
INPUT="${1:-}"

if [ -z "$INPUT" ]; then
  exit 0
fi

python3 -c "
import json, sys, datetime, os

metrics_file = os.path.expanduser('~/.claude/memory/metrics/events.jsonl')
os.makedirs(os.path.dirname(metrics_file), exist_ok=True)

try:
    d = json.loads('$INPUT'.replace(\"'\", '\"'))
except Exception:
    try:
        d = json.loads(sys.argv[1])
    except Exception:
        sys.exit(0)

d['ts'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

with open(metrics_file, 'a') as f:
    f.write(json.dumps(d) + '\n')
" "$INPUT" 2>/dev/null || true

exit 0

#!/usr/bin/env bash
# emit-metric.sh — Append one event line to the F13-A metrics log.
# Usage: emit-metric.sh '{"event":"save_state","mode":"delta","reads_skipped":4}'
# The script adds "ts" automatically. Safe to call from hooks or agent self-log.
# FAILURE ISOLATION: errors never block the caller (set +e).
set +e

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"

METRICS_DIR="$AGENCY_ROOT/memory/metrics"
METRICS_FILE="$METRICS_DIR/events.jsonl"
INPUT="${1:-}"

if [ -z "$INPUT" ]; then
  exit 0
fi

# The directory is created in bash, and python is handed a BARE FILENAME with the
# metrics dir as its cwd — never an absolute path.
#
# Why: on Windows this runs under Git Bash, but `python3` on PATH is usually
# native Windows Python. Handing it the MSYS path `/d/a/_temp/.../events.jsonl`
# fails — that path means nothing to a win32 interpreter — and because this
# script is fire-and-forget (set +e, stderr muted) the failure was invisible:
# every metric emitted from a Windows install silently went nowhere. A relative
# filename needs no path translation and is correct on every platform.
mkdir -p "$METRICS_DIR" 2>/dev/null || true

( cd "$METRICS_DIR" 2>/dev/null || exit 0
  python3 -c "
import json, sys, datetime

try:
    d = json.loads('$INPUT'.replace(\"'\", '\"'))
except Exception:
    try:
        d = json.loads(sys.argv[1])
    except Exception:
        sys.exit(0)

d['ts'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

with open('events.jsonl', 'a') as f:
    f.write(json.dumps(d) + '\n')
" "$INPUT" 2>/dev/null || true
)

exit 0

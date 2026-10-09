#!/usr/bin/env bash
# reconcile-stale-spawns.sh — closes stale spawn_start records that never received
# a spawn_end. Root cause: completion can be lost two ways —
#   (1) the automatic PostToolUse hook (spawn-completion.sh) genuinely never fires
#       because the spawning session was killed/crashed/hit a usage limit before
#       the Agent tool call returned, and
#   (2) the separate "agent-instrumented" manual convention (log-spawn-from-agent.sh
#       / log-spawn-end-from-agent.sh, called directly by Coord/PD bash steps) skips
#       its own after-call because that convention depends on the calling LLM
#       remembering a second, later, explicit step — this accounts for the large
#       majority of the gap (~81% in the audited sample) and cannot be guaranteed
#       fixed at the hook level since it isn't a hook at all.
# Neither failure mode can be prevented with certainty at write time, so this sweep
# makes the gap a KNOWN state instead of a silent one: any spawn_start with no
# spawn_end after SPAWN_STALE_THRESHOLD_SEC gets an explicit synthetic spawn_end
# with outcome "ABANDONED" and source "reconciliation-sweep".
#
# APPEND-ONLY — never rewrites, deletes, or reorders existing lines. Idempotent —
# a spawn_id that already has ANY spawn_end (real or previously reconciled) is
# never touched again, because that end record is what future runs check against.
# Throttled via a sibling ".reconcile-marker" file so real work happens at most
# once per SPAWN_RECONCILE_INTERVAL_SEC (default 900s) per log file — safe to call
# from a hot hook path on every spawn event.
#
# C4: the ABANDONED row copies agent_type and model (launched.resolved_model when the start row
# only says inherit/unknown) from the spawn it closes, and marks the unknowable cost as cost_usd 0.0 +
# cost_source "unavailable". Nothing is recomputed; the real cost of an abandoned spawn is not recoverable here.
#
# Usage: bash reconcile-stale-spawns.sh /path/to/spawns.jsonl
#
# FAILURE ISOLATION: fire-and-forget. Never blocks, never exits non-zero to the
# caller, never raises to stderr in a way that would surface in hook output.
set +e

LOG_FILE="${1:-}"
if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
  exit 0
fi

STALE_THRESHOLD_SEC="${SPAWN_STALE_THRESHOLD_SEC:-21600}"      # 6h default
RECONCILE_INTERVAL_SEC="${SPAWN_RECONCILE_INTERVAL_SEC:-900}"  # 15min default

MARKER="${LOG_FILE}.reconcile-marker"

# Throttle: skip if marker was touched within RECONCILE_INTERVAL_SEC.
if [ -f "$MARKER" ]; then
  NOW_EPOCH=$(date +%s 2>/dev/null || echo 0)
  MARKER_EPOCH=$(stat -f %m "$MARKER" 2>/dev/null || stat -c %Y "$MARKER" 2>/dev/null || echo 0)
  AGE=$((NOW_EPOCH - MARKER_EPOCH))
  if [ "$AGE" -lt "$RECONCILE_INTERVAL_SEC" ] 2>/dev/null; then
    exit 0
  fi
fi

# Touch marker before doing work so a slow/duplicate concurrent invocation
# doesn't double-run the sweep in the same window.
touch "$MARKER" 2>/dev/null || true

# Same idiom as hooks/emit-metric.sh (Wave 13): cd into the log's directory and hand
# python only its bare filename, so no absolute (possibly MSYS-style) path crosses the
# bash -> python3 boundary on Windows.
LOG_DIR=$(dirname "$LOG_FILE")
LOG_BASE=$(basename "$LOG_FILE")

( cd "$LOG_DIR" 2>/dev/null || exit 0
python3 -c '
import sys, json, re
from datetime import datetime

log_file = sys.argv[1]
stale_threshold = int(sys.argv[2])

try:
    with open(log_file) as f:
        lines = f.readlines()
except Exception:
    sys.exit(0)

starts = {}
has_end = set()
launched_model = {}

for line in lines:
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
    except Exception:
        continue
    ev = e.get("event")
    sid = e.get("spawn_id")
    if not sid:
        continue
    if ev == "spawn_start":
        starts[sid] = e
    elif ev == "spawn_end":
        has_end.add(sid)
    elif ev == "spawn_launched" and e.get("resolved_model"):
        launched_model[sid] = re.sub(r"\[[^\]]*\]$", "", e["resolved_model"])

try:
    now = datetime.now().astimezone()
except Exception:
    sys.exit(0)

new_lines = []
for sid, s in starts.items():
    if sid in has_end:
        continue
    ts_raw = s.get("ts", "")
    try:
        start_dt = datetime.fromisoformat(ts_raw)
    except Exception:
        continue
    try:
        age = (now - start_dt).total_seconds()
    except Exception:
        continue
    if age < stale_threshold:
        continue
    smodel = (s.get("model") or "").strip()
    if smodel in ("", "inherit", "unknown") and sid in launched_model:
        model, model_source = launched_model[sid], "launched"
    elif smodel:
        model, model_source = smodel, s.get("model_source") or "start"
    else:
        model, model_source = "unknown", "unavailable"
    entry = {
        "event": "spawn_end",
        "spawn_id": sid,
        "tool_use_id": s.get("tool_use_id", ""),
        "outcome": "ABANDONED",
        "agent_type": s.get("subagent_type", "") or s.get("child_agent", ""),
        "model": model,
        "model_source": model_source,
        "duration_ms": 0,
        "tokens": 0,
        "tool_uses": 0,
        "cost_usd": 0.0,
        "cost_source": "unavailable",
        "summary_excerpt": "reconciliation-sweep: no spawn_end recorded within %ds of spawn_start" % stale_threshold,
        "ts": now.isoformat(timespec="seconds"),
        "source": "reconciliation-sweep"
    }
    new_lines.append(json.dumps(entry))

if new_lines:
    try:
        with open(log_file, "a") as f:
            for l in new_lines:
                f.write(l + "\n")
    except Exception:
        pass
' "$LOG_BASE" "$STALE_THRESHOLD_SEC" 2>/dev/null || true
)

exit 0

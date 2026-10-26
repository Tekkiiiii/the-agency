#!/usr/bin/env bash
# cost-tracker.sh — Stop hook
# Reads the session transcript JSONL, computes cumulative token usage and cost.
# Appends one row per Stop to {agency-root}/metrics/costs.jsonl.
# Rates + transcript parsing live in hooks/lib/claude_pricing.py (single source;
# verified live 2026-10-05). Usage is deduplicated by message.id and priced per
# model (a session that switches models is priced per message, not by the last
# model seen). Subagent transcripts are NOT included here.
set -euo pipefail

. "$(dirname "${BASH_SOURCE[0]:-$0}")/lib/resolve-root.sh" 2>/dev/null || AGENCY_ROOT="${AGENCY_HOME:-$HOME/.claude}"
HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/lib" && pwd)"

INPUT=$(cat)

TRANSCRIPT=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json,os
d=json.loads(sys.stdin.read())
print(d.get("transcript_path","") or os.environ.get("CLAUDE_TRANSCRIPT_PATH",""))' 2>/dev/null || true)

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

mkdir -p "$AGENCY_ROOT/metrics"
METRICS_FILE="$AGENCY_ROOT/metrics/costs.jsonl"
# Fixed path, overwritten every run: bounded by construction, and whatever the
# last failure printed is still there to read.
COST_ERR="$AGENCY_ROOT/metrics/.cost-tracker.err"

# Same idiom as hooks/emit-metric.sh (Wave 13, 3383ea9): no absolute path crosses
# the bash -> python3 boundary, since a Windows box's native python3 cannot open
# an MSYS-style path like /d/a/_temp/foo/transcript.jsonl. Bash cd's into
# hooks/lib (so `import claude_pricing` resolves from the cwd) and hands the
# transcript to python on stdin (native bash redirection, no path translation);
# python reads it as fd 0. python prints the computed row (JSON) to stdout and
# the diagnostic cost line to stderr; bash appends stdout to METRICS_FILE.
ROW=$( cd "$HOOK_LIB" 2>/dev/null || exit 0
python3 -c "
import json, sys
from datetime import datetime, timezone
from claude_pricing import usage_from_transcript, rate_for

try:
    u = usage_from_transcript(0)
except Exception:
    sys.exit(0)
t = u['totals']
if t['input'] == 0 and t['output'] == 0:
    sys.exit(0)

# Primary model = the one with the most output tokens.
primary = max(u['by_model'].items(), key=lambda kv: kv[1]['output'])[0] if u['by_model'] else 'unknown'
rt, src = rate_for(primary)
row = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'session_id': u['session_id'],
    'model': primary,
    'rate_label': rt['label'],
    'rate_source': src,
    'input_tokens': t['input'],
    'output_tokens': t['output'],
    'cache_write_tokens': t['cache_write_5m'] + t['cache_write_1h'],
    'cache_write_5m_tokens': t['cache_write_5m'],
    'cache_write_1h_tokens': t['cache_write_1h'],
    'cache_read_tokens': t['cache_read'],
    'by_model': {m: b['cost_usd'] for m, b in u['by_model'].items()},
    'estimated_cost_usd': t['cost_usd'],
    'pricing_version': '2026-10-05',
}

# Print the row to stdout (captured by bash into ROW below) rather than writing
# it here: this python process's cwd is hooks/lib, not AGENCY_ROOT/metrics.
print(json.dumps(row))

print(f\"Session cost: \${t['cost_usd']:.4f} ({t['input']/1000:.0f}k in, {t['output']/1000:.0f}k out, \"
      f\"{t['cache_read']/1000:.0f}k cache-read, {rt['label']})\", file=sys.stderr)
" < "$TRANSCRIPT" 2>"$COST_ERR"
) || true

# The python block above prints "Session cost: ..." to stderr on purpose — it is
# the only thing this hook ever shows a human. stderr goes to a fixed,
# overwritten file (self-bounding, and still inspectable after a failure) and
# only the intended line is re-emitted. A traceback stays out of the UI: failure
# isolation was the point of the suppression, and it is preserved.
grep -m1 '^Session cost:' "$COST_ERR" >&2 2>/dev/null || true

if [ -n "$ROW" ]; then
  printf '%s\n' "$ROW" >> "$METRICS_FILE" 2>/dev/null || true
fi

exit 0

#!/usr/bin/env bash
# cost-tracker.sh — Stop hook
# Reads transcript JSONL, computes cumulative token usage and estimated cost.
# Appends one row per Stop to ~/.claude/metrics/costs.jsonl.
set -euo pipefail

INPUT=$(cat)

TRANSCRIPT=$(printf '%s' "$INPUT" | python3 -c \
  'import sys,json,os
d=json.loads(sys.stdin.read())
print(d.get("transcript_path","") or os.environ.get("CLAUDE_TRANSCRIPT_PATH",""))' 2>/dev/null || true)

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

mkdir -p "$HOME/.claude/metrics"

python3 -c "
import json, os, sys
from datetime import datetime, timezone

transcript = '$TRANSCRIPT'
metrics_file = os.path.expanduser('~/.claude/metrics/costs.jsonl')

rates = {
    'haiku':  {'input': 0.80, 'output': 4.00, 'cache_write': 1.00, 'cache_read': 0.08},
    'sonnet': {'input': 3.00, 'output': 15.00, 'cache_write': 3.75, 'cache_read': 0.30},
    'opus':   {'input': 15.00, 'output': 75.00, 'cache_write': 18.75, 'cache_read': 1.50},
}

input_tokens = 0
output_tokens = 0
cache_write = 0
cache_read = 0
model = 'unknown'
session_id = ''

try:
    with open(transcript) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except:
                continue

            if entry.get('type') == 'assistant':
                msg = entry.get('message', {})
                usage = msg.get('usage', {})
                input_tokens += usage.get('input_tokens', 0)
                output_tokens += usage.get('output_tokens', 0)
                cache_write += usage.get('cache_creation_input_tokens', 0)
                cache_read += usage.get('cache_read_input_tokens', 0)
                m = msg.get('model', '')
                if m and m != 'unknown':
                    model = m

            if not session_id:
                session_id = entry.get('session_id', entry.get('sessionId', ''))
except Exception as e:
    sys.exit(0)

if input_tokens == 0 and output_tokens == 0:
    sys.exit(0)

tier = 'sonnet'
model_lower = model.lower()
if 'haiku' in model_lower:
    tier = 'haiku'
elif 'opus' in model_lower:
    tier = 'opus'

r = rates[tier]
cost = (
    (input_tokens / 1_000_000) * r['input'] +
    (output_tokens / 1_000_000) * r['output'] +
    (cache_write / 1_000_000) * r['cache_write'] +
    (cache_read / 1_000_000) * r['cache_read']
)

row = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'session_id': session_id,
    'model': model,
    'input_tokens': input_tokens,
    'output_tokens': output_tokens,
    'cache_write_tokens': cache_write,
    'cache_read_tokens': cache_read,
    'estimated_cost_usd': round(cost, 4),
}

with open(metrics_file, 'a') as f:
    f.write(json.dumps(row) + '\n')

in_k = input_tokens / 1000
out_k = output_tokens / 1000
print(f'Session cost: \${cost:.4f} ({in_k:.0f}k in, {out_k:.0f}k out, {tier})', file=sys.stderr)
" 2>/dev/null || true

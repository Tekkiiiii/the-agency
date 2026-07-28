#!/bin/bash
# bos.sh — thin BrowserOS MCP wrapper (JSON-RPC tools/call over StreamableHTTP)
# ponytail: temp shim until browseros-cli matches the stable app server (brew 0.48+); then delete.
# Usage: bos.sh <tool> ['<json-args>']
#   bos.sh tabs '{"action":"list"}'
#   bos.sh navigate '{"url":"https://example.com","newTab":true}'
#   bos.sh snapshot '{"tabId":2}'
#   bos.sh read '{"tabId":2}'
# Tool list: bos.sh --tools
set -euo pipefail
URL="${BROWSEROS_URL:-http://127.0.0.1:9000/mcp}"
if [ "${1:-}" = "--tools" ]; then
  curl -s -m 10 -X POST "$URL" -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' |
    python3 -c "import sys,json;[print(t['name'],'-',t.get('description','')[:80]) for t in json.load(sys.stdin)['result']['tools']]"
  exit 0
fi
TOOL="${1:?tool name required}"; ARGS="${2:-{\}}"
python3 - "$TOOL" "$ARGS" <<'EOF' > /tmp/bos-req.json
import sys, json
print(json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call",
  "params":{"name":sys.argv[1],"arguments":json.loads(sys.argv[2])}}))
EOF
curl -s -m 60 -X POST "$URL" -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data @/tmp/bos-req.json |
  python3 -c "
import sys, json
r = json.load(sys.stdin)
if 'error' in r: print('ERROR:', r['error'].get('message', r['error'])); sys.exit(1)
for c in r.get('result', {}).get('content', []):
    print(c.get('text', c))"

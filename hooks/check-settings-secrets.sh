#!/usr/bin/env bash
# check-settings-secrets.sh — SessionStart hook
# Warns if settings.json has plaintext secrets in env blocks. Non-blocking.
set -euo pipefail

SETTINGS="$HOME/.claude/settings.json"
[ -f "$SETTINGS" ] || exit 0

COUNT=$(python3 -c "
import json, re
try:
    d = json.load(open('$SETTINGS'))
    count = 0
    for srv in d.get('mcpServers', {}).values():
        for v in srv.get('env', {}).values():
            s = str(v)
            if re.search(r'eyJ[A-Za-z0-9_-]{50,}', s):
                count += 1
            elif re.search(r'[a-fA-F0-9]{48,}', s):
                count += 1
    print(count)
except:
    print(0)
" 2>/dev/null || echo 0)

if [ "$COUNT" -gt 0 ]; then
  echo "SECURITY: settings.json has $COUNT plaintext token(s) in mcpServers env blocks." >&2
  echo "  Consider moving to keychain: security add-generic-password -s '<svc>' -a '<user>' -w '<token>'" >&2
fi

#!/usr/bin/env bash
# write-evidence.sh — PostToolUse/Write+Edit hook (F12)
# Purpose: Log write evidence for deliverable files (html, pdf, md plans, reports).
# On every Write/Edit targeting outputs/, plans/, reports/, or *.html paths:
#   - emit write_evidence event to events.jsonl
#   - stat the file and record actual byte count
# Provides a paper trail for the fabrication guard: if a file was claimed DONE,
# there must be a write_evidence entry with non-zero bytes.
#
# FAILURE ISOLATION: any internal error is silent — hook never blocks writes.
set +e

INPUT=$(cat)

python3 - <<'PYEOF'
import sys, json, os, re
from datetime import datetime

def is_deliverable_path(path):
    """True if the path looks like a plan/report/output deliverable."""
    deliverable_dirs = ['/outputs/', '/plans/', '/reports/', '/qa/']
    deliverable_exts = re.compile(r'\.(html|htm|pdf|docx|pptx|xlsx)$', re.IGNORECASE)
    for d in deliverable_dirs:
        if d in path:
            return True
    return bool(deliverable_exts.search(path))

try:
    import sys as _sys
    raw_input = sys.stdin.read() if not _sys.argv[1:] else _sys.argv[1]
except:
    raw_input = ""

try:
    # Read from stdin (hook input is stdin, not argv)
    import io
    raw_input = open('/dev/stdin', 'r').read() if not raw_input else raw_input
except:
    pass

try:
    d = json.loads(raw_input)
    tool_name = d.get("tool_name", "")
    tool_input = d.get("tool_input", {})

    # Get the file path being written/edited
    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        sys.exit(0)

    # Expand ~ if present
    home = os.path.expanduser("~")
    if file_path.startswith("~/"):
        file_path = os.path.join(home, file_path[2:])

    if not is_deliverable_path(file_path):
        sys.exit(0)

    # Stat the file (after write completed, file should exist)
    file_size = -1
    if os.path.isfile(file_path):
        file_size = os.path.getsize(file_path)

    # Emit write_evidence event
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "ts": ts,
        "event": "write_evidence",
        "tool": tool_name,
        "path": file_path,
        "bytes": file_size,
        "exists": file_size >= 0,
    }

    log_dir = os.path.join(home, ".claude", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "write-evidence.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Also emit to events.jsonl via metrics script for queryability
    # (fire-and-forget subprocess)
    import subprocess
    metrics_script = os.path.join(home, ".claude", "memory", "metrics", "emit-metric.sh")
    if os.path.isfile(metrics_script):
        payload = json.dumps({
            "ts": ts,
            "event": "write_evidence",
            "path": file_path,
            "bytes": file_size,
        })
        subprocess.Popen(
            ["bash", metrics_script, payload],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

except Exception:
    # Silent failure — never block writes
    pass

sys.exit(0)
PYEOF
exit 0

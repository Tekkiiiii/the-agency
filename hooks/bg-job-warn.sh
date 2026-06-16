#!/usr/bin/env bash
# bg-job-warn.sh — PostToolUse/Bash hook
# Purpose: Track fire-and-forget background jobs and warn when session ends
# with un-awaited background commands.
#
# HOW IT WORKS:
# 1. On every Bash tool call with run_in_background: true, log the command
#    to ~/.claude/.pending-bg-jobs.jsonl (session-scoped).
# 2. On every Bash tool result, if the output says "Command running in
#    background with ID:", record that ID.
# 3. On Stop (see session-end.sh), if .pending-bg-jobs.jsonl is non-empty,
#    emit a WARNING visible to the parent agent.
#    (session-end.sh sources this file's companion: bg-job-warn-stop.sh)
#
# FAILURE ISOLATION: any internal error is silent.
set +e

INPUT=$(cat)
BG_JOB_FILE="$HOME/.claude/.pending-bg-jobs.jsonl"

python3 - "$INPUT" "$BG_JOB_FILE" <<'PYEOF'
import sys, json, os, re
from datetime import datetime

try:
    raw_input = sys.argv[1]
    bg_job_file = sys.argv[2]

    d = json.loads(raw_input)
    hook_type = d.get("hook_event_name", "PostToolUse")

    # ---- PostToolUse: detect run_in_background in tool_input ----
    tool_input = d.get("tool_input", {})
    tool_response = d.get("tool_response", {})

    is_bg = tool_input.get("run_in_background", False)
    if not is_bg:
        sys.exit(0)

    command = tool_input.get("command", "")[:300]
    description = tool_input.get("description", "")[:200]

    # Extract bg job ID from response if available
    bg_id = ""
    response_text = ""
    if isinstance(tool_response, dict):
        content = tool_response.get("content", "")
        if isinstance(content, list):
            parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            response_text = "\n".join(parts)
        else:
            response_text = str(content)
    elif isinstance(tool_response, str):
        response_text = tool_response

    m = re.search(r'running in background with ID:\s*(\S+)', response_text, re.IGNORECASE)
    if m:
        bg_id = m.group(1)

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    entry = {
        "ts": ts,
        "bg_id": bg_id,
        "command": command,
        "description": description,
        "resolved": False,
    }

    os.makedirs(os.path.dirname(bg_job_file), exist_ok=True)
    with open(bg_job_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Warn immediately when a heavy render/mux command fires in background
    RENDER_SIGNALS = ["render", "ffmpeg", "bun run", "npm run build", "make ", "cargo build", "go build"]
    cmd_lower = command.lower()
    if any(sig in cmd_lower for sig in RENDER_SIGNALS):
        print(f"\n[bg-job-warn] {ts} BACKGROUND RENDER/BUILD DETECTED", flush=True)
        print(f"[bg-job-warn] Command: {command[:120]}", flush=True)
        if bg_id:
            print(f"[bg-job-warn] Background ID: {bg_id}", flush=True)
        print("[bg-job-warn] RULE: You MUST await this job and test -f the output before reporting DONE.", flush=True)
        print("[bg-job-warn] Do not proceed to summary until you verify the artifact exists on disk.", flush=True)
        print("", flush=True)

except Exception:
    pass

sys.exit(0)
PYEOF
exit 0

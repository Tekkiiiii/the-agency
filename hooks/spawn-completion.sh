#!/usr/bin/env bash
# spawn-completion.sh — PostToolUse/Agent hook (spawn completion emitter)
# Appends one spawn_end JSONL line per agent completion.
# FAILURE ISOLATION: errors are always silent — hook never raises exceptions.
set +e

PROFILE=$(cat "$HOME/.claude/.hook-profile" 2>/dev/null | tr -d '[:space:]' || echo "standard")
if [ "$PROFILE" = "minimal" ]; then
  exit 0
fi

INPUT=$(cat)

# Resolve project log file
if [ -f "$HOME/.claude/hooks/lib/resolve-project.sh" ]; then
  source "$HOME/.claude/hooks/lib/resolve-project.sh" 2>/dev/null || true
  resolve_project_path 2>/dev/null || true
fi

if [ -z "${SPAWN_LOG_FILE:-}" ]; then
  mkdir -p "$HOME/.claude/logs" 2>/dev/null || true
  SPAWN_LOG_FILE="$HOME/.claude/logs/spawns.jsonl"
fi

# Parse completion data and write spawn_end entry — pass INPUT as argv to avoid stdin conflict
python3 -c '
import sys, json, os, re
from datetime import datetime

def find_spawn_id(log_file, tool_use_id):
    """Walk log file backwards to find spawn_start matching tool_use_id."""
    if not os.path.exists(log_file):
        return ""
    try:
        with open(log_file) as f:
            lines = f.readlines()
        for line in reversed(lines):
            try:
                entry = json.loads(line.strip())
                if (entry.get("event") == "spawn_start" and
                        entry.get("tool_use_id") == tool_use_id):
                    return entry.get("spawn_id", "")
            except Exception:
                continue
    except Exception:
        pass
    return ""

def detect_outcome(content):
    """Scan agent output for outcome markers."""
    if not content:
        return "UNKNOWN"
    text = str(content).upper()
    if "KILLED" in text:
        return "KILLED"
    if "BLOCKED:" in text or "STATUS: BLOCKED" in text or ": BLOCKED" in text or "— BLOCKED" in text:
        return "BLOCKED"
    if "ESCALATE:" in text or "STATUS: ESCALATE" in text or ": ESCALATE" in text or "— ESCALATE" in text:
        return "ESCALATE"
    if "DONE" in text or "COMPLETE" in text or "SAVE-STATE DONE" in text:
        return "DONE"
    return "UNKNOWN"

def parse_usage(content):
    """Extract token counts, tool_uses, and duration_ms from agent output.

    The Agent tool result uses a <usage> block with colon-separated key:value pairs:
      <usage>subagent_tokens: N
      tool_uses: N
      duration_ms: N</usage>

    We also handle JSON-encoded usage blocks as a fallback.
    """
    tokens = 0
    tool_uses = 0
    duration_ms = 0
    if not content:
        return tokens, tool_uses, duration_ms

    text = str(content)

    # Primary: <usage>...</usage> block with key: value pairs
    usage_block = re.search(r"<usage>(.*?)</usage>", text, re.DOTALL)
    if usage_block:
        block = usage_block.group(1)
        m = re.search(r"subagent_tokens:\s*(\d+)", block)
        if m:
            tokens = int(m.group(1))
        m = re.search(r"tool_uses:\s*(\d+)", block)
        if m:
            tool_uses = int(m.group(1))
        m = re.search(r"duration_ms:\s*(\d+)", block)
        if m:
            duration_ms = int(m.group(1))
        if tokens > 0 or tool_uses > 0 or duration_ms > 0:
            return tokens, tool_uses, duration_ms

    # Fallback: XML-like individual tags (older format)
    m = re.search(r"<subagent_tokens>(\d+)</subagent_tokens>", text)
    if m:
        tokens = int(m.group(1))
    m = re.search(r"<tool_uses>(\d+)</tool_uses>", text)
    if m:
        tool_uses = int(m.group(1))
    m = re.search(r"<duration_ms>(\d+)</duration_ms>", text)
    if m:
        duration_ms = int(m.group(1))
    if tokens > 0:
        return tokens, tool_uses, duration_ms

    # Fallback: JSON-encoded usage block
    try:
        d = json.loads(text)
        usage = d.get("usage", {})
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        tool_uses = d.get("tool_uses", tool_uses)
        if tokens > 0:
            return tokens, tool_uses, duration_ms
    except Exception:
        pass

    # Fallback: JSON key pattern scan
    matches = re.findall(r"\"(?:input|output)_tokens\":\s*(\d+)", text)
    for m in matches:
        tokens += int(m)

    return tokens, tool_uses, duration_ms

try:
    raw_input = sys.argv[1]
    log_file = sys.argv[2]

    d = json.loads(raw_input)
    tool_use_id = d.get("tool_use_id", "")
    tool_response = d.get("tool_response", {})

    # Find matching spawn_start entry
    spawn_id = find_spawn_id(log_file, tool_use_id)

    # Extract content and outcome
    # tool_response.content is a list of content blocks: [{'type': 'text', 'text': '...'}]
    content = ""
    if isinstance(tool_response, dict):
        raw_content = tool_response.get("content", "")
        if isinstance(raw_content, list):
            # Extract text from all text blocks
            parts = []
            for block in raw_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            content = "\n".join(parts)
        elif isinstance(raw_content, str):
            content = raw_content
        else:
            content = str(raw_content)
    elif isinstance(tool_response, str):
        content = tool_response

    outcome = detect_outcome(content)
    tokens, tool_uses, duration_ms = parse_usage(content)

    # Summary excerpt
    summary_excerpt = content[:300] if content else ""

    # Timestamp
    ts = datetime.now().astimezone().isoformat(timespec="seconds")

    entry = {
        "event": "spawn_end",
        "spawn_id": spawn_id,
        "tool_use_id": tool_use_id,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "tokens": tokens,
        "tool_uses": tool_uses,
        "summary_excerpt": summary_excerpt,
        "ts": ts
    }

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

except Exception:
    pass
' "$INPUT" "$SPAWN_LOG_FILE" 2>/dev/null || true

exit 0

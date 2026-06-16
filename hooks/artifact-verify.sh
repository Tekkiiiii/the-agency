#!/usr/bin/env bash
# artifact-verify.sh — PostToolUse/Agent hook
# Purpose: Catch fabricated "build complete" claims.
# After every agent completes, scan its output for:
#   (a) a completion signal (DONE / COMPLETE / SUCCESS / BUILD COMPLETE)
#   (b) a file path that looks like a deliverable (mp4, pdf, html, png, jpg, wav, mp3, zip, json, csv)
# Then test -f each claimed path. If any claimed file is missing, emit a WARNING
# into hook stderr so the parent agent sees it before relaying to the user.
#
# This is the harness-level backstop — it fires even when the agent ignores
# prompt-level "verify before reporting done" instructions.
#
# FAILURE ISOLATION: any internal error is silent — hook never blocks agent.
set +e

INPUT=$(cat)

python3 - "$INPUT" <<'PYEOF'
import sys, json, re, os
from datetime import datetime

def extract_text(tool_response):
    """Extract plain text from tool_response content block."""
    if isinstance(tool_response, dict):
        raw = tool_response.get("content", "")
        if isinstance(raw, list):
            parts = []
            for block in raw:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)
        return str(raw)
    return str(tool_response)

def has_completion_signal(text):
    """True if the agent output claims something is complete/done."""
    upper = text.upper()
    signals = [
        "BUILD COMPLETE", "DONE", "COMPLETE", "SUCCESS", "FINISHED",
        "FILE READY", "RENDER COMPLETE", "OUTPUT READY", "SHIPPED",
        "FULLY COMPLETE", "TASK COMPLETE", "ALL DONE", "SAVE-STATE DONE",
    ]
    return any(s in upper for s in signals)

# Deliverable file extensions — media, documents, archives, data
DELIVERABLE_EXTS = re.compile(
    r'\.(mp4|mp3|wav|aac|ogg|flac|'
    r'pdf|html|htm|docx|xlsx|pptx|'
    r'png|jpg|jpeg|gif|webp|svg|'
    r'zip|tar\.gz|tgz|'
    r'json|csv|'
    r'wasm|exe|dmg|pkg|deb|rpm)(?:\s|$|["\']|,|\))',
    re.IGNORECASE
)

def extract_file_paths(text):
    """
    Extract candidate file paths that look like deliverable files.
    Heuristic: find tokens that contain / or ~ and end with a known extension.
    """
    paths = set()

    # Pattern 1: absolute or home-relative paths with deliverable extensions
    abs_paths = re.findall(
        r'(?:^|[\s`"\'])(/[^\s"\'<>(){}|,;]+\.' +
        r'(?:mp4|mp3|wav|aac|ogg|flac|pdf|html|htm|docx|xlsx|pptx|'
        r'png|jpg|jpeg|gif|webp|svg|zip|json|csv|wasm|exe|dmg))'
        r'(?=[\s"\'<>(){}|,;]|$)',
        text, re.IGNORECASE | re.MULTILINE
    )
    paths.update(abs_paths)

    # Pattern 2: ~/... paths
    home_paths = re.findall(
        r'(~/[^\s"\'<>(){}|,;]+\.' +
        r'(?:mp4|mp3|wav|aac|ogg|flac|pdf|html|htm|docx|xlsx|pptx|'
        r'png|jpg|jpeg|gif|webp|svg|zip|json|csv|wasm|exe|dmg))'
        r'(?=[\s"\'<>(){}|,;]|$)',
        text, re.IGNORECASE | re.MULTILINE
    )
    paths.update(home_paths)

    # Pattern 3: relative paths mentioned near "out/", "output/", "dist/", "build/"
    rel_paths = re.findall(
        r'(?:out|output|dist|build|exports?|rendered?|final)/'
        r'[^\s"\'<>(){}|,;]+\.' +
        r'(?:mp4|mp3|wav|aac|pdf|html|png|jpg|zip|json|csv)',
        text, re.IGNORECASE
    )
    paths.update(rel_paths)

    return paths

def resolve_path(p, home):
    """Expand ~ and return absolute path if possible."""
    if p.startswith("~/"):
        return os.path.join(home, p[2:])
    if p.startswith("/"):
        return p
    return None  # relative paths can't be checked without cwd

try:
    raw_input = sys.argv[1]
    d = json.loads(raw_input)
    tool_response = d.get("tool_response", {})
    text = extract_text(tool_response)

    if not has_completion_signal(text):
        sys.exit(0)

    paths = extract_file_paths(text)
    if not paths:
        sys.exit(0)

    home = os.path.expanduser("~")
    missing = []
    found = []

    for p in paths:
        abs_p = resolve_path(p.strip(), home)
        if abs_p is None:
            continue  # skip unresolvable relative paths
        if os.path.isfile(abs_p):
            found.append(abs_p)
        else:
            missing.append(abs_p)

    if not missing:
        sys.exit(0)

    # Emit structured warning visible to parent agent
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    print(f"\n[artifact-verify] {ts} ARTIFACT_MISSING WARNING", flush=True)
    print("[artifact-verify] Agent claimed DONE/COMPLETE but these files do NOT exist on disk:", flush=True)
    for p in missing:
        print(f"  MISSING: {p}", flush=True)
    if found:
        for p in found:
            print(f"  OK:      {p}", flush=True)
    print("[artifact-verify] Do NOT relay this completion to the user.", flush=True)
    print("[artifact-verify] Verify the agent's work before marking done.", flush=True)
    print("", flush=True)

    # Also log to a persistent file for audit
    log_dir = os.path.join(home, ".claude", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "artifact-verify.jsonl")
    entry = {
        "ts": ts,
        "event": "ARTIFACT_MISSING",
        "missing": missing,
        "found": found,
        "agent_excerpt": text[:500],
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

except Exception as e:
    # Silent failure — never block the agent
    pass

sys.exit(0)
PYEOF
exit 0

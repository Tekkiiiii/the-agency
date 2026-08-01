#!/usr/bin/env python3
"""mem-d8-sample.py — D8 sampler: correction -> lesson/feedback-delta latency.

Spec (memory-v2-target-architecture.html #D8): "Every session with a user
correction produces a lesson/feedback delta within that session (sampled
from transcripts)."

Ponytail-sized implementation: no framework, no transcript-classification
model. Mechanical signal only -- for every Edit/Write tool_use in a raw
session transcript that targets a memory/lessons/*.md or
memory/feedback_*.md file (the exact write targets CLAUDE.md's
Self-Improvement Loop names), record the elapsed time since the nearest
preceding 'user' turn in the same transcript. Because CLAUDE.md restricts
those specific files to append-on-correction content, an edit landing there
is treated as a correction-delta event -- this is a PROXY (same honesty
class as D1's PROXY label in mem-scorecard.py), not semantic correction
detection. It does NOT distinguish a real correction-triggered append from
a bulk/batch link-maintenance edit (e.g. a memory-lint sweep) -- those show
up as genuine data points with their own (often longer or shorter) latency,
not filtered out. This is disclosed in the output, not hidden.

Scope: only <agency-root>/projects/<agency-root-slug>/*.jsonl -- the transcript
directory that sits alongside the two memory bundles mem-graph-build.py already
scores (global memory/ + auto-memory). Keeps D8's data source aligned with the
same bundle boundary the rest of the scorecard uses, instead of inventing a
third scope.

Output: projects/system-improvement/memory/ops/d8-correction-latency.json
"""
import json
import glob
import os
import re
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
# Claude Code encodes the working directory into the project-dir name by
# replacing "/" and "." with "-". Derive it instead of hardcoding one
# machine's slug — a literal "-Users-{name}--claude" silently no-ops for
# every other user.
# Python twin of hooks/lib/resolve-root.sh — same precedence, same default,
# and byte-identical to the copy carried by every hook (enforced by
# .github/scripts/check-hardcoded-root.sh). resolve-root.sh explains why it
# is inlined rather than imported, and why the nt rewrite exists.
def agency_root(home):
    # MSYS-aware Python twin of hooks/lib/resolve-root.sh. That file documents
    # the precedence, why the /c/... rewrite is nt-only, and why this is inlined
    # at every call site instead of imported.
    root = os.environ.get('AGENCY_HOME') or os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(home, '.claude')
    if os.name == 'nt':
        m = re.fullmatch(r'/(?:cygdrive/)?([A-Za-z])(/.*)?', root)
        if m:
            root = m.group(1).upper() + ':' + (m.group(2) or '/')
    return root


CLAUDE = Path(agency_root(str(HOME)))
AUTO_SLUG = str(CLAUDE).replace("/", "-").replace(".", "-")
TRANSCRIPT_DIR = CLAUDE / "projects" / AUTO_SLUG
OUT_PATH = CLAUDE / "projects/system-improvement/memory/ops/d8-correction-latency.json"

DELTA_PATTERNS = ("/memory/lessons/", "/memory/feedback_")


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def scan_transcript(path: Path):
    """Return list of (event_ts_iso, latency_seconds, file_path) for this transcript."""
    hits = []
    prev_user_ts = None
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                t = d.get("type")
                if t == "user":
                    ts = parse_ts(d.get("timestamp"))
                    if ts:
                        prev_user_ts = ts
                elif t == "assistant":
                    msg = d.get("message", {})
                    content = msg.get("content", [])
                    if not isinstance(content, list):
                        continue
                    for c in content:
                        if not (isinstance(c, dict) and c.get("type") == "tool_use"
                                and c.get("name") in ("Edit", "Write")):
                            continue
                        fp = (c.get("input") or {}).get("file_path", "")
                        if not any(pat in fp for pat in DELTA_PATTERNS):
                            continue
                        event_ts = parse_ts(d.get("timestamp"))
                        if event_ts and prev_user_ts:
                            latency = (event_ts - prev_user_ts).total_seconds()
                            if latency >= 0:
                                hits.append((d.get("timestamp"), latency, fp))
    except Exception:
        pass
    return hits


def main():
    files = sorted(glob.glob(str(TRANSCRIPT_DIR / "*.jsonl")))
    all_hits = []
    for fn in files:
        for ts, latency, fp in scan_transcript(Path(fn)):
            all_hits.append({"session_file": Path(fn).name, "event_ts": ts,
                              "latency_s": round(latency, 3), "target": fp})

    latencies = [h["latency_s"] for h in all_hits]
    result = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "method": "PROXY -- mechanical elapsed-time from nearest-preceding user turn to an "
                  "Edit/Write tool_use targeting memory/lessons/*.md or memory/feedback_*.md "
                  "in the same transcript. NOT semantic correction detection; does not "
                  "distinguish a real correction-triggered append from a batch/maintenance "
                  "edit landing on the same file class.",
        "sessions_scanned": len(files),
        "deltas_found": len(all_hits),
        "median_latency_s": (sorted(latencies)[len(latencies) // 2] if latencies else None),
        "max_latency_s": (max(latencies) if latencies else None),
        "samples": all_hits[-25:],  # keep the file bounded; most-recent 25 events
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(f"D8 sample: {len(files)} sessions scanned, {len(all_hits)} delta event(s), "
          f"median latency {result['median_latency_s']}s -> {OUT_PATH}")


if __name__ == "__main__":
    main()

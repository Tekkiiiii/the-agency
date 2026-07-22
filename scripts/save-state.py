#!/usr/bin/env python3
"""save-state.py — mechanical writer for the save-state ritual.

Replaces the LLM-subagent file plumbing of the save-state skill. The caller
(PD or parent session) synthesizes a small JSON payload from what it already
knows about the session; this script does every mechanical read/write the
old Steps 0-13 did. One process, no agent spawn, no token cost beyond the
payload itself.

Usage:
    python3 ~/.claude/scripts/save-state.py --project /path/to/project --payload payload.json
    echo '{...}' | python3 ~/.claude/scripts/save-state.py --project /path/to/project --payload -

Payload schema (all fields optional except slug, phase, next):
{
  "slug": "system-improvement",
  "phase": "current phase or status",
  "next": "specific next action — one sentence",
  "blockers": ["..."],                # or []
  "decisions": ["..."],               # NEW decisions from this session (appended to decisions.md)
  "top_decisions": ["..."],           # locked decisions for next-session.md Decisions field
  "mid_flight": ["path — one-line desc"],
  "delegated": ["task — status"],
  "was_doing": "one line",
  "just_finished": "one line",
  "session_notes": ["bullet", ...],   # extra bullets for the session log
  "interspawn_active": ["T-042 from example-pd — desc"]  # active inter-spawn tasks for index.md
}

Contracts preserved (consumers in parentheses):
  next-session.md format          (recall, pd-resume Step 2)
  sessions/YYYY-MM-DD.md log      (Pinecone upsert, humans)
  heartbeat.md Session End block  (save-state full-scan baseline)
  decisions.md append + >200-line prune to decisions-archive.md
  tasks/ongoing/ next-action stub (Step 3c — pd-resume actionability)
  inter-spawn-tasks/index.md Active Summary overwrite (Step 3b)
  .claude/save-state-state.json reset (Step 10 — turn counter)
  overseer incoming brief         (Step 11 — overseer-pd digest)
  save_state / save_state_complete metric events (weekly aggregator)
  graphify update + unified merge + session node (Step 11b/13 — curator)
  Pinecone session upsert         (Step 12 — RAG recall)
"""

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys

HOME = pathlib.Path.home()
OVERSEER_INCOMING = HOME / "projects/overseer/memory/inter-spawn-tasks/incoming"
EMIT = HOME / ".claude/memory/metrics/emit-metric.sh"
PINECONE_SCRIPT = HOME / ".claude/skills/save-state/pinecone_upsert.py"
UNIFIED_GRAPH = HOME / ".claude/graphify-out/unified/graph.json"


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def now_gmt7():
    return now_utc().astimezone(datetime.timezone(datetime.timedelta(hours=7)))


def atomic_write(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def emit(event: dict):
    """Fire-and-forget metric emit. Never blocks or fails the save."""
    if not EMIT.exists():
        return
    try:
        subprocess.Popen(
            ["bash", str(EMIT), json.dumps(event)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def fmt_list(items, empty="none"):
    items = [i for i in (items or []) if str(i).strip()]
    return items if items else None if empty is None else ([] if not items else items) or []


# ---------------------------------------------------------------- steps

def write_session_log(project: pathlib.Path, p: dict, date_str: str):
    """Step 4 — append to memory/sessions/YYYY-MM-DD.md."""
    path = project / "memory/sessions" / f"{date_str}.md"
    hhmm = now_utc().strftime("%H:%M")
    lines = [f"\n## {hhmm} UTC — save-state"]
    if p.get("was_doing"):
        lines.append(f"**was_doing**: {p['was_doing']}")
    if p.get("just_finished"):
        lines.append(f"**just_finished**: {p['just_finished']}")
    for n in p.get("session_notes") or []:
        lines.append(f"- {n}")
    if p.get("decisions"):
        lines.append("### Decisions")
        lines += [f"- {d}" for d in p["decisions"]]
    if p.get("blockers"):
        lines.append("### Blockers")
        lines += [f"- {b}" for b in p["blockers"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "" if path.exists() else f"# {p['slug']} — session log {date_str}\n"
    with open(path, "a") as f:
        f.write(header + "\n".join(lines) + "\n")
    return path


def write_heartbeat(project: pathlib.Path, p: dict, date_str: str):
    """Step 5 — replace/append the Session End block; preserve content above it."""
    path = project / "memory/heartbeat.md"
    hhmm = now_utc().strftime("%H:%M")
    block = "\n".join([
        f"## Session End — {date_str} {hhmm} UTC",
        f"Status: {p['phase']}",
        f"Was doing: {p.get('was_doing') or 'see next-session.md'}",
        f"Next: {p['next']}",
        "Blockers: " + ("; ".join(p.get("blockers") or []) or "none"),
        f"Details: memory/sessions/{date_str}.md",
    ])
    if path.exists():
        text = path.read_text()
        idx = text.find("## Session End")
        text = (text[:idx].rstrip() + "\n\n") if idx >= 0 else (text.rstrip() + "\n\n")
    else:
        text = f"# {p['slug']} heartbeat\n\n"
    atomic_write(path, text + block + "\n")


def materialize_next_action(project: pathlib.Path, p: dict, date_str: str):
    """Step 3c — ensure tasks/ongoing/ has a file matching the Next action."""
    next_line = p["next"]
    ongoing = project / "memory/tasks/ongoing"
    if not ongoing.is_dir():
        return "no tasks/ongoing dir — skipped"
    token = re.search(r"\b([A-Z]\d+|T\d+-\d+|F\d+)\b", next_line)
    if token and list(ongoing.glob(f"*{token.group(1)}*.md")):
        return f"matched by token {token.group(1)}"
    sig_words = [w for w in re.sub(r"[^a-z0-9 ]", " ", next_line.lower()).split() if len(w) > 3][:5]
    for task in ongoing.glob("*.md"):
        try:
            head = task.read_text(errors="ignore")[:400].lower()
        except OSError:
            continue
        if len(sig_words) >= 3 and sum(w in head for w in sig_words) >= 3:
            return f"matched existing task {task.name}"
    kebab = re.sub(r"[^a-z0-9]+", "-", next_line.lower()).strip("-")[:40]
    stub = ongoing / f"next-action-{kebab}.md"
    atomic_write(stub, f"""# {next_line}

**Status:** ACTIVE — auto-materialized by save-state
**Created:** {date_str}
**Priority:** P2
**Source:** next-session.md Next: line ({date_str} session date)

## Action
{next_line}

## Note
Auto-generated by save-state (Step 3c) because no ongoing task matched this
Next action. The next PD session will pick this up from tasks/ongoing/.
Expand into a fuller spec if the action needs decomposition.
""")
    return f"created {stub.name}"


def update_interspawn_index(project: pathlib.Path, p: dict):
    """Step 3b — overwrite the Active Summary section of inter-spawn-tasks/index.md."""
    path = project / "memory/inter-spawn-tasks/index.md"
    if not path.exists():
        return
    active = p.get("interspawn_active") or []
    summary = "\n".join(f"- {a}" for a in active) if active else "_(no active inter-spawn tasks)_"
    text = path.read_text()
    m = re.search(r"(## Active Summary\s*\n)(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if m:
        text = text[:m.start(2)] + summary + "\n" + text[m.end(2):]
    else:
        text = text.rstrip() + "\n\n## Active Summary\n" + summary + "\n"
    atomic_write(path, text)


def sweep_incoming(project: pathlib.Path):
    incoming = project / "memory/inter-spawn-tasks/incoming"
    if not incoming.is_dir():
        return []
    out = []
    for f in sorted(incoming.glob("*.md")):
        title = ""
        try:
            for line in f.read_text(errors="ignore").splitlines():
                if line.strip():
                    title = line.strip().lstrip("# ")[:80]
                    break
        except OSError:
            pass
        out.append(f"{f.name} — {title}" if title else f.name)
    return out


def write_next_session(project: pathlib.Path, p: dict, date_str: str, inbound: list):
    """Step 6 — overwrite next-session.md. ONLY file pd-resume/recall read at startup."""
    path = project / "memory/next-session.md"
    blockers = p.get("blockers") or []
    tops = p.get("top_decisions") or []
    mid = p.get("mid_flight") or []
    deleg = p.get("delegated") or []
    lines = [f"# {p['slug']}", f"Phase: {p['phase']}", f"Next: {p['next']}"]
    lines.append("Blockers: " + (blockers[0] if len(blockers) == 1 else "none" if not blockers else ""))
    lines += [f"  {b}" for b in (blockers if len(blockers) > 1 else [])]
    lines.append("Decisions: " + ("; ".join(tops[:2]) if tops else "see decisions.md"))
    lines.append("Mid-flight: " + ("; ".join(mid[:2]) if mid else "none"))
    lines.append("Delegated: " + ("; ".join(deleg) if deleg else "none"))
    lines.append("Pending inbound: " + ("; ".join(inbound) if inbound else "none"))
    lines.append(f"Last saved: {date_str}")
    atomic_write(path, "\n".join(lines[:15]) + "\n")


def update_decisions(project: pathlib.Path, p: dict, date_str: str):
    """Steps 6b/6c — append new decisions, prune >200 lines (keep 60, archive rest)."""
    path = project / "memory/decisions.md"
    new = p.get("decisions") or []
    if new:
        existing = path.read_text() if path.exists() else ""
        to_add = [d for d in new if d not in existing]
        if to_add:
            block = f"## {date_str} (save-state)\n" + "\n".join(f"- {d}" for d in to_add) + "\n"
            # newest-at-top convention: prune keeps the TOP 60 lines, so new
            # decisions must be prepended (after a leading # title if present)
            lines = existing.splitlines()
            if lines and lines[0].startswith("# "):
                out = lines[0] + "\n\n" + block + "\n".join(lines[1:]) + ("\n" if lines[1:] else "")
            else:
                out = block + existing
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, out)
    if path.exists():
        lines = path.read_text().splitlines()
        if len(lines) > 200:
            keep, archive = lines[:60], lines[60:]
            arch = project / "memory/decisions-archive.md"
            with open(arch, "a") as f:
                f.write(f"\n## Archived {date_str} (auto-prune): decisions moved from decisions.md lines 61+\n")
                f.write("\n".join(archive) + "\n")
            atomic_write(path, "\n".join(keep) +
                         f"\n_({date_str} decisions auto-archived to memory/decisions-archive.md)_\n")


def update_state_md(project: pathlib.Path, p: dict, date_str: str):
    """Step 8 — backwards compat only. Update Last Session section if STATE.md exists."""
    path = project / "STATE.md"
    if not path.exists():
        return
    text = path.read_text()
    block = f"## Last Session\n- {date_str}: {p.get('was_doing') or p['phase']}\n- Next: {p['next']}\n"
    m = re.search(r"(## Last Session\s*\n)(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if m:
        atomic_write(path, text[:m.start()] + block + text[m.end():])


def reset_state_json(project: pathlib.Path, date_str: str):
    """Step 10 — reset turn counter."""
    path = project / ".claude/save-state-state.json"
    if not path.exists():
        return
    try:
        state = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        state = {}
    ts = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    state.update({"turn_count": 0, "last_turn_at": ts,
                  "last_saved_at": ts, "last_session_date": date_str})
    atomic_write(path, json.dumps(state, indent=2) + "\n")


def write_overseer_brief(p: dict):
    """Step 11 — brief to overseer incoming. Skip for overseer itself."""
    if p["slug"] == "overseer":
        return
    ts = now_gmt7().strftime("%Y%m%d-%H%M%S")
    OVERSEER_INCOMING.mkdir(parents=True, exist_ok=True)
    blocker = (p.get("blockers") or ["no blockers"])[0]
    content = "\n".join([
        f"project: {p['slug']}",
        "status:",
        f"- {p['phase']} — save-state written"
        + (f", {len(p.get('mid_flight') or [])} mid-flight file(s)" if p.get("mid_flight") else ""),
        f"- {p.get('was_doing') or p.get('just_finished') or 'session work captured'}",
        f"- Blocker: {blocker}. Next: {p['next']}",
    ]) + "\n"
    atomic_write(OVERSEER_INCOMING / f"save-state-brief-{ts}-{p['slug']}.md", content)


def inject_session_node(project: pathlib.Path, slug: str, date_str: str):
    """Step 13 — session node + mention edges into the unified graph. Best-effort."""
    if not UNIFIED_GRAPH.exists():
        return
    try:
        graph = json.loads(UNIFIED_GRAPH.read_text())
    except (json.JSONDecodeError, OSError):
        return
    node_id = f"session_{re.sub(r'[^a-z0-9]', '_', slug.lower())}_{date_str.replace('-', '_')}"
    session_file = f"memory/sessions/{date_str}.md"
    nodes = graph.setdefault("nodes", [])
    edges = graph.setdefault("links", [])  # edges live under "links", NOT "edges"
    if any(n.get("id") == node_id for n in nodes):
        return
    nodes.append({"id": node_id, "label": f"{slug} session {date_str}",
                  "file_type": "session", "source_file": session_file,
                  "source_location": None, "source_url": None,
                  "captured_at": date_str, "author": None, "contributor": None})
    session_path = project / session_file
    text = ""
    if session_path.exists():
        try:
            text = session_path.read_text(errors="ignore")
        except OSError:
            pass
    node_ids = {n.get("id") for n in nodes}
    for skill in set(re.findall(r"/([a-z][a-z0-9-]+)", text)):
        edges.append({"source": node_id, "target": f"skill_{re.sub(r'[^a-z0-9]', '_', skill)}",
                      "relation": "used_skill", "confidence": "EXTRACTED",
                      "confidence_score": 1.0, "source_file": session_file, "weight": 1.0})
    for agent in set(re.findall(r"\b([a-z][a-z0-9-]+-(?:pd|coord|exec))\b", text, re.IGNORECASE)):
        edges.append({"source": node_id, "target": f"agent_{re.sub(r'[^a-z0-9]', '_', agent.lower())}",
                      "relation": "worked_with", "confidence": "EXTRACTED",
                      "confidence_score": 1.0, "source_file": session_file, "weight": 1.0})
    if re.search(r"(?i)(decision|decided|resolved)", text):
        edges.append({"source": node_id, "target": f"decisions_{re.sub(r'[^a-z0-9]', '_', slug.lower())}",
                      "relation": "recorded_decision", "confidence": "INFERRED",
                      "confidence_score": 0.8, "source_file": session_file, "weight": 1.0})
    for fpath in list(set(re.findall(r"(?:memory|src|lib|app)/[a-zA-Z0-9/_-]+\.(?:md|ts|py|rs|json)", text)))[:10]:
        target_id = re.sub(r"[^a-z0-9]", "_", pathlib.Path(fpath).stem.lower())
        if target_id in node_ids:
            edges.append({"source": node_id, "target": target_id, "relation": "modified",
                          "confidence": "INFERRED", "confidence_score": 0.7,
                          "source_file": session_file, "weight": 1.0})
    session_nodes = [n for n in nodes if n.get("file_type") == "session"]
    if len(session_nodes) % 5 == 0:
        (HOME / ".claude/graphify-out/.session_merge_needed").write_text(str(len(session_nodes)))
    atomic_write(UNIFIED_GRAPH, json.dumps(graph, indent=2))


def fire_background_jobs(project: pathlib.Path, p: dict, date_str: str):
    """Steps 11b + 12 — graphify update/merge and Pinecone upsert, detached."""
    cmd = f'''
if command -v graphify >/dev/null 2>&1 && [ -d "{project}/memory" ]; then
  cd "{project}"
  graphify memory/ --update --no-viz --exclude "brand/" --exclude "qa/" --exclude "graphify-out/" 2>/dev/null || \
  graphify memory/ --update --no-viz 2>/dev/null || true
  if [ -f "memory/graphify-out/graph.json" ] && [ -f "$HOME/.claude/graphify-out/unified/graph.json" ]; then
    graphify merge-graphs "$HOME/.claude/graphify-out/unified/graph.json" memory/graphify-out/graph.json --in-place 2>/dev/null || true
  fi
fi
FLAG="$HOME/.claude/graphify-out/.session_merge_needed"
if [ -f "$FLAG" ]; then
  rm -f "$FLAG"
  graphify merge-graphs "$HOME/.claude/graphify-out/unified/graph.json" --in-place 2>/dev/null || true
fi
'''
    try:
        subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass
    if PINECONE_SCRIPT.exists():
        session_log = ""
        sp = project / "memory/sessions" / f"{date_str}.md"
        if sp.exists():
            try:
                session_log = sp.read_text(errors="ignore")[-4000:]
            except OSError:
                pass
        blob = json.dumps({
            "project_slug": p["slug"], "session_date": date_str,
            "session_log": session_log,
            "decisions": "\n".join(p.get("decisions") or []),
            "next_action": p["next"],
            "blockers": "; ".join(p.get("blockers") or []) or "none",
            "mid_flight": "; ".join(p.get("mid_flight") or []) or "none",
            "status": p["phase"],
        })
        try:
            subprocess.Popen(["/tmp/pinecone-env/bin/python3", str(PINECONE_SCRIPT), blob],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--payload", required=True, help="path to payload JSON, or - for stdin")
    args = ap.parse_args()

    project = pathlib.Path(args.project).expanduser().resolve()
    if not (project / "memory").is_dir():
        sys.exit(f"ERROR: {project}/memory does not exist — wrong project path?")

    raw = sys.stdin.read() if args.payload == "-" else pathlib.Path(args.payload).read_text()
    p = json.loads(raw)
    for field in ("slug", "phase", "next"):
        if not p.get(field):
            sys.exit(f"ERROR: payload missing required field '{field}'")

    date_str = now_utc().date().isoformat()
    emit({"ts": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"), "event": "save_state",
          "mode": "script", "reads_skipped": 7})

    write_session_log(project, p, date_str)
    write_heartbeat(project, p, date_str)
    note_3c = materialize_next_action(project, p, date_str)
    update_interspawn_index(project, p)
    inbound = sweep_incoming(project)
    write_next_session(project, p, date_str, inbound)
    update_decisions(project, p, date_str)
    update_state_md(project, p, date_str)
    reset_state_json(project, date_str)
    write_overseer_brief(p)
    try:
        inject_session_node(project, p["slug"], date_str)
    except Exception:
        pass
    fire_background_jobs(project, p, date_str)

    emit({"ts": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"), "event": "save_state_complete",
          "project": p["slug"], "mode": "script"})
    print(f"save-state done! ({note_3c}; {len(inbound)} pending inbound)")


if __name__ == "__main__":
    main()

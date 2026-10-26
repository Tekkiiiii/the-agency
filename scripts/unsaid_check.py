#!/usr/bin/env python3
"""unsaid_check.py - flag brief lines that carry instructions the user never said (warn-only reporter).

Why: the main session put rules the user never said into PD briefs (e.g. "Replaces the 7-tab layout").
Pure core: user_corpus(), extract_brief(), check().  Consumers: hooks/unsaid-check.sh (--hook), CLI replay, --scan-transcripts.
Rules: A = removal/restriction/priority marker whose stem never appears in the user's text;
       C = quote attributed to the user that is not a substring of the user's text; B (--strict only) = low content-word overlap.
CLI always exits 0.
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys
import time
from collections import Counter

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


# name -> regex (used on brief lines AND on the corpus, so "stem appears" means the same on both sides)
# Dropped after FP measurement (2026-10-23, 518 briefs: median flags per flagged brief 2 -> 1): only, first, stop, block, don't/do not.
# Too common in ordinary scoping prose; they re-enter via --scan-transcripts experiments, not the hook.
MARKERS = {
    "replace": r"\breplac\w*",
    "remove": r"\bremov\w*",
    "drop": r"\bdrop(?:s|ped|ping)?\b",
    "delete": r"\bdelet\w*",
    "strike": r"\bstr(?:ike|ikes|uck|iking)\b",
    "retire": r"\bretir\w*",
    "hide": r"\b(?:hide|hides|hidden|hiding)\b",
    "clear": r"\bclear(?:s|ed)?\b",
    "instead of": r"\binstead of\b",
    "no longer": r"\bno longer\b",
    "never": r"\bnever\b",
    "priority": r"\bpriorit\w*",
    "must not": r"\bmust not\b",
}
EXEMPT_PREFIX = re.compile(r"^(source|user verbatim|assumption|question|main-session addition)\s*:", re.I)
QUOTE_SPAN = re.compile(r'["“](.+?)["”]')
ATTRIB = re.compile(r'\buser\s+(?:verbatim|said)|\buser\s*:\s*["“]', re.I)
SKIP_START = ("<local-command-caveat>", "<agent-message", "Another Claude session sent a message", "<task-notification")
BRIEF_DIRS = ("/inter-spawn-tasks/revisions/", "/inter-spawn-tasks/incoming/")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[ \t]*\n(.*?)\n[ \t]*\1[ \t]*(?:\n|$)", re.S)
STOP = set("this that with from have will should would there their about which when where what into than then them they were been being also each does done make made must only your you the and for are not but all any can its our out use used using has had was who how why one two".split())


# ---------- corpus ----------
def user_text(entry):
    """The user's text from one JSONL entry, or None."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    c = (entry.get("message") or {}).get("content")
    if isinstance(c, list):
        parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
        c = "\n".join(parts) if parts else None
    if not isinstance(c, str):
        return None
    c = c.strip()
    if c.startswith(SKIP_START):
        return None
    if c.startswith("<command-") or "<command-name>" in c:
        m = re.search(r"<command-args>(.*?)</command-args>", c, re.S)
        c = m.group(1).strip() if m else ""
    c = re.sub(r"<system-reminder>.*?</system-reminder>", "", c, flags=re.S).strip()
    return c or None


def _entries(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            try:
                yield i, json.loads(line)
            except ValueError:
                continue


def user_corpus(transcript_path, upto_line=None):
    out = []
    for i, e in _entries(transcript_path):
        if upto_line is not None and i >= upto_line:
            break
        t = user_text(e)
        if t:
            out.append(t)
    return "\n".join(out)


# ---------- brief extraction ----------
def extract_brief(tool_name, tool_input):
    ti = tool_input or {}
    if tool_name in ("Write", "Edit"):
        fp = ti.get("file_path") or ""
        if any(d in fp for d in BRIEF_DIRS):
            v = ti.get("content") if tool_name == "Write" else ti.get("new_string")
            return v if isinstance(v, str) else None
        return None
    if tool_name == "Bash":
        cmd = ti.get("command") or ""
        if "inter-spawn-tasks/revisions" in cmd or "inter-spawn-tasks/incoming" in cmd:
            bodies = [m.group(2) for m in HEREDOC.finditer(cmd)]
            return "\n".join(bodies) if bodies else None
        return None
    if tool_name == "SendMessage":
        m = ti.get("message")
        return m if isinstance(m, str) and m.strip() else None
    if tool_name == "Agent":
        st = ti.get("subagent_type") or ""
        if st.endswith("-pd") or st == "pd-coordinator":
            p = ti.get("prompt")
            return p if isinstance(p, str) else None
    return None


# ---------- check ----------
def _norm(s):
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def _clean_line(raw):
    s = raw.strip()
    return re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", s).lstrip("*_ ").strip()


def _words(s):
    return {w for w in re.findall(r"[a-z]{4,}", s.lower()) if w not in STOP}


def check(brief, corpus, strict=False, markers=None):
    markers = MARKERS if markers is None else markers
    corp = _norm(corpus)
    corpus_l = corpus.lower().replace("’", "'")
    cwords = _words(corpus) if strict else set()
    flags = []
    for n, raw in enumerate(brief.split("\n"), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body = _clean_line(line)
        if "[STRUCK" in line:
            continue
        # Rule C: quotes attributed to the user
        if ATTRIB.search(body):
            for m in QUOTE_SPAN.finditer(body):
                if _norm(m.group(1)) not in corp:
                    flags.append({"line_no": n, "line": line, "rule": "C",
                                  "reason": "quote attributed to the user is not in the user's words this session"})
                    break
        if EXEMPT_PREFIX.match(body):
            continue
        text = QUOTE_SPAN.sub(" ", body).replace("’", "'")
        if not text.strip():
            continue
        # Rule A
        missing = [name for name, rx in markers.items()
                   if re.search(rx, text, re.I) and not re.search(rx, corpus_l, re.I)]
        if missing:
            flags.append({"line_no": n, "line": line, "rule": "A",
                          "reason": "marker not in the user's words: " + ", ".join(missing)})
            continue
        # Rule B (strict only)
        if strict:
            w = _words(text)
            if len(w) >= 4 and len(w & cwords) / len(w) < 0.3:
                flags.append({"line_no": n, "line": line, "rule": "B", "reason": "low content-word overlap with the user's words"})
    return flags


def tag(f):
    if f["rule"] == "A":
        return "A:" + f["reason"].split(": ", 1)[1].split(", ")[0]
    return {"B": "B:overlap", "C": "C:quote"}[f["rule"]]


def fmt(f):
    return 'UNSAID L%d [%s] "%s"' % (f["line_no"], tag(f), f["line"])


# ---------- transcript helpers ----------
def _tool_uses(entry):
    c = (entry.get("message") or {}).get("content") if isinstance(entry.get("message"), dict) else None
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                yield b.get("name"), b.get("input") or {}


def replay(transcript, line, strict=False):
    corpus = user_corpus(transcript, upto_line=line)
    for i, e in _entries(transcript):
        if i != line:
            continue
        found = False
        for name, ti in _tool_uses(e):
            b = extract_brief(name, ti)
            if b is None:
                continue
            found = True
            print("# line %d tool=%s" % (line, name))
            for f in check(b, corpus, strict):
                print(fmt(f))
        if not found:
            print("# line %d: no qualifying tool call" % line, file=sys.stderr)
        return


def scan(pattern, strict=False, markers=None):
    briefs = []  # list of (path, line, tool, flags)
    for p in sorted(glob.glob(os.path.expanduser(pattern))):
        corpus = []
        for i, e in _entries(p):
            t = user_text(e)
            if t:
                corpus.append(t)
                continue
            if e.get("type") != "assistant" or e.get("isSidechain"):
                continue
            for name, ti in _tool_uses(e):
                b = extract_brief(name, ti)
                if b is not None:
                    briefs.append((p, i, name, check(b, "\n".join(corpus), strict, markers)))
    return briefs


def report(briefs, show_samples=12):
    n = len(briefs)
    fl = [b for b in briefs if b[3]]
    counts = [len(b[3]) for b in fl]
    print("briefs: %d" % n)
    print("flagged briefs: %d" % len(fl))
    if counts:
        print("flags per flagged brief: mean %.2f median %s max %d" % (statistics.mean(counts), statistics.median(counts), max(counts)))
    allc = [len(b[3]) for b in briefs]
    if allc:
        print("flags per brief (all): mean %.2f median %s" % (statistics.mean(allc), statistics.median(allc)))
    rules = Counter(f["rule"] for b in briefs for f in b[3])
    print("rules:", dict(rules))
    tm = Counter(tag(f) for b in briefs for f in b[3])
    print("top markers:")
    for k, v in tm.most_common(10):
        print("  %4d %s" % (v, k))
    print("samples:")
    import random
    random.seed(1)
    pool = [(p, i, t, f) for p, i, t, flags in fl for f in flags]
    for p, i, t, f in random.sample(pool, min(show_samples, len(pool))):
        print("  %s:%d %s %s" % (os.path.basename(p)[:8], i, t, fmt(f)[:200]))
    return fl


# ---------- hook ----------
def hook(raw):
    try:
        d = json.loads(raw)
        if d.get("agent_id"):
            return {}
        tool = d.get("tool_name")
        brief = extract_brief(tool, d.get("tool_input"))
        tp = d.get("transcript_path")
        if brief is None or not tp or not os.path.exists(tp):
            return {}
        flags = check(brief, user_corpus(tp))
        if not flags:
            return {}
        try:
            logd = os.path.join(agency_root(os.path.expanduser("~")), "logs")
            os.makedirs(logd, exist_ok=True)
            with open(os.path.join(logd, "unsaid-check.jsonl"), "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": tool,
                                    "rules": dict(Counter(x["rule"] for x in flags)), "flags": len(flags)}) + "\n")
        except OSError:
            pass
        shown = "\n".join(fmt(f)[:240] for f in flags[:8])
        msg = ("UNSAID-CHECK: these brief lines are not in the user's words this session. Remove them, or relabel as "
               "`Assumption:` / `Question:` for the user:\n" + shown)
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}
    except Exception:
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript")
    ap.add_argument("--upto-line", type=int)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--brief-file")
    ap.add_argument("--replay-line", type=int)
    ap.add_argument("--scan-transcripts", nargs="?", const="__DEFAULT__",
                    help="glob of transcript .jsonl files (default: <agency-root>/projects/*/*.jsonl)")
    ap.add_argument("--drop-markers", default="", help="comma list of marker names to disable (measurement)")
    ap.add_argument("--hook", action="store_true")
    a = ap.parse_args(argv)
    if a.hook:
        print(json.dumps(hook(sys.stdin.read())))
        return 0
    if a.scan_transcripts:
        if a.scan_transcripts == "__DEFAULT__":
            a.scan_transcripts = os.path.join(agency_root(os.path.expanduser("~")), "projects/*/*.jsonl")
        drop = {m.strip() for m in a.drop_markers.split(",") if m.strip()}
        mk = {k: v for k, v in MARKERS.items() if k not in drop}
        report(scan(a.scan_transcripts, a.strict, mk))
        return 0
    if a.replay_line is not None and a.transcript:
        replay(a.transcript, a.replay_line, a.strict)
        return 0
    if a.brief_file and a.transcript:
        corpus = user_corpus(a.transcript, a.upto_line)
        for f in check(open(a.brief_file).read(), corpus, a.strict):
            print(fmt(f))
        return 0
    ap.print_usage(sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

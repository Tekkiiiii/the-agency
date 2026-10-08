#!/usr/bin/env python3
"""jev-feedback.py - reviewer feedback loop for the skill router (scripts/skill-route.py).

Offline and local only: this tool appends to / rewrites one JSONL file. It never opens a
network connection, never starts a subprocess and works whether or not the router is enabled.

One JSONL record per verdict in $JEV_FEEDBACK_LOG (default {root}/memory/metrics/jev-feedback.jsonl):
  {ts, project, task_id, tool: skill-route, jev_verdict, router, pd_review: agree|disagree, pd_reason,
   outcome: null|ok|wrong_skill, outcome_mismatch: null|bool, task_text}
Optional keys: "correct_skills" (list, for wrong_skill outcomes; lets skill-route-eval.py turn the miss into a
regression case) and "sample" (true => ignored by every reader).
{root} is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.

Subcommands:
  add         record a router verdict plus the reviewer's call (agree|disagree + one-line reason)
  outcome     TASK_ID OUTCOME  - attach the observed outcome, compute outcome_mismatch
  mismatches  print confirmed mismatches (outcome_mismatch == true) as JSONL

Secrets: task_text is passed through jev_client.redact() before it is stored (API-key families and
KEY=value assignments become [REDACTED]). validate_record() rejects a record whose task_text still holds
something redact() would change. If jev_client cannot be imported the text is stored as "" (fail closed).
Stdlib only. Python 3.9 compatible.
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile
import time

try:
    import fcntl
except ImportError:  # non-POSIX (e.g. native Windows): no advisory lock, tool still works
    fcntl = None


# Python twin of hooks/lib/resolve-root.sh: same precedence, same default,
# byte-identical to the copy carried by every hook and script (enforced by
# .github/scripts/check-hardcoded-root.sh).
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


TOOLS = ("skill-route",)
REVIEWS = ("agree", "disagree")
OUTCOMES = ("ok", "wrong_skill")
REQUIRED = ("ts", "project", "task_id", "tool", "jev_verdict", "router",
            "pd_review", "pd_reason", "outcome", "outcome_mismatch", "task_text")
OPTIONAL = ("correct_skills", "sample")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def default_log():
    return os.environ.get("JEV_FEEDBACK_LOG") or os.path.join(
        agency_root(os.path.expanduser("~")), "memory", "metrics", "jev-feedback.jsonl")


def now_iso():
    return datetime.datetime.fromtimestamp(time.time(), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_REDACTOR = []   # one-element cache: [redact_fn_or_None]


def _redactor():
    """jev_client.redact, or None when jev_client cannot be imported. jev_client does no I/O at import time."""
    if not _REDACTOR:
        _REDACTOR.append(_load_redactor())
    return _REDACTOR[0]


def _load_redactor():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import jev_client  # noqa: E402
        return jev_client.redact
    except Exception:  # noqa: BLE001 - any import problem means "fail closed", not a crash
        return None
    finally:
        try:
            sys.path.remove(os.path.dirname(os.path.abspath(__file__)))
        except ValueError:
            pass


def scrub(text):
    """task_text as it may be stored: secrets redacted; "" when no redactor is available (fail closed)."""
    text = text or ""
    if not text:
        return ""
    redact = _redactor()
    if redact is None:
        sys.stderr.write("warning: jev_client.redact unavailable; task_text stored as empty\n")
        return ""
    return redact(text)


def holds_secret(text):
    """True when redact() would change task_text (or no redactor is available and text is non-empty)."""
    if not text:
        return False
    redact = _redactor()
    return redact is None or redact(text) != text


def validate_record(rec):
    """Return a list of error strings (empty list == valid)."""
    errs = []
    if not isinstance(rec, dict):
        return ["record is not an object"]
    for k in REQUIRED:
        if k not in rec:
            errs.append("missing key: %s" % k)
    for k in rec:
        if k not in REQUIRED and k not in OPTIONAL:
            errs.append("unknown key: %s" % k)
    if errs:
        return errs
    if not isinstance(rec["ts"], str) or not TS_RE.match(rec["ts"]):
        errs.append("ts must be UTC ISO like 2026-01-02T03:04:05Z")
    for k in ("project", "task_id", "jev_verdict", "router", "pd_reason", "task_text"):
        if not isinstance(rec[k], str):
            errs.append("%s must be a string" % k)
    if not rec["project"]:
        errs.append("project must not be empty")
    if not rec["task_id"]:
        errs.append("task_id must not be empty")
    if rec["tool"] not in TOOLS:
        errs.append("tool must be one of %s" % (TOOLS,))
    if rec["pd_review"] not in REVIEWS:
        errs.append("pd_review must be one of %s" % (REVIEWS,))
    if rec["outcome"] is not None and rec["outcome"] not in OUTCOMES:
        errs.append("outcome must be null or one of %s" % (OUTCOMES,))
    if rec["outcome_mismatch"] is not None and not isinstance(rec["outcome_mismatch"], bool):
        errs.append("outcome_mismatch must be null or bool")
    if rec["outcome"] is None and rec["outcome_mismatch"] is not None:
        errs.append("outcome_mismatch must be null while outcome is null")
    if rec["tool"] == "skill-route" and not rec["jev_verdict"]:
        errs.append("skill-route jev_verdict must name the top-1 skill")
    if rec["pd_review"] == "disagree" and not rec["pd_reason"].strip():
        errs.append("pd_reason is required when pd_review is disagree")
    if "correct_skills" in rec:
        cs = rec["correct_skills"]
        if not isinstance(cs, list) or not cs or not all(isinstance(x, str) and x for x in cs):
            errs.append("correct_skills must be a non-empty list of skill names")
    if "sample" in rec and not isinstance(rec["sample"], bool):
        errs.append("sample must be a bool")
    if isinstance(rec["task_text"], str) and holds_secret(rec["task_text"]):
        errs.append("task_text must not hold a secret (jev_client.redact would change it)")
    return errs


def compute_mismatch(rec, outcome):
    """outcome_mismatch rules. Returns (bool, error_or_None)."""
    if outcome == "ok":
        return False, None
    if outcome == "wrong_skill":
        return True, None
    return False, "unknown outcome"


def read_records(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                sys.stderr.write("warning: %s line %d is not JSON, skipped\n" % (path, n))
                continue
            out.append(rec)
    return out


def write_all(path, records):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".jev-feedback.", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


class Locked(object):
    """Advisory lock on <log>.lock so concurrent add/outcome calls do not lose records."""

    def __init__(self, path):
        self.lockpath = path + ".lock"
        self.f = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.lockpath) or ".", exist_ok=True)
        self.f = open(self.lockpath, "a")
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def cmd_add(a):
    rec = {
        "ts": a.ts or now_iso(),
        "project": a.project,
        "task_id": a.task_id,
        "tool": a.tool,
        "jev_verdict": a.verdict,
        "router": a.router,
        "pd_review": a.review,
        "pd_reason": a.reason or "",
        "outcome": None,
        "outcome_mismatch": None,
        "task_text": scrub(a.task_text),
    }
    if a.sample:
        rec["sample"] = True
    errs = validate_record(rec)
    if errs:
        sys.stderr.write("invalid record:\n  " + "\n  ".join(errs) + "\n")
        return 2
    path = a.file or default_log()
    with Locked(path):
        recs = read_records(path)
        for r in recs:
            if (r.get("tool"), r.get("project"), r.get("task_id")) == (a.tool, a.project, a.task_id) and bool(r.get("sample")) == bool(a.sample):
                sys.stderr.write("a record for %s/%s/%s already exists (one record per verdict); use `outcome` to update it\n" % (a.tool, a.project, a.task_id))
                return 2
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "task_id": a.task_id, "file": path}))
    return 0


def cmd_outcome(a):
    path = a.file or default_log()
    with Locked(path):
        recs = read_records(path)
        idx = [i for i, r in enumerate(recs)
               if r.get("task_id") == a.task_id and not r.get("sample")
               and (not a.project or r.get("project") == a.project)
               and (not a.tool or r.get("tool") == a.tool)]
        if not idx:
            sys.stderr.write("no record for task_id %s\n" % a.task_id)
            return 2
        if len(idx) > 1:
            sys.stderr.write("task_id %s is ambiguous (%d records); add --project and/or --tool\n" % (a.task_id, len(idx)))
            return 2
        rec = recs[idx[0]]
        mm, err = compute_mismatch(rec, a.outcome)
        if err:
            sys.stderr.write(err + "\n")
            return 2
        rec["outcome"] = a.outcome
        rec["outcome_mismatch"] = mm
        if a.correct_skills:
            rec["correct_skills"] = [s.strip() for s in a.correct_skills.split(",") if s.strip()]
        errs = validate_record(rec)
        if errs:
            sys.stderr.write("invalid record after update:\n  " + "\n  ".join(errs) + "\n")
            return 2
        write_all(path, recs)
    print(json.dumps({"ok": True, "task_id": a.task_id, "outcome": a.outcome, "outcome_mismatch": mm}))
    return 0


def confirmed_mismatches(path, tool=None, include_sample=False):
    out = []
    for r in read_records(path):
        if r.get("sample") and not include_sample:
            continue
        if r.get("outcome_mismatch") is not True:
            continue
        if tool and r.get("tool") != tool:
            continue
        out.append(r)
    return out


def cmd_mismatches(a):
    for r in confirmed_mismatches(a.file or default_log(), a.tool, a.include_sample):
        print(json.dumps(r, ensure_ascii=False))
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="Skill router feedback loop: add verdict + reviewer call, record outcome, list mismatches")
    p.add_argument("--file", help="feedback JSONL (default $JEV_FEEDBACK_LOG or {root}/memory/metrics/jev-feedback.jsonl)")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("add", help="record a verdict and the reviewer's call")
    s.add_argument("--project", required=True)
    s.add_argument("--task-id", required=True)
    s.add_argument("--tool", choices=TOOLS, default="skill-route", help="always skill-route (kept so records stay self-describing)")
    s.add_argument("--verdict", required=True, help="the router's top-1 skill name")
    s.add_argument("--router", required=True, help="jev|haiku|grep|passthrough")
    s.add_argument("--review", required=True, choices=REVIEWS, help="reviewer's call on the verdict")
    s.add_argument("--reason", default="", help="one-line reason (required when disagree)")
    s.add_argument("--task-text", default="", help="task text (secrets are redacted before it is stored)")
    s.add_argument("--ts", default=None)
    s.add_argument("--sample", action="store_true", help='mark as a sample record ("sample": true); readers ignore it')
    s.set_defaults(fn=cmd_add)
    o = sub.add_parser("outcome", help="attach the observed outcome and compute outcome_mismatch")
    o.add_argument("task_id")
    o.add_argument("outcome", choices=OUTCOMES)
    o.add_argument("--project", default=None)
    o.add_argument("--tool", default=None, choices=TOOLS)
    o.add_argument("--correct-skills", default=None, help="comma list; for wrong_skill: the skills that should have won")
    o.set_defaults(fn=cmd_outcome)
    m = sub.add_parser("mismatches", help="print confirmed mismatches as JSONL")
    m.add_argument("--tool", choices=TOOLS, default=None)
    m.add_argument("--include-sample", action="store_true")
    m.set_defaults(fn=cmd_mismatches)
    return p


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    if not getattr(a, "fn", None):
        p.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())

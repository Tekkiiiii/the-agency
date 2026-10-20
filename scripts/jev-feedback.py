#!/usr/bin/env python3
"""jev-feedback.py - reviewer feedback loop for the skill router (scripts/skill-route.py).

Offline and local only: this tool appends to / rewrites one JSONL file. It never opens a
network connection, never starts a subprocess and works whether or not the router is enabled.

One JSONL record per verdict in $JEV_FEEDBACK_LOG (default {root}/memory/metrics/jev-feedback.jsonl):
  {ts, project, task_id, tool: skill-route, jev_verdict, router, pd_review: agree|disagree|unreviewed, pd_reason,
   outcome: null|ok|wrong_skill, outcome_mismatch: null|bool, task_text}
Optional keys: "correct_skills" (list, for wrong_skill outcomes; lets skill-route-eval.py turn the miss into a
regression case) and "sample" (true => ignored by every reader).
{root} is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.

Spawn records (automatic, written per Agent spawn by scripts/jev_spawn.py via append_spawn_record). tool is
"skill-route", jev_verdict is Jev's top-1 skill or "(none)", pd_review is agree (accept) | disagree
(modify/reject) | unreviewed, and these optional keys are allowed:
  source "spawn"; spawn_verdict accept|modify|reject|unreviewed; verdict_raw (str); verdict_source
  explicit|auto_default|auto_match|auto_empty|confidential_local|inferred|jev_unavailable|deny_cap; gate (str); none_fired (bool);
  jev_skills / spawner_skills (lists of str); subagent_type, parent_agent, role, route_id, spawn_id (str);
  consult pre|gate|post.
For source spawn, pd_reason may be empty on disagree. Records without "source" validate exactly as before.

Importable (other scripts load this file via importlib because of the hyphen):
  append_spawn_record(rec, path=None) -> list   validate (a task_text redact() would change is rejected), append under the lock;
                                                returns the error list (empty = written); never raises
  reconcile(feedback_path=None, spawn_logs=None) -> dict   fill outcome from spawn_end rows; {checked, updated_ok, updated_wrong_skill}

Subcommands:
  add         record a router verdict plus the reviewer's call (agree|disagree + one-line reason)
  outcome     TASK_ID OUTCOME  - attach the observed outcome, compute outcome_mismatch
  mismatches  print confirmed mismatches (outcome_mismatch == true) as JSONL
  reconcile   [--spawn-logs FILE ...]  join spawn records to spawn_end rows by spawn_id (skill_mismatch true ->
              wrong_skill, outcome DONE -> ok, else left null). Default logs: {root}/logs/spawns.jsonl plus
              every project memory/spawns.jsonl listed in {root}/memory/medium-term.md. Prints a JSON summary.
  spawn-stats print JSON stats over source-spawn records: totals, gate x spawn_verdict, verdict_source, parent_agent,
              agreement rate (accept share), outcomes, Jev-mismatch count

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
REVIEWS = ("agree", "disagree", "unreviewed")
CLI_REVIEWS = ("agree", "disagree")
OUTCOMES = ("ok", "wrong_skill")
REQUIRED = ("ts", "project", "task_id", "tool", "jev_verdict", "router",
            "pd_review", "pd_reason", "outcome", "outcome_mismatch", "task_text")
SPAWN_VERDICTS = ("accept", "modify", "reject", "unreviewed")
VERDICT_SOURCES = ("explicit", "auto_default", "auto_match", "auto_empty", "confidential_local", "inferred",
                   "jev_unavailable", "deny_cap")
CONSULTS = ("pre", "gate", "post")
SPAWN_STR_KEYS = ("verdict_raw", "gate", "subagent_type", "parent_agent", "role", "route_id", "spawn_id")  # str or null
SPAWN_LIST_KEYS = ("jev_skills", "spawner_skills")
OPTIONAL = ("correct_skills", "sample", "source", "spawn_verdict", "verdict_source", "none_fired", "consult") \
    + SPAWN_STR_KEYS + SPAWN_LIST_KEYS
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
    is_spawn = rec.get("source") == "spawn"
    if rec["pd_review"] == "disagree" and not rec["pd_reason"].strip() and not is_spawn:
        errs.append("pd_reason is required when pd_review is disagree")
    errs.extend(_validate_spawn_keys(rec))
    if "correct_skills" in rec:
        cs = rec["correct_skills"]
        if not isinstance(cs, list) or not cs or not all(isinstance(x, str) and x for x in cs):
            errs.append("correct_skills must be a non-empty list of skill names")
    if "sample" in rec and not isinstance(rec["sample"], bool):
        errs.append("sample must be a bool")
    if isinstance(rec["task_text"], str) and holds_secret(rec["task_text"]):
        errs.append("task_text must not hold a secret (jev_client.redact would change it)")
    return errs


def _validate_spawn_keys(rec):
    errs = []
    if "source" in rec:
        if rec["source"] != "spawn":
            errs.append('source must be "spawn"')
        elif rec["tool"] != "skill-route":
            errs.append("source spawn requires tool skill-route")
    for k, allowed in (("spawn_verdict", SPAWN_VERDICTS), ("verdict_source", VERDICT_SOURCES), ("consult", CONSULTS)):
        if k in rec and rec[k] not in allowed:
            errs.append("%s must be one of %s" % (k, (allowed,)))
    for k in SPAWN_STR_KEYS:
        if k in rec and rec[k] is not None and not isinstance(rec[k], str):
            errs.append("%s must be a string or null" % k)
    for k in SPAWN_LIST_KEYS:
        if k in rec and (not isinstance(rec[k], list) or not all(isinstance(x, str) and x for x in rec[k])):
            errs.append("%s must be a list of non-empty strings" % k)
    if "none_fired" in rec and not isinstance(rec["none_fired"], bool):
        errs.append("none_fired must be a bool")
    return errs


def compute_mismatch(rec, outcome):
    """outcome_mismatch rules. Returns (bool, error_or_None)."""
    if outcome == "ok":
        return False, None
    if outcome == "wrong_skill":
        if rec.get("source") == "spawn":
            # mismatch against Jev only when Jev's pick actually ran (a Jev miss, not a spawner override)
            jev = set(rec.get("jev_skills") or [])
            return bool(jev) and set(rec.get("spawner_skills") or []) == jev, None
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


def append_spawn_record(rec, path=None):
    """Validate and append one automatic spawn record. Returns the error list (empty == written). Never raises."""
    try:
        if not isinstance(rec, dict):
            return ["record is not an object"]
        rec = dict(rec)
        rec.setdefault("source", "spawn")
        rec.setdefault("ts", now_iso())
        errs = validate_record(rec)
        if errs:
            return errs
        path = path or default_log()
        with Locked(path):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return []
    except Exception as e:  # noqa: BLE001 - the recorder must never break a spawn
        return ["error: %s: %s" % (type(e).__name__, e)]


def default_spawn_logs():
    """{root}/logs/spawns.jsonl plus every project memory/spawns.jsonl in medium-term.md (backtick path column)."""
    home = os.path.expanduser("~")
    root = agency_root(home)
    logs = [os.path.join(root, "logs", "spawns.jsonl")]
    medium_term = os.path.join(root, "memory", "medium-term.md")
    try:
        with open(medium_term, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\|[^|]+\|\s*`([^`]+)`", line)
                if not m:
                    continue
                raw = m.group(1).replace("~", home).rstrip("/")
                root = (raw[:-7] if raw.endswith("/memory") else raw).rstrip("/")
                cand = os.path.join(root, "memory", "spawns.jsonl") if root else ""
                if cand and cand not in logs:
                    logs.append(cand)
    except OSError:
        pass
    return logs


def _spawn_end_index(spawn_logs):
    """spawn_id -> last spawn_end row across the given logs."""
    idx = {}
    for p in spawn_logs:
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if '"spawn_end"' not in line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict) and row.get("event") == "spawn_end" and row.get("spawn_id"):
                        idx[row["spawn_id"]] = row
        except OSError:
            continue
    return idx


def reconcile(feedback_path=None, spawn_logs=None):
    """Fill outcome on open spawn records from spawn_end rows. Returns {checked, updated_ok, updated_wrong_skill}."""
    path = feedback_path or default_log()
    summary = {"checked": 0, "updated_ok": 0, "updated_wrong_skill": 0}
    if not os.path.exists(path):
        return summary
    idx = _spawn_end_index(spawn_logs if spawn_logs is not None else default_spawn_logs())
    with Locked(path):
        recs = read_records(path)
        changed = False
        for r in recs:
            if not isinstance(r, dict) or r.get("sample") or r.get("source") != "spawn":
                continue
            if r.get("outcome") is not None or not r.get("spawn_id"):
                continue
            summary["checked"] += 1
            end = idx.get(r["spawn_id"])
            if not end:
                continue
            if end.get("skill_mismatch") is True:
                outcome = "wrong_skill"
            elif end.get("outcome") == "DONE":
                outcome = "ok"
            else:
                continue
            mm, err = compute_mismatch(r, outcome)
            if err:
                continue
            r["outcome"] = outcome
            r["outcome_mismatch"] = mm
            summary["updated_ok" if outcome == "ok" else "updated_wrong_skill"] += 1
            changed = True
        if changed:
            write_all(path, recs)
    return summary


def cmd_reconcile(a):
    print(json.dumps(reconcile(a.file or None, a.spawn_logs)))
    return 0


def _bump(d, k):
    k = "(none)" if k is None or k == "" else str(k)
    d[k] = d.get(k, 0) + 1


def spawn_stats(path):
    recs = [r for r in read_records(path)
            if isinstance(r, dict) and not r.get("sample") and r.get("source") == "spawn"]
    total = len(recs)
    by_gate = {}
    by_source, by_parent, outcomes = {}, {}, {}
    accept = {"all": 0}
    gate_total = {}
    reviewed = 0
    accept_reviewed = 0
    mismatches = 0
    for r in recs:
        gate = r.get("gate") or "(none)"
        verdict = r.get("spawn_verdict") or "(none)"
        by_gate.setdefault(gate, {})
        _bump(by_gate[gate], verdict)
        gate_total[gate] = gate_total.get(gate, 0) + 1
        _bump(by_source, r.get("verdict_source"))
        _bump(by_parent, r.get("parent_agent"))
        _bump(outcomes, r.get("outcome") if r.get("outcome") is not None else "pending")
        if verdict == "accept":
            accept["all"] += 1
            accept[gate] = accept.get(gate, 0) + 1
        if verdict != "unreviewed":
            reviewed += 1
            if verdict == "accept":
                accept_reviewed += 1
        if r.get("outcome_mismatch") is True:
            mismatches += 1
    rate = lambda n, d: round(n / float(d), 4) if d else None  # noqa: E731
    return {
        "total": total,
        "by_gate_spawn_verdict": by_gate,
        "by_verdict_source": by_source,
        "by_parent_agent": by_parent,
        "agreement_rate": rate(accept["all"], total),
        "agreement_rate_reviewed": rate(accept_reviewed, reviewed),
        "agreement_rate_by_gate": {g: rate(accept.get(g, 0), n) for g, n in gate_total.items()},
        "outcomes": outcomes,
        "jev_mismatch_count": mismatches,
    }


def cmd_spawn_stats(a):
    print(json.dumps(spawn_stats(a.file or default_log()), ensure_ascii=False, sort_keys=True))
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
    s.add_argument("--review", required=True, choices=CLI_REVIEWS, help="reviewer's call on the verdict")
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
    r = sub.add_parser("reconcile", help="fill outcome on spawn records from spawn_end rows")
    r.add_argument("--spawn-logs", nargs="+", default=None, metavar="FILE",
                   help="spawns.jsonl files (default: {root}/logs/spawns.jsonl + project logs from medium-term.md)")
    r.set_defaults(fn=cmd_reconcile)
    t = sub.add_parser("spawn-stats", help="print JSON stats over source-spawn records")
    t.set_defaults(fn=cmd_spawn_stats)
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

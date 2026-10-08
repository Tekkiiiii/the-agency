#!/usr/bin/env python3
"""skill-route-eval.py - score the Jev skill router against a seed set of labelled tasks.

  AGENCY_SKILL_ROUTER=1 skill-route-eval.py --router jev --mode two-stage --split all [--limit N] [--concurrency 4]

OPT-IN, NETWORK-CAPABLE (maintainer / advanced tool). It calls the router once per seed case, and the router calls the Jev
endpoint (and falls back to `claude -p`). It therefore refuses to run unless the router is enabled: with AGENCY_SKILL_ROUTER
unset (or not "1") it prints "skill router disabled (set AGENCY_SKILL_ROUTER=1 to run skill-route-eval.py); nothing run"
and exits 0 before it imports anything router-related, starts a server or runs a subprocess.

{root} below is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.

Runs skill-route.py from the directory of this script (override: env SKILL_ROUTE_CMD, shlex-split; used by unit tests and
stubs) once per seed case with `--router R --mode M`, task text on stdin, env JEV_PURPOSE=eval so the shared client logs the
call to jev-usage.jsonl with purpose "eval" (we do NOT pass --no-log; eval calls must be cost-logged).
Seed: {root}/evals/skill-route/seed.jsonl (override: --seed). THE SEED IS NOT SHIPPED with the-agency: you write your own
labelled tasks, one JSON object per line:
  {"id": "t1", "task": "build a React landing page", "expected_skills": ["frontend"], "split": "dev|holdout",
   "lang": "en", "source": "hand"}              (split, lang and source are optional: dev / en / unknown)
plus confirmed skill-route mismatches from {root}/memory/metrics/jev-feedback.jsonl (source "feedback", split dev; "sample"
records are ignored). Then runs prerules.jsonl assertions ({root}/evals/skill-route/prerules.jsonl, also not shipped; skipped
with a note when absent): each case runs against a loopback counting server (503) with a bogus key, in an isolated env (temp
state dir, temp usage log, JEV_NOTIFY=0, JEV_EMIT=0; the real jev-down flag is never touched). `claude` is replaced by a
counting stub (JEV_HAIKU_CMD; it appends one line per invocation to a temp file, then exits 1, so a Haiku fallback degrades to
grep and never spends a real call), so every case counts BOTH Jev requests (loopback server) and Haiku invocations (stub).
Expect keys: router, router_in, jev_requests (exact), jev_requests_min, haiku_requests (exact), lang, skills_include,
skills_any, skills_exclude, pre_rules_include.

Metrics: top-1 (router top-1 in expected_skills), top-3 (any returned skill in expected), gate-pass rate, top-1 among
gate=pass, per-source / per-split / per-lang tables, cost (sum of `usd` in jev-usage.jsonl rows with purpose eval written
during the run). Results: {root}/evals/skill-route/results/{YYYY-MM-DD}-{router}-{mode}-{split}.json (local date) with every miss.
Seed flags: a record with "unscored": true is NOT sent to the router and is excluded
from every metric (it is listed on a separate "unscored" line and kept in the results rows with unscored=true). A record with
"expected_none": true (expected_skills == []) means "no skill fits": top-1 and top-3 are correct iff the router returns an
empty skills list. An empty skills list on a normal record is a miss (never a crash). Every results row carries the
`expected_none` and `unscored` flags so jev-gate-check.py can recompute from raw rows.
Exit code: 0 ok (or disabled), 1 if any prerules assertion failed, 2 on usage/IO errors (including a missing seed with no
feedback cases).
Stdlib only, Python 3.9 compatible.
"""
import argparse
import collections
import concurrent.futures
import datetime
import http.server
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time


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


ROOT = agency_root(os.path.expanduser("~"))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CMD = [sys.executable, os.path.join(SCRIPTS_DIR, "skill-route.py")]
EVAL_DIR = os.path.join(ROOT, "evals", "skill-route")
METRICS_DIR = os.path.join(ROOT, "memory", "metrics")


# ---------------------------------------------------------------- loading
def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                sys.stderr.write("warning: %s line %d not JSON, skipped\n" % (path, n))
    return out


def load_seed(path):
    cases = read_jsonl(path)
    for c in cases:
        c.setdefault("split", "dev")
        c.setdefault("lang", "en")
        c.setdefault("source", "unknown")
    return cases


def load_feedback_cases(path):
    """Confirmed skill-route mismatches become regression cases (source 'feedback')."""
    cases, skipped = [], 0
    for r in read_jsonl(path):
        if r.get("sample") or r.get("tool") != "skill-route" or r.get("outcome_mismatch") is not True:
            continue
        exp = r.get("correct_skills")
        text = r.get("task_text") or ""
        if not exp or not text:
            skipped += 1
            sys.stderr.write("warning: feedback %s skipped (needs task_text and correct_skills)\n" % r.get("task_id"))
            continue
        cases.append({"id": "fb-%s-%s" % (r.get("project", "?"), r.get("task_id", "?")), "task": text, "expected_skills": list(exp),
                      "source": "feedback", "split": "dev", "lang": "en", "notes": "confirmed mismatch from jev-feedback.jsonl"})
    return cases, skipped


# ---------------------------------------------------------------- running
def router_cmd():
    env = os.environ.get("SKILL_ROUTE_CMD")
    return shlex.split(env) if env else list(DEFAULT_CMD)


def run_router(task, router, mode, project=None, extra=None, env_over=None, timeout=180):
    """Run one routing call. Returns (result_dict_or_None, error_or_None, latency_ms)."""
    cmd = router_cmd()
    if router:
        cmd += ["--router", router]
    if mode:
        cmd += ["--mode", mode]
    if project:
        cmd += ["--project", project]
    cmd += list(extra or [])
    env = dict(os.environ)
    env["JEV_PURPOSE"] = "eval"
    env.update(env_over or {})
    t0 = time.time()
    try:
        p = subprocess.run(cmd, input=task, capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout", int((time.time() - t0) * 1000)
    except OSError as e:
        return None, "exec error: %s" % e, int((time.time() - t0) * 1000)
    ms = int((time.time() - t0) * 1000)
    if p.returncode != 0:
        return None, "exit %d: %s" % (p.returncode, (p.stderr or "").strip()[-200:]), ms
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")
    except ValueError:
        return None, "unparseable stdout: %r" % p.stdout[-200:], ms
    if not isinstance(res, dict) or not isinstance(res.get("skills"), list):
        return None, "contract violation (no skills list)", ms
    return res, None, ms


def evaluate_case(case, router, mode):
    exp = list(case.get("expected_skills") or [])
    none_ok = bool(case.get("expected_none"))
    base = {"id": case["id"], "source": case["source"], "split": case["split"], "lang": case.get("lang", "en"),
            "task": case["task"], "expected": exp, "expected_none": none_ok, "unscored": bool(case.get("unscored"))}
    if base["unscored"]:  # excluded by design: no router call, no cost, counted in no metric
        base.update(latency_ms=0, error=None, top1=False, top3=False, gate=None, skills=[], router_used=None,
                    unscored_reason=case.get("unscored_reason", ""))
        return base
    res, err, ms = run_router(case["task"], router, mode)
    row = dict(base, latency_ms=ms)
    if err:
        row.update(error=err, top1=False, top3=False, gate=None, skills=[], router_used=None)
        return row
    skills = [str(s) for s in res.get("skills", [])]
    row.update(skills=skills, gate=res.get("gate"), router_used=res.get("router"), domain=res.get("domain"),
               jev_down=bool(res.get("jev_down")), error=None,
               **score_skills(skills, exp, none_ok))
    return row


def score_skills(skills, exp, expected_none=False):
    """top-1 / top-3 correctness for one routed case. expected_none: correct iff the router returned no skill at all.
    An empty skills list on a normal case is a miss (never an error)."""
    if expected_none:
        ok = not skills
        return {"top1": ok, "top3": ok}
    return {"top1": bool(skills) and skills[0] in exp, "top3": any(s in exp for s in skills[:3])}


def run_cases(cases, router, mode, concurrency):
    rows = [None] * len(cases)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = {ex.submit(evaluate_case, c, router, mode): i for i, c in enumerate(cases)}
        for f in concurrent.futures.as_completed(futs):
            rows[futs[f]] = f.result()
    return rows


# ---------------------------------------------------------------- scoring
def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def summarize(rows):
    n = len(rows)
    g = [r for r in rows if r.get("gate") == "pass"]
    return {"n": n,
            "top1": pct(sum(1 for r in rows if r["top1"]), n),
            "top3": pct(sum(1 for r in rows if r["top3"]), n),
            "gate_pass_rate": pct(len(g), n),
            "top1_among_gate_pass": pct(sum(1 for r in g if r["top1"]), len(g)),
            "n_gate_pass": len(g),
            "errors": sum(1 for r in rows if r.get("error"))}


def group(rows, key):
    d = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: str(r[key])):
        d.setdefault(r[key], []).append(r)
    return collections.OrderedDict((k, summarize(v)) for k, v in d.items())


def usage_cost(since_epoch, log_path=None):
    """Sum usd + calls of purpose=eval rows in the jev usage log written at/after since_epoch."""
    path = log_path or os.environ.get("JEV_USAGE_LOG") or os.path.join(METRICS_DIR, "jev-usage.jsonl")
    usd, calls, by_router = 0.0, 0, collections.Counter()
    for r in read_jsonl(path):
        if r.get("purpose") != "eval":
            continue
        try:
            ts = datetime.datetime.strptime(r["ts"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
        except (KeyError, ValueError):
            continue
        if ts + 1 < since_epoch:
            continue
        usd += float(r.get("usd") or 0.0)
        calls += 1
        by_router[r.get("router", "?")] += 1
    return {"usd": round(usd, 6), "calls": calls, "by_router": dict(by_router)}


# ---------------------------------------------------------------- prerules
class _Counter(http.server.BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        self.server.hits += 1
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)  # drain body; never stored or logged (it may carry an auth header we ignore)
        except Exception:
            pass
        self.send_response(503)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_POST  # noqa: N815

    def log_message(self, *a):  # silence
        pass


def start_counter():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Counter)
    srv.hits = 0
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def check_expect(expect, res, hits, haiku=0):
    """Return list of failure strings for one prerules case. hits = Jev requests, haiku = Haiku invocations."""
    f = []
    skills = [str(s) for s in res.get("skills", [])]
    if "router" in expect and res.get("router") != expect["router"]:
        f.append("router %r != %r" % (res.get("router"), expect["router"]))
    if "router_in" in expect and res.get("router") not in expect["router_in"]:
        f.append("router %r not in %r" % (res.get("router"), expect["router_in"]))
    if "jev_requests" in expect and hits != expect["jev_requests"]:
        f.append("jev requests %d != %d" % (hits, expect["jev_requests"]))
    if "haiku_requests" in expect and haiku != expect["haiku_requests"]:
        f.append("haiku invocations %d != %d" % (haiku, expect["haiku_requests"]))
    if "jev_requests_min" in expect and hits < expect["jev_requests_min"]:
        f.append("jev requests %d < %d (Jev must be allowed)" % (hits, expect["jev_requests_min"]))
    for r in expect.get("pre_rules_include", []):
        if r not in (res.get("pre_rules") or []):
            f.append("pre_rule %s missing from %r" % (r, res.get("pre_rules")))
    if "lang" in expect and res.get("lang") != expect["lang"]:
        f.append("lang %r != %r" % (res.get("lang"), expect["lang"]))
    for s in expect.get("skills_include", []):
        if s not in skills:
            f.append("skill %s missing from %r" % (s, skills))
    if expect.get("skills_any") and not any(s in skills for s in expect["skills_any"]):
        f.append("none of %r in %r" % (expect["skills_any"], skills))
    for s in expect.get("skills_exclude", []):
        if s in skills:
            f.append("skill %s must not be present, got %r" % (s, skills))
    return f


def _count_lines(path):
    try:
        with open(path, "r") as f:
            return sum(1 for ln in f if ln.strip())
    except OSError:
        return 0


def run_prerules(path, mode):
    cases = read_jsonl(path)
    if not cases:
        return []
    srv = start_counter()
    tmpd = tempfile.mkdtemp(prefix="skill-route-eval-")
    envfile = os.path.join(tmpd, "bogus.env")
    with open(envfile, "w") as f:  # BOGUS key only: the counting server must never see the real key
        f.write("TYPESAFE_API_KEY=bogus-eval-key-not-real\nJEV_MODEL=jev-latest\n")
    # Isolated: a case that IS allowed to call Jev hits the 503 counter; that must not raise the real jev-down flag,
    # notify, emit, write the real usage log, or spend a real Haiku call (the stub counts the invocation and fails ->
    # grep after the miss). Do NOT set SKILL_ROUTE_CHILD: it would hide a Haiku call the router should not make.
    haiku_log = os.path.join(tmpd, "haiku-calls.txt")
    haiku_stub = os.path.join(tmpd, "claude-stub.sh")
    with open(haiku_stub, "w") as f:
        f.write("#!/bin/sh\necho call >> '%s'\nexit 1\n" % haiku_log)
    os.chmod(haiku_stub, 0o700)
    env = {"JEV_ENDPOINT": "http://127.0.0.1:%d/v1/systemone" % srv.server_address[1], "JEV_ENV_FILE": envfile,
           "SKILL_ROUTE_STATE_DIR": os.path.join(tmpd, "state"), "JEV_USAGE_LOG": os.path.join(tmpd, "usage.jsonl"),
           "JEV_NOTIFY_LOG": os.path.join(tmpd, "notify.log"), "JEV_NOTIFY": "0", "JEV_EMIT": "0",
           "JEV_HAIKU_CMD": haiku_stub, "SKILL_ROUTE_CHILD": "", "AGENCY_SKILL_ROUTER": "1"}
    results = []
    try:
        for c in cases:
            before = srv.hits
            h_before = _count_lines(haiku_log)
            res, err, ms = run_router(c["task"], None, mode, project=c.get("project"), extra=c.get("args"), env_over=env)
            hits = srv.hits - before
            haiku = _count_lines(haiku_log) - h_before
            if err:
                results.append({"id": c["id"], "pass": False, "failures": ["router call failed: %s" % err],
                                "jev_requests": hits, "haiku_requests": haiku})
                continue
            fails = check_expect(c.get("expect", {}), res, hits, haiku)
            results.append({"id": c["id"], "pass": not fails, "failures": fails, "jev_requests": hits,
                            "haiku_requests": haiku,
                            "router": res.get("router"), "skills": res.get("skills"), "lang": res.get("lang"),
                            "pre_rules": res.get("pre_rules")})
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmpd, ignore_errors=True)
    return results


# ---------------------------------------------------------------- output
def fmt(v):
    return "-" if v is None else ("%.1f" % v)


def print_table(title, groups):
    print("\n%s" % title)
    print("  %-18s %5s %7s %7s %9s %12s %4s" % ("", "n", "top1%", "top3%", "gatepass%", "top1|pass%", "err"))
    for k, s in groups.items():
        print("  %-18s %5d %7s %7s %9s %12s %4d" % (str(k)[:18], s["n"], fmt(s["top1"]), fmt(s["top3"]), fmt(s["gate_pass_rate"]),
                                                  fmt(s["top1_among_gate_pass"]), s["errors"]))


def router_enabled():
    """The single opt-in switch. Inlined (not jev_client.router_enabled) so the refusal happens before any router import."""
    return os.environ.get("AGENCY_SKILL_ROUTER") == "1"


def main(argv=None):
    if not router_enabled():
        print("skill router disabled (set AGENCY_SKILL_ROUTER=1 to run skill-route-eval.py); nothing run")
        return 0
    ap = argparse.ArgumentParser(description="Score skill-route.py against a labelled seed set (needs AGENCY_SKILL_ROUTER=1)")
    ap.add_argument("--router", choices=["jev", "haiku", "grep"], default="jev")
    ap.add_argument("--mode", choices=["two-stage", "flat"], default="two-stage")
    ap.add_argument("--split", choices=["dev", "holdout", "all"], default="all")
    ap.add_argument("--limit", type=int, default=0, help="only the first N cases after split filter")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", default=os.path.join(EVAL_DIR, "seed.jsonl"),
                    help="labelled seed cases, JSONL (default {root}/evals/skill-route/seed.jsonl; NOT shipped, write your own)")
    ap.add_argument("--prerules", default=os.path.join(EVAL_DIR, "prerules.jsonl"))
    ap.add_argument("--feedback", default=os.environ.get("JEV_FEEDBACK_LOG") or os.path.join(METRICS_DIR, "jev-feedback.jsonl"))
    ap.add_argument("--results-dir", default=os.path.join(EVAL_DIR, "results"))
    ap.add_argument("--skip-prerules", action="store_true")
    ap.add_argument("--prerules-only", action="store_true")
    a = ap.parse_args(argv)

    started = time.time()
    sys.path.insert(0, SCRIPTS_DIR)
    import jev_fingerprint  # noqa: E402  (after the switch check: nothing router-related is imported while disabled)
    fp_fields = jev_fingerprint.fingerprint_fields()   # at run START: an edit mid-run must not be stamped as evaluated
    summary = {}
    rows = []
    skipped_fb = 0
    if not a.prerules_only:
        seed_missing = not os.path.exists(a.seed)
        cases = load_seed(a.seed)
        fb, skipped_fb = load_feedback_cases(a.feedback)
        cases += fb
        if seed_missing:
            sys.stderr.write("seed file not found: %s\n"
                             "  The eval seed is NOT shipped with the-agency. Create it as JSONL, one labelled task per line,\n"
                             "  e.g. {\"id\": \"t1\", \"task\": \"build a React landing page\", \"expected_skills\": [\"frontend\"]},\n"
                             "  or point --seed at your own file. See the docstring of this script for every field.\n" % a.seed)
        if a.split != "all":
            cases = [c for c in cases if c["split"] == a.split]
        if a.limit and a.limit > 0:
            cases = cases[:a.limit]
        if not cases:
            sys.stderr.write("no cases selected%s\n" % (" (no seed file and no confirmed feedback cases)" if seed_missing else ""))
            return 2
        rows = run_cases(cases, a.router, a.mode, a.concurrency)
        unscored = [r for r in rows if r.get("unscored")]
        scored = [r for r in rows if not r.get("unscored")]
        summary = {"overall": summarize(scored), "by_source": group(scored, "source"), "by_split": group(scored, "split"),
                   "by_lang": group(scored, "lang"),
                   "unscored": {"n": len(unscored), "ids": [r["id"] for r in unscored]},
                   "expected_none": {"n": sum(1 for r in scored if r.get("expected_none")),
                                     "top1": pct(sum(1 for r in scored if r.get("expected_none") and r["top1"]),
                                                 sum(1 for r in scored if r.get("expected_none")))}}
        print("skill-route eval: router=%s mode=%s split=%s n=%d scored (feedback cases: %d)" % (a.router, a.mode, a.split, len(scored), len(fb)))
        print("  unscored (excluded from all metrics): %d %s" % (len(unscored), [r["id"] for r in unscored]))
        if summary["expected_none"]["n"]:
            print("  expected_none (router must return no skill): %d cases, %s%% correct" % (
                summary["expected_none"]["n"], fmt(summary["expected_none"]["top1"])))
        o = summary["overall"]
        print("  top-1 %s%%   top-3 %s%%   gate-pass %s%%   top-1 among gate=pass %s%% (n=%d)   errors %d" % (
            fmt(o["top1"]), fmt(o["top3"]), fmt(o["gate_pass_rate"]), fmt(o["top1_among_gate_pass"]), o["n_gate_pass"], o["errors"]))
        print_table("per source", summary["by_source"])
        print_table("per split", summary["by_split"])
        print_table("per lang", summary["by_lang"])

    pre = []
    if not a.skip_prerules:
        pre = run_prerules(a.prerules, a.mode)
        if not pre:
            print("\nprerules: none (no cases in %s; the prerules file is not shipped)" % a.prerules)
        else:
            print("\nprerules assertions: %d/%d passed" % (sum(1 for r in pre if r["pass"]), len(pre)))
        for r in pre:
            print("  %-10s %s %s" % (r["id"], "PASS" if r["pass"] else "FAIL", "; ".join(r["failures"])))

    cost = usage_cost(started)
    if not a.prerules_only:
        misses = [r for r in scored if not r["top1"]]
        print("\ncost (purpose=eval rows in jev-usage.jsonl during this run): $%.6f over %d calls %s" % (cost["usd"], cost["calls"], cost["by_router"]))
        print("misses: %d (listed in the results file)" % len(misses))
        for m in misses[:15]:
            print("  MISS %-9s expected=%s got=%s%s" % (m["id"], "NONE" if m.get("expected_none") else m["expected"][:3], m["skills"][:3], "  ERROR " + m["error"] if m.get("error") else ""))
        os.makedirs(a.results_dir, exist_ok=True)
        out = os.path.join(a.results_dir, "%s-%s-%s-%s.json" % (datetime.date.today().isoformat(), a.router, a.mode, a.split))
        doc = {"meta": {"date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "router": a.router, "mode": a.mode,
                        "split": a.split, "n": len(scored), "n_unscored": len(unscored), "seed": a.seed,
                        "feedback_cases": len(rows) and sum(1 for r in rows if r["source"] == "feedback"),
                        "feedback_skipped": skipped_fb, "cmd": router_cmd()[-1], "purpose_env": "JEV_PURPOSE=eval"},
               "summary": summary, "cost": cost, "misses": misses, "prerules": pre, "rows": rows}
        doc.update(fp_fields)   # inputs_fingerprint (code AST + routable menu, see jev_fingerprint.py) for jev-gate-check.py
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        print("results: %s" % out)
    return 1 if any(not r["pass"] for r in pre) else 0


if __name__ == "__main__":
    sys.exit(main())

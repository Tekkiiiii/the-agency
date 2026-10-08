#!/usr/bin/env python3
"""jev-gate-check.py - readiness gate for the skill router (scripts/skill-route.py).

The script is the judge, not memory: every criterion is computed from files on disk. This tool is OFFLINE:
it never opens a network connection and never calls the router or the Jev endpoint, so it runs the same
whether or not the router is enabled (AGENCY_SKILL_ROUTER=1) and without any API key. It only reads result
files and logs, plus one live menu build (the menu-build criterion).

{root} below is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.

Criteria
  menu-build                the skill menu builds FRESH: skill-route.py is loaded (importlib) from the directory of THIS
                            script (not JEV_GATE_SCRIPTS_DIR) and load_menu(rebuild=True) must succeed. FAIL when the build
                            raises (MenuError, e.g. a skill dir with no overlay entry, or any other exception such as a
                            corrupt overlay or an import failure; never a crash, never exit 2). SystemExit raised during the
                            build or the module import counts as a failure too. The value names the offending skills
                            ("no overlay entry: a, b") and the fix (skill-route-overlay-add.py); when other problems are
                            listed too, the generic "fix the overlay" hint is printed as well. No Jev call, no network,
                            no cost. NOT subject to the staleness guard: it is computed live on every run. Side effect: each
                            run rebuilds and rewrites the menu cache (SKILL_ROUTE_STATE_DIR/skill-route-menu.json, the normal
                            load_menu side effect); set SKILL_ROUTE_STATE_DIR to a temp dir in CI. This is the check to run
                            in CI and after installing a skill: `jev-gate-check.py --only menu-build`.
                            Listed first: a dead menu makes every router number below meaningless.

The three criteria below are maintainer / advanced checks. They only read result files that the opt-in tools write
(skill-route-eval.py, jev-drill.py, the router's shadow log) and fail with a "run: <command>" hint when those do not exist.
  skill-route-gated-accuracy  latest skill-route eval, router=jev, split=all, mode=<DEFAULT_MODE read from skill-route.py>:
                            accuracy among gate=pass rows >= 0.95 AND coverage (share of scored rows with gate=pass)
                            >= COVERAGE_FLOOR (0.70, one constant); no outage rows (jev_down) in the run. Computed from the
                            raw rows: a confident answer must be right, but the router may not buy accuracy by abstaining on
                            most tasks. Raw top-1 (all scored rows) is INFO.
  outage-drill              latest drill result: steps s1-s4 ran and pass is true for skill-route.
  shadow-window             window start = earliest ts over skill-route-shadow.jsonl and jev-feedback.jsonl (records with
                            "sample": true ignored). Met when now - start >= 7 days OR gated tasks >= 50.
Gated-task count (conservative, no double counting) =
    skill-route shadow records that carry actual skills
  + jev-feedback records not already represented (task_id not equal to a shadow spawn_id).
Staleness guard (content hash, not mtime): the writers (skill-route-eval.py, jev-drill.py) stamp "inputs_fingerprint" into
every result (scripts/jev_fingerprint.py: sha256 of the AST of skill-route.py and jev_client.py - comments, docstrings,
formatting and mtimes do not count - plus the ROUTABLE skill menu: name, description, triggers, domain, also_domains, hint per
skill, and the overlay domains / vi_map / en_only). The gate recomputes it once per run; an eval or drill result counts only
when its fingerprint equals the current one. A result without one is stale ("result has no inputs_fingerprint"), a changed one
is stale ("inputs changed since the run (code or routable menu)"); both print "stale - re-run <command>". An exclude-only overlay
addition, or touching any file, does NOT stale a result; a change to router code or to a routable skill's description /
triggers / domain / hint does. If the fingerprint cannot be computed (a broken menu) the guarded criteria FAIL with
"cannot fingerprint inputs: <error>" (never a crash, never exit 2).
Scoring rules for the skill-route rows: rows with unscored=true are excluded from the accuracy/coverage/top-1 computation (and
from the holdout INFO and the coverage denominator); rows with expected_none=true are correct iff the router returned no skill
(row top1 is trusted when present, else recomputed as "skills == []").
Informational (never a pass criterion): raw top-1, holdout top-1, reviewer-agree rate (agree / reviewed).

Usage: jev-gate-check.py [--json] [--only NAME ...]
  --only NAME   evaluate only the named criterion (repeatable; NAME is one of the four above). The exit code and OVERALL
                line then cover just the selected criteria, and nothing else is computed: `--only menu-build` does not read
                any result file, DEFAULT_MODE or the fingerprint.
Output: one line per criterion `PASS|FAIL name: value (threshold) source-file`, INFO lines, then `OVERALL PASS|FAIL`.
Timestamps are printed in UTC with a Z suffix (inputs with an offset are converted).
Exit: 0 only on overall PASS, 1 on FAIL, 2 on input error (bad args, unknown --only name; the default mode cannot be
determined). Missing or unreadable result/log files are a FAIL of that criterion, never a crash.

Env overrides (every input path; tests use them)
  JEV_GATE_SCRIPTS_DIR        dir holding skill-route.py (DEFAULT_MODE; its load_menu feeds the fingerprint) and jev_client.py
                              (the two fingerprinted code files); default: the directory of this script
  JEV_GATE_SKILL_ROUTE_RESULTS, JEV_GATE_DRILL_RESULTS   result dirs
  JEV_GATE_SKILL_ROUTE_SHADOW, JEV_GATE_FEEDBACK         jsonl files (feedback also honours JEV_FEEDBACK_LOG, like jev-feedback.py)
  JEV_GATE_SKILL_ROUTE_MODE   skip reading DEFAULT_MODE from skill-route.py
  JEV_GATE_NOW                ISO timestamp used as "now"
  SKILL_ROUTE_SKILLS_DIR, SKILL_ROUTE_OVERLAY, SKILL_ROUTE_STATE_DIR
                              not gate variables: skill-route.py honours them and the menu-build criterion and the
                              fingerprint let them flow through untouched (skills dir, overlay json, menu cache dir), so
                              tests use temp dirs
Defaults: results {root}/evals/skill-route/results and {root}/evals/jev-drill/results; shadow log and feedback log
{root}/memory/metrics/skill-route-shadow.jsonl and {root}/memory/metrics/jev-feedback.jsonl.
Stdlib only; Python 3.9 compatible.
"""
import argparse
import datetime
import glob
import importlib.util
import itertools
import json
import os
import re
import shlex
import sys


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
EVAL_THRESHOLD = 0.95
COVERAGE_FLOOR = 0.70          # skill-route: min share of scored rows the router answers confidently (gate=pass)
WINDOW_DAYS = 7
WINDOW_TASKS = 50
DRILL_STEPS = ["s1", "s2", "s3", "s4"]
DRILL_TOOLS = ("skill-route",)
CRITERIA = ("menu-build", "skill-route-gated-accuracy", "outage-drill", "shadow-window")
GATE_DIR = os.path.dirname(os.path.abspath(__file__))     # menu-build loads skill-route.py from here
OVERLAY_ADD = "python3 %s" % shlex.quote(os.path.join(GATE_DIR, "skill-route-overlay-add.py"))
ROUTER_ON = "AGENCY_SKILL_ROUTER=1 "                      # prefix of the maintainer commands the gate prints (they need the switch)
_LOAD_SEQ = itertools.count(1)


class InputError(Exception):
    pass


# ---------------------------------------------------------------- paths
def _env(name, default):
    return os.environ.get(name) or default


def scripts_dir():
    return _env("JEV_GATE_SCRIPTS_DIR", GATE_DIR)


def p_skill_results():
    return _env("JEV_GATE_SKILL_ROUTE_RESULTS", os.path.join(ROOT, "evals", "skill-route", "results"))


def p_drill_results():
    return _env("JEV_GATE_DRILL_RESULTS", os.path.join(ROOT, "evals", "jev-drill", "results"))


def p_skill_shadow():
    return _env("JEV_GATE_SKILL_ROUTE_SHADOW", os.path.join(ROOT, "memory", "metrics", "skill-route-shadow.jsonl"))


def p_feedback():
    return (os.environ.get("JEV_GATE_FEEDBACK") or os.environ.get("JEV_FEEDBACK_LOG")
            or os.path.join(ROOT, "memory", "metrics", "jev-feedback.jsonl"))


# ---------------------------------------------------------------- helpers
_TS_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")


def parse_ts(s):
    """ISO-8601 -> aware datetime (naive input is taken as UTC). None when unparseable."""
    if not isinstance(s, str):
        return None
    m = _TS_RE.match(s.strip())
    if not m:
        return None
    y, mo, d, h, mi, se, tz = m.groups()
    try:
        if tz in (None, "Z"):
            off = datetime.timedelta(0)
        else:
            sign = -1 if tz[0] == "-" else 1
            digits = tz[1:].replace(":", "")
            off = sign * datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        return datetime.datetime(int(y), int(mo), int(d), int(h), int(mi), int(se),
                                 tzinfo=datetime.timezone(off))
    except ValueError:
        return None


def now_utc():
    raw = os.environ.get("JEV_GATE_NOW")
    if raw:
        dt = parse_ts(raw)
        if dt is None:
            raise InputError("JEV_GATE_NOW is not an ISO timestamp: %r" % raw)
        return dt
    return datetime.datetime.now(datetime.timezone.utc)


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def read_jsonl(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("sample") is not True:
                    out.append(rec)
    except OSError:
        pass
    return out


def utc_stamp(dt):
    """Aware datetime -> 'YYYY-MM-DDTHH:MM:SSZ' in UTC (an offset input is converted, never relabelled)."""
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pct(x):
    return "n/a" if x is None else "%.1f%%" % (100.0 * x)


def ratio(num, den):
    return None if not den else float(num) / den


def crit(name, ok, value, threshold, source, detail=None):
    return {"name": name, "pass": bool(ok), "value": value, "threshold": threshold,
            "source": source, "detail": detail}


def router_enabled():
    """The single opt-in switch (same rule as jev_client.router_enabled). Read here only to report it: the gate never needs it."""
    return os.environ.get("AGENCY_SKILL_ROUTER") == "1"


# ---------------------------------------------------------------- default mode + staleness (content fingerprint)
def default_mode():
    env = os.environ.get("JEV_GATE_SKILL_ROUTE_MODE")
    if env:
        return env
    path = os.path.join(scripts_dir(), "skill-route.py")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
    except OSError as e:
        raise InputError("cannot read %s to learn DEFAULT_MODE: %s" % (path, e))
    m = re.search(r'(?m)^DEFAULT_MODE\s*=\s*["\']([^"\']+)["\']', txt)
    if not m:
        raise InputError("DEFAULT_MODE not found in %s" % path)
    return m.group(1)


def current_fingerprint():
    """(fingerprint, None) over scripts_dir(), or (None, one-line error) when the menu cannot be built. Never raises.

    jev_fingerprint is imported here, not at module top, so criteria that need no fingerprint (--only menu-build)
    have no dependency on it."""
    try:
        sys.path.insert(0, GATE_DIR)
        try:
            import jev_fingerprint
        finally:
            try:
                sys.path.remove(GATE_DIR)
            except ValueError:
                pass
        return jev_fingerprint.inputs_fingerprint(scripts_dir()), None
    except (Exception, SystemExit) as e:
        return None, _one_line(e)


def staleness(doc, cmd, cur):
    """None when the result was produced on the current inputs, else (criterion value, detail)."""
    fp, err = cur
    if fp is None:
        return "cannot fingerprint inputs: %s" % err, None
    got = doc.get("inputs_fingerprint")
    if not got:
        return "stale - re-run %s" % cmd, "result has no inputs_fingerprint (pre-content-hash result)"
    if got != fp:
        return "stale - re-run %s" % cmd, "inputs changed since the run (code or routable menu)"
    return None


def pick_latest(dirpath, matcher, ts_of):
    """Latest matching result in dirpath: (path, doc, datetime) or None. Unreadable files are skipped."""
    best = None
    for f in sorted(glob.glob(os.path.join(dirpath, "*.json"))):
        d = read_json(f)
        if d is None or not matcher(d):
            continue
        dt = ts_of(d)
        if dt is None:
            try:
                dt = datetime.datetime.fromtimestamp(os.path.getmtime(f), datetime.timezone.utc)
            except OSError:
                continue
        if best is None or dt > best[2]:
            best = (f, d, dt)
    return best


# ---------------------------------------------------------------- criteria
def _load_module(filename, tag):
    """Load GATE_DIR/<filename> under a unique module name (a test can load it twice without a collision)."""
    path = os.path.join(GATE_DIR, filename)
    spec = importlib.util.spec_from_file_location("jev_gate_%s_%d" % (tag, next(_LOAD_SEQ)), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_via_skill_route():
    return _load_module("skill-route.py", "skill_route").load_menu(rebuild=True)


def _one_line(exc):
    """Exception -> one line. A MenuError keeps its problem lines ('no overlay entry: a, b' grouped); others get the class name."""
    msg = str(exc)
    if exc.__class__.__name__ != "MenuError":
        return "%s: %s" % (exc.__class__.__name__, " ".join(msg.split()))
    problems = [l.strip() for l in msg.splitlines() if l.startswith("  ") and l.strip()]
    if not problems:
        return " ".join(msg.split())
    prefix = "no overlay entry: "
    missing = [l[len(prefix):] for l in problems if l.startswith(prefix)]
    rest = [l for l in problems if not l.startswith(prefix)]
    parts = ([prefix + ", ".join(missing)] if missing else []) + rest
    return "; ".join(parts)


def check_menu_build():
    """Build the skill menu fresh. Any failure is a FAIL of this criterion, never a crash."""
    name = "menu-build"
    thr = "load_menu(rebuild=True) succeeds for skill-route.py"
    overlay = os.environ.get("SKILL_ROUTE_OVERLAY") or os.path.join(GATE_DIR, "skill-route", "overlay.json")
    try:
        menu = _build_via_skill_route()
    except (Exception, SystemExit) as e:   # MenuError or anything else (corrupt overlay, import failure, sys.exit at import): FAIL, not a crash
        err = _one_line(e)
    else:
        value = "menu builds for skill-route.py (%d skills, %d excluded)" % (len(menu["skills"]), len(menu["excluded"]))
        return crit(name, True, value, thr, overlay)
    head = "for skill-route.py: %s" % err
    segments = [seg for seg in err.split("; ") if seg.strip()]
    has_missing = any("no overlay entry" in seg for seg in segments)
    has_other = any("no overlay entry" not in seg for seg in segments)
    fixes = []
    if has_missing:
        fixes.append("add overlay entries: %s <name>" % OVERLAY_ADD)
    if has_other or not has_missing:
        fixes.append("fix the overlay %s (python3 %s --rebuild-menu shows the full error)"
                     % (overlay, shlex.quote(os.path.join(GATE_DIR, "skill-route.py"))))
    fix = "; ".join(fixes)
    return crit(name, False, "menu build FAILED %s. Fix: %s" % (head, fix), thr, overlay)


def row_top1(r):
    """Top-1 correctness of one skill-route result row. expected_none rows: correct iff no skill returned."""
    if "top1" in r:
        return bool(r.get("top1"))
    if r.get("expected_none"):
        return not r.get("error") and not r.get("skills")
    return False


def check_skill_route(mode, cur):
    d = p_skill_results()
    name = "skill-route-gated-accuracy"
    thr = "accuracy >= %s AND coverage >= %s" % (EVAL_THRESHOLD, COVERAGE_FLOOR)
    cmd = "%spython3 %s --router jev --mode %s --split all" % (
        ROUTER_ON, shlex.quote(os.path.join(GATE_DIR, "skill-route-eval.py")), mode)
    info = {}

    def match(doc):
        m = doc.get("meta") or {}
        return m.get("router") == "jev" and m.get("mode") == mode and m.get("split") == "all" and (m.get("n") or 0) > 0

    hit = pick_latest(d, match, lambda doc: parse_ts((doc.get("meta") or {}).get("date")))
    if hit is None:
        return crit(name, False, "no result (router=jev, mode=%s, split=all)" % mode, thr, d + "/*.json",
                    "run: " + cmd), info
    path, doc, dt = hit
    all_rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    rows = [r for r in all_rows if not r.get("unscored")]
    info["unscored_n"] = len(all_rows) - len(rows)
    if rows:
        # raw rows are the judge: eval summaries round to 0.1%
        gated = [r for r in rows if r.get("gate") == "pass"]
        acc = ratio(sum(1 for r in gated if row_top1(r)), len(gated))
        cov = ratio(len(gated), len(rows))
        n_scored, n_gated = len(rows), len(gated)
        info["raw_top1"] = ratio(sum(1 for r in rows if row_top1(r)), len(rows))
        hold = [r for r in rows if r.get("split") == "holdout"]
        info["holdout_top1"] = ratio(sum(1 for r in hold if row_top1(r)), len(hold))
        info["holdout_n"] = len(hold)
        down = sum(1 for r in rows if r.get("jev_down"))
    else:
        sm = doc.get("summary") or {}
        o = sm.get("overall") or {}
        acc = None if o.get("top1_among_gate_pass") is None else o["top1_among_gate_pass"] / 100.0
        cov = None if o.get("gate_pass_rate") is None else o["gate_pass_rate"] / 100.0
        n_scored = (doc.get("meta") or {}).get("n") or 0
        n_gated = o.get("n_gate_pass")
        info["raw_top1"] = None if o.get("top1") is None else o["top1"] / 100.0
        h = (sm.get("by_split") or {}).get("holdout") or {}
        info["holdout_top1"] = None if h.get("top1") is None else h["top1"] / 100.0
        info["holdout_n"] = h.get("n")
        down = 0
    info["accuracy_among_gate_pass"] = acc
    info["coverage"] = cov
    info["n_scored"] = n_scored
    info["n_gate_pass"] = n_gated
    if cov is None or (acc is None and not n_gated and cov > 0):
        return crit(name, False, "result has no gate-pass accuracy/coverage", thr, path, "unreadable result"), info
    value = "accuracy %s | coverage %s (n=%d, gate=pass %s, run %s)" % (
        pct(acc), pct(cov), n_scored, "?" if n_gated is None else n_gated, utc_stamp(dt))
    st = staleness(doc, cmd, cur)
    if st:
        return crit(name, False, st[0], thr, path, st[1]), info
    if down:
        return crit(name, False, "%s but %d rows ran during a Jev outage (jev_down)" % (value, down), thr, path,
                    "re-run %s" % cmd), info
    if acc is None:
        return crit(name, False, "%s: no gate=pass rows to score" % value, thr, path), info
    return crit(name, acc >= EVAL_THRESHOLD and cov >= COVERAGE_FLOOR, value, thr, path), info


def check_drill(cur):
    d = p_drill_results()
    name = "outage-drill"
    thr = "steps s1-s4 ran, pass true for skill-route"
    cmd = "%spython3 %s" % (ROUTER_ON, shlex.quote(os.path.join(GATE_DIR, "jev-drill.py")))
    hit = pick_latest(d, lambda doc: isinstance(doc.get("tools"), dict), lambda doc: parse_ts(doc.get("ts")))
    if hit is None:
        return crit(name, False, "no drill result", thr, d + "/*.json", "run: " + cmd)
    path, doc, dt = hit
    st = staleness(doc, cmd, cur)
    if st:
        return crit(name, False, st[0], thr, path, st[1])
    problems = []
    tools = doc.get("tools") or {}
    for t in DRILL_TOOLS:
        td = tools.get(t)
        if not isinstance(td, dict):
            problems.append("%s missing" % t)
            continue
        if td.get("pass") is not True:
            problems.append("%s pass=%s" % (t, td.get("pass")))
        ran = td.get("steps_run") or doc.get("steps_run") or []
        if sorted(ran) != DRILL_STEPS:
            problems.append("%s partial run (steps_run=%s)" % (t, ",".join(ran) or "none"))
    if doc.get("pass") is not True:
        problems.append("overall pass=%s" % doc.get("pass"))
    stamp = utc_stamp(dt)
    if problems:
        return crit(name, False, "%s (run %s)" % ("; ".join(problems), stamp), thr, path)
    return crit(name, True, "pass for skill-route (run %s)" % stamp, thr, path)


def check_window(now):
    skill_sh = read_jsonl(p_skill_shadow())
    fb = read_jsonl(p_feedback())
    name = "shadow-window"
    thr = ">= %d days OR >= %d gated tasks" % (WINDOW_DAYS, WINDOW_TASKS)
    src = "%s + %s" % (p_skill_shadow(), p_feedback())

    stamps = [parse_ts(r.get("ts")) for r in skill_sh + fb]
    stamps = [s for s in stamps if s is not None]

    n_route = sum(1 for r in skill_sh if r.get("actual_skills"))
    spawn_ids = set(r.get("spawn_id") for r in skill_sh if r.get("spawn_id"))
    n_fb = 0
    for r in fb:
        if r.get("tool") == "skill-route" and r.get("task_id") in spawn_ids:
            continue
        n_fb += 1
    n_total = n_route + n_fb

    reviewed = [r for r in fb if r.get("pd_review") in ("agree", "disagree")]
    agree = sum(1 for r in reviewed if r.get("pd_review") == "agree")
    info = {"pd_agree_rate": ratio(agree, len(reviewed)), "pd_agree": agree, "pd_reviewed": len(reviewed),
            "tasks_skill_route": n_route, "tasks_feedback_extra": n_fb}

    if not stamps:
        return crit(name, False, "no shadow records yet (0 gated tasks, window not started)", thr, src), info
    start = min(stamps)
    days = (now - start).total_seconds() / 86400.0
    met_days = days >= WINDOW_DAYS
    met_count = n_total >= WINDOW_TASKS
    value = "%.1f days since %s; %d gated tasks (skill-route %d + feedback %d)" % (
        days, utc_stamp(start), n_total, n_route, n_fb)
    if met_days or met_count:
        value += " [met by %s]" % ("days" if met_days else "count")
    info.update(window_start=utc_stamp(start), window_days=round(days, 2), gated_tasks=n_total,
                met_by_days=met_days, met_by_count=met_count)
    return crit(name, met_days or met_count, value, thr, src), info


# ---------------------------------------------------------------- run
def run(only=None):
    """Evaluate the selected criteria (all when `only` is empty). Only what is selected is computed."""
    sel = [c for c in CRITERIA if not only or c in only]
    now = now_utc() if "shadow-window" in sel else None
    mode = default_mode() if "skill-route-gated-accuracy" in sel else None
    cur = current_fingerprint() if ("skill-route-gated-accuracy" in sel or "outage-drill" in sel) else (None, None)
    crits = []
    i1, i4 = {}, None
    for c in sel:
        if c == "menu-build":
            crits.append(check_menu_build())
        elif c == "skill-route-gated-accuracy":
            cr, i1 = check_skill_route(mode, cur)
            crits.append(cr)
        elif c == "outage-drill":
            crits.append(check_drill(cur))
        elif c == "shadow-window":
            cr, i4 = check_window(now)
            crits.append(cr)
    return {"overall": all(c["pass"] for c in crits), "criteria": crits, "selected": sel,
            "info": {"router_enabled": router_enabled(), "default_mode": mode, "inputs_fingerprint": cur[0],
                     "skill_route_raw_top1": i1.get("raw_top1"),
                     "skill_route_accuracy_among_gate_pass": i1.get("accuracy_among_gate_pass"),
                     "skill_route_coverage": i1.get("coverage"), "coverage_floor": COVERAGE_FLOOR,
                     "skill_route_holdout_top1": i1.get("holdout_top1"), "skill_route_holdout_n": i1.get("holdout_n"),
                     "skill_route_unscored_n": i1.get("unscored_n"), "shadow": i4,
                     "now": utc_stamp(now) if now else None}}


def render(res):
    lines = []
    for c in res["criteria"]:
        lines.append("%s %s: %s (%s) %s" % ("PASS" if c["pass"] else "FAIL", c["name"], c["value"], c["threshold"], c["source"]))
    i = res["info"]
    lines.append("INFO skill router switch: %s (this gate is offline: it reads files only, no network call)"
                 % ("on" if i["router_enabled"] else "off; set AGENCY_SKILL_ROUTER=1 to enable the router"))
    if "skill-route-gated-accuracy" in res["selected"]:
        hold = "n/a" if i["skill_route_holdout_top1"] is None else "%s (n=%s)" % (pct(i["skill_route_holdout_top1"]), i["skill_route_holdout_n"])
        lines.append("INFO skill-route raw top-1 (all scored rows, INFO): %s" % pct(i.get("skill_route_raw_top1")))
        lines.append("INFO skill-route holdout top-1: %s" % hold)
    sh = i["shadow"]
    if sh is not None:
        agree = "n/a (0 reviewed)" if sh["pd_agree_rate"] is None else "%s (%d agree / %d reviewed)" % (
            pct(sh["pd_agree_rate"]), sh["pd_agree"], sh["pd_reviewed"])
        lines.append("INFO reviewer-agree rate (jev-feedback.jsonl): %s" % agree)
    lines.append("OVERALL %s" % ("PASS" if res["overall"] else "FAIL"))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="jev-gate-check.py", description="Skill router readiness gate (offline: reads files only).")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--only", action="append", default=[], choices=CRITERIA, metavar="NAME",
                    help="evaluate only this criterion (repeatable). One of: %s. "
                         "`--only menu-build` needs no result file, key or network and works with the router disabled."
                         % ", ".join(CRITERIA))
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code not in (0, None) else 0
    try:
        res = run(args.only)
    except InputError as e:
        sys.stderr.write("jev-gate-check: input error: %s\n" % e)
        return 2
    if args.json:
        print(json.dumps(res, indent=1, sort_keys=True))
    else:
        print(render(res))
    return 0 if res["overall"] else 1


if __name__ == "__main__":
    sys.exit(main())

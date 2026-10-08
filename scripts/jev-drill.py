#!/usr/bin/env python3
"""jev-drill.py - re-runnable Jev outage drill for the skill router (skill-route.py).

OPT-IN, NETWORK-CAPABLE. This tool refuses to run unless the router is enabled: with AGENCY_SKILL_ROUTER unset
(or not "1") it prints one line and exits 0 before it imports anything router-related, starts a server or runs a
subprocess. Steps s1, s3 and s4 reach the Jev endpoint (s4 with your real key); s2/s3 use a local server and a
made-up key. Stdlib only; runs on Python 3.9 and newer.

{root} below is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.

Four steps, each a SUBPROCESS of the real CLI with env overrides:
  s1  bogus-key env file (made-up literal in a temp file), real endpoint -> 401 -> router haiku,
      flag created, exactly 1 new "down" notify-log line
  s2  same again -> haiku, flag failures incremented, NO new notify line
  s3  local slow http server on 127.0.0.1 (sleeps > the client's 2s timeout; BOGUS key) -> timeout ->
      haiku, flag failures incremented, no new notify
  s4  real key (default env file, real endpoint) -> router jev -> flag gone, exactly 1 new "up" line
Evidence per step: router (from the tool output), flag before/after + JSON, new jev-notify.log lines
and new events.jsonl lines (jev_down / jev_up / jev_haiku_fallback), both diffed by BYTE OFFSET taken at
step start, plus the new jev-usage.jsonl records (cost/latency per call).
Steps s1-s3 degrade to Haiku (`claude -p`) exactly like a real outage does, so the Claude CLI must be on PATH.

The real API key is never read, printed or passed by this script: s1-s3 use a temp env file with a bogus
key, s4 simply leaves JEV_ENV_FILE unset so the client reads its default file itself (see skill-route/README.md).

State dir: default isolated {root}/state/skill-route/jev-drill/ (cleared at start) so the drill never collides with
the live {root}/state/skill-route/jev-down flag. --real-state uses {root}/state/skill-route and REFUSES to start when
jev-down already exists. Desktop notifications are REAL by default (macOS only; elsewhere only the notify log line is
written); pass --no-notify to skip them.

Usage
    AGENCY_SKILL_ROUTER=1 jev-drill.py [--no-notify] [--notify-log PATH] [--events on|off]
                 [--results-dir DIR] [--usage-log PATH] [--real-state] [--steps s1,s2,s3,s4]
Dry run (no desktop notification, no pollution of the real logs):
    AGENCY_SKILL_ROUTER=1 jev-drill.py --no-notify --notify-log /tmp/n.log --events off --results-dir /tmp/res --usage-log /tmp/u.jsonl
Output: results JSON {root}/evals/jev-drill/results/{YYYY-MM-DD}.json (local date; the same-day file is
overwritten with the newest run on top and earlier runs of that day kept under "runs"), a PASS/FAIL table
on stdout. Exit 0 only if every executed step passes.
The newest run (the top-level doc) carries "inputs_fingerprint" (jev_fingerprint.py: router code AST + routable
menu, taken at run start); jev-gate-check.py counts the drill only while that equals the current fingerprint. On error it
is null with "inputs_fingerprint_error". Older runs under "runs" keep whatever they had.

--steps limits the steps run (default s1-s4; a partial run is recorded as such and cannot satisfy the
gate: results carry "steps_run", which lists the steps run - jev-gate-check.py pins the set s1-s4). Sequence-dependent
checks (s2 failures incremented) still use the real flag state, so a partial run that skips s1 simply fails the checks
that need it.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


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


DRILL_VERSION = "1.0"
BOGUS_KEY = "drill-bogus-key-not-a-real-key-0000"   # made-up literal; never a real key
SLOW_SECONDS = 3.5                                   # > the client's 2.0s timeout
STEP_TIMEOUT = 240                                   # per CLI subprocess
EVENTS = ("jev_down", "jev_up", "jev_haiku_fallback")
ALL_STEPS = ("s1", "s2", "s3", "s4")
DEFAULT_STEPS = ALL_STEPS
TOOL = "skill-route"

ROOT = agency_root(os.path.expanduser("~"))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REAL_STATE = os.path.join(ROOT, "state", "skill-route")
ISOLATED_STATE = os.path.join(REAL_STATE, "jev-drill")
METRICS = os.path.join(ROOT, "memory", "metrics")
DEFAULT_NOTIFY_LOG = os.path.join(METRICS, "jev-notify.log")
DEFAULT_USAGE_LOG = os.path.join(METRICS, "jev-usage.jsonl")
EVENTS_FILE = os.path.join(METRICS, "events.jsonl")
DEFAULT_RESULTS = os.path.join(ROOT, "evals", "jev-drill", "results")

SKILL_ROUTE_TEXT = "Build a responsive landing page for our pricing in React and Tailwind"


# --------------------------------------------------------------------------- small helpers
def now_local():
    """Local time with its UTC offset; the results file is named by the LOCAL date."""
    return datetime.datetime.now().astimezone()


def file_size(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def read_from(path, offset):
    """Text appended to `path` after byte `offset` (complete lines only)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            data = fh.read()
    except OSError:
        return []
    return [ln for ln in data.decode("utf-8", "replace").split("\n") if ln.strip()]


def read_flag(state_dir):
    path = os.path.join(state_dir, "jev-down")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return {"exists": False}
    try:
        data = json.loads(raw)
    except ValueError:
        data = {"_unparseable": True}
    return {"exists": True, "json": data}


def flag_failures(flag):
    j = flag.get("json") if flag.get("exists") else None
    if isinstance(j, dict):
        try:
            return int(j.get("failures"))
        except (TypeError, ValueError):
            return None
    return None


def new_events(offset):
    out = []
    for ln in read_from(EVENTS_FILE, offset):
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("event") in EVENTS:
            out.append(rec)
    return out


def new_usage(path, offset):
    out = []
    for ln in read_from(path, offset):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append({k: r.get(k) for k in
                        ("ts", "purpose", "router", "model", "input_tokens", "output_tokens", "usd",
                         "latency_ms", "ok")})
    return out


# --------------------------------------------------------------------------- slow server (step s3)
class _SlowHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        self.server.hits += 1
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            time.sleep(SLOW_SECONDS)
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def log_message(self, *a):  # silence
        pass


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_slow_server():
    srv = _Server(("127.0.0.1", 0), _SlowHandler)
    srv.hits = 0
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


# --------------------------------------------------------------------------- tool runner
def base_env(ctx):
    env = dict(os.environ)
    for k in ("TYPESAFE_API_KEY", "JEV_ENDPOINT", "JEV_MODEL", "JEV_ENV_FILE", "JEV_HAIKU_CMD",
              "SKILL_ROUTE_CHILD", "JEV_PURPOSE", "SKILL_ROUTE_SKILLS_DIR", "SKILL_ROUTE_OVERLAY",
              "SKILL_ROUTE_LOG", "JEV_NOTIFY", "JEV_EMIT", "JEV_USAGE_LOG"):
        env.pop(k, None)
    env["AGENCY_SKILL_ROUTER"] = "1"     # the drill only runs with the switch on; the child must see it too
    env["SKILL_ROUTE_STATE_DIR"] = ctx["state_dir"]
    env["JEV_PURPOSE"] = "drill"
    env["JEV_NOTIFY_LOG"] = ctx["notify_log"]
    env["JEV_USAGE_LOG"] = ctx["usage_log"]
    if not ctx["notify_real"]:
        env["JEV_NOTIFY"] = "0"
    if not ctx["events_on"]:
        env["JEV_EMIT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_cli(step_env):
    argv = [sys.executable, os.path.join(SCRIPTS, "skill-route.py"), SKILL_ROUTE_TEXT, "--no-log"]
    t0 = time.time()
    try:
        p = subprocess.run(argv, env=step_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=STEP_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"rc": None, "elapsed_s": round(time.time() - t0, 2), "out": None, "err": "cli timeout"}
    out = None
    try:
        out = json.loads(p.stdout.decode("utf-8", "replace"))
    except ValueError:
        pass
    return {"rc": p.returncode, "elapsed_s": round(time.time() - t0, 2), "out": out,
            "err": p.stderr.decode("utf-8", "replace")[-300:]}


def tool_router(out):
    return out.get("router") if isinstance(out, dict) else None


# --------------------------------------------------------------------------- step logic
STEP_DEF = {
    "s1": {"key": "bogus", "want_router": "haiku", "flag_before": False, "flag_after": True,
           "notify": ("down", 1), "failures": "created"},
    "s2": {"key": "bogus", "want_router": "haiku", "flag_before": True, "flag_after": True,
           "notify": (None, 0), "failures": "incremented"},
    "s3": {"key": "slow", "want_router": "haiku", "flag_before": True, "flag_after": True,
           "notify": (None, 0), "failures": "incremented"},
    "s4": {"key": "real", "want_router": "jev", "flag_before": True, "flag_after": False,
           "notify": ("up", 1), "failures": None},
}


def run_step(step, ctx, bogus_env_file, slow_srv):
    sd = STEP_DEF[step]
    env = base_env(ctx)
    srv_hits_before = None
    if sd["key"] in ("bogus", "slow"):
        env["JEV_ENV_FILE"] = bogus_env_file
    if sd["key"] == "slow":
        env["JEV_ENDPOINT"] = "http://127.0.0.1:%d/v1/systemone" % slow_srv.server_address[1]
        srv_hits_before = slow_srv.hits
    # real: JEV_ENV_FILE / JEV_ENDPOINT left unset -> the client uses its default file + real endpoint

    n_off = file_size(ctx["notify_log"])
    e_off = file_size(EVENTS_FILE) if ctx["events_on"] else 0
    u_off = file_size(ctx["usage_log"])
    flag_before = read_flag(ctx["state_dir"])
    res = run_cli(env)
    flag_after = read_flag(ctx["state_dir"])
    notify = read_from(ctx["notify_log"], n_off)
    events = new_events(e_off) if ctx["events_on"] else []
    usage = new_usage(ctx["usage_log"], u_off)

    router = tool_router(res["out"])
    fails = []
    if res["rc"] != 0:
        fails.append("cli rc=%s" % res["rc"])
    if router != sd["want_router"]:
        fails.append("router=%s want %s" % (router, sd["want_router"]))
    if flag_before["exists"] != sd["flag_before"]:
        fails.append("flag_before=%s want %s" % (flag_before["exists"], sd["flag_before"]))
    if flag_after["exists"] != sd["flag_after"]:
        fails.append("flag_after=%s want %s" % (flag_after["exists"], sd["flag_after"]))
    kind, count = sd["notify"]
    kinds = [ln.split("\t")[-1].strip() for ln in notify]
    if len(notify) != count or (kind and kinds != [kind] * count):
        fails.append("new_notify=%s want %d%s" % (kinds, count, " " + kind if kind else ""))
    fb, fa = flag_failures(flag_before), flag_failures(flag_after)
    if sd["failures"] == "created" and not (fa and fa >= 1):
        fails.append("flag failures=%s want >=1" % fa)
    if sd["failures"] == "incremented" and not (fa is not None and fb is not None and fa > fb):
        fails.append("flag failures %s -> %s not incremented" % (fb, fa))
    if step == "s3":
        hits = slow_srv.hits - srv_hits_before
        if hits < 1:
            fails.append("slow server saw 0 requests")
        reason = (flag_after.get("json") or {}).get("reason") if flag_after["exists"] else None
        if reason != "timeout":
            fails.append("flag reason=%s want timeout" % reason)
    if ctx["events_on"]:
        names = [e.get("event") for e in events]
        if step == "s1" and names.count("jev_down") != 1:
            fails.append("events jev_down x%d want 1" % names.count("jev_down"))
        if step in ("s2", "s3") and "jev_down" in names:
            fails.append("unexpected jev_down event")
        if step == "s4" and names.count("jev_up") != 1:
            fails.append("events jev_up x%d want 1" % names.count("jev_up"))
        if step != "s4" and "jev_haiku_fallback" not in names:
            fails.append("no jev_haiku_fallback event")
    detail = "; ".join(fails) if fails else "ok"
    rec = {"pass": not fails, "router": router, "flag_before": flag_before, "flag_after": flag_after,
           "new_notify": notify, "new_events": events, "new_usage": usage, "detail": detail,
           "elapsed_s": res["elapsed_s"], "events_checked": ctx["events_on"]}
    if step == "s3":
        rec["slow_server_hits"] = slow_srv.hits - srv_hits_before
    if res["rc"] != 0 and res["err"]:
        rec["stderr_tail"] = res["err"]
    return rec


def run_tool(ctx, steps, bogus_env_file, slow_srv):
    n0 = file_size(ctx["notify_log"])
    rec = {"steps": {}, "steps_run": [s for s in steps if s in ALL_STEPS]}
    for s in steps:
        rec["steps"][s] = run_step(s, ctx, bogus_env_file, slow_srv)
    lines = read_from(ctx["notify_log"], n0)
    kinds = [ln.split("\t")[-1].strip() for ln in lines]
    rec["notify_down"] = kinds.count("down")
    rec["notify_up"] = kinds.count("up")
    rec["notify_lines"] = lines
    ok = all(v["pass"] for v in rec["steps"].values())
    if "s1" in steps and rec["notify_down"] != 1:
        ok = False
    if "s4" in steps and rec["notify_up"] != 1:
        ok = False
    rec["pass"] = ok
    return rec


# --------------------------------------------------------------------------- main
def router_enabled():
    """The single opt-in switch. Inlined (not jev_client.router_enabled) so the refusal happens before any router import."""
    return os.environ.get("AGENCY_SKILL_ROUTER") == "1"


def main(argv=None):
    if not router_enabled():
        print("skill router disabled (set AGENCY_SKILL_ROUTER=1 to run jev-drill.py); nothing run")
        return 0

    ap = argparse.ArgumentParser(description="Jev outage drill for the skill router (needs AGENCY_SKILL_ROUTER=1)")
    ap.add_argument("--no-notify", action="store_true", help="JEV_NOTIFY=0 (notify-log lines still written)")
    ap.add_argument("--notify-log", default=DEFAULT_NOTIFY_LOG, help="notify log path (default: the real one)")
    ap.add_argument("--events", choices=("on", "off"), default="on", help="off: JEV_EMIT=0, events not checked")
    ap.add_argument("--results-dir", default=DEFAULT_RESULTS)
    ap.add_argument("--usage-log", default=DEFAULT_USAGE_LOG)
    ap.add_argument("--real-state", action="store_true", help="use {root}/state/skill-route (refuses if jev-down exists)")
    ap.add_argument("--steps", default=",".join(DEFAULT_STEPS), help="comma list of s1..s4 (default all)")
    args = ap.parse_args(argv)

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    if not steps or any(s not in DEFAULT_STEPS for s in steps):
        sys.stderr.write("jev-drill.py: --steps must be a subset of s1,s2,s3,s4\n")
        return 2
    steps = [s for s in DEFAULT_STEPS if s in steps]

    sys.path.insert(0, SCRIPTS)
    import jev_fingerprint  # noqa: E402  (after the switch check: nothing router-related is imported while disabled)

    state_dir = REAL_STATE if args.real_state else ISOLATED_STATE
    if args.real_state:
        if os.path.exists(os.path.join(state_dir, "jev-down")):
            sys.stderr.write("jev-drill.py: refusing to start: %s/jev-down already exists (live outage?)\n" % state_dir)
            return 2
    else:
        if os.path.realpath(state_dir) != os.path.realpath(ISOLATED_STATE):
            sys.stderr.write("jev-drill.py: unexpected state dir\n")
            return 2
        shutil.rmtree(state_dir, ignore_errors=True)
        os.makedirs(state_dir, exist_ok=True)
        if os.path.exists(os.path.join(state_dir, "jev-down")):
            sys.stderr.write("jev-drill.py: flag present after clearing state dir\n")
            return 2

    tmp = tempfile.mkdtemp(prefix="jev-drill-")
    srv = None
    try:
        bogus_env_file = os.path.join(tmp, "bogus.env")
        fd = os.open(bogus_env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write("TYPESAFE_API_KEY=%s\n" % BOGUS_KEY)
        srv = start_slow_server() if "s3" in steps else None

        ctx = {"state_dir": state_dir, "notify_log": args.notify_log, "usage_log": args.usage_log,
               "notify_real": not args.no_notify, "events_on": args.events == "on"}
        run = {"ts": now_local().isoformat(timespec="seconds"), "version": DRILL_VERSION, "state_dir": state_dir,
               **jev_fingerprint.fingerprint_fields(),
               "notify_real": ctx["notify_real"], "events_checked": ctx["events_on"],
               "steps_run": [x for x in steps if x in ALL_STEPS], "tools": {}}
        run["tools"][TOOL] = run_tool(ctx, steps, bogus_env_file, srv)
        run["steps_run"] = [x for x in steps if x in ALL_STEPS]
        run["pass"] = all(v["pass"] for v in run["tools"].values()) and set(steps) == set(DEFAULT_STEPS)
        # a partial run (--steps) is recorded, but never counts as a full PASS for the gate
        exit_ok = all(v["pass"] for v in run["tools"].values())
    finally:
        if srv is not None:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    # leftover flag in the drill state dir is reported (and does not pollute the live flag)
    run["flag_left"] = read_flag(state_dir)["exists"]
    if run["flag_left"]:
        exit_ok = False
        run["pass"] = False

    # ---- results file (same-day: newest on top, earlier runs under "runs"; the day is the LOCAL date)
    os.makedirs(args.results_dir, exist_ok=True)
    path = os.path.join(args.results_dir, "%s.json" % now_local().strftime("%Y-%m-%d"))
    prior_runs = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            prev = json.load(fh)
        if isinstance(prev, dict):
            prior_runs = list(prev.pop("runs", []) or [])
            prior_runs.append(prev)
    except (OSError, ValueError):
        pass
    run["runs"] = prior_runs
    tmp_out = path + ".tmp"
    with open(tmp_out, "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp_out, path)

    # ---- table
    print("Jev outage drill v%s  state=%s  notify_real=%s  events=%s" %
          (DRILL_VERSION, state_dir, ctx["notify_real"], "on" if ctx["events_on"] else "off"))
    print("%-12s %-4s %-5s %-7s %-9s %-14s %s" % ("tool", "step", "res", "router", "notify", "flag b->a", "detail"))
    for t, tr in run["tools"].items():
        for s, sr in tr["steps"].items():
            kinds = ",".join(ln.split("\t")[-1].strip() for ln in sr["new_notify"]) or "-"
            fl = "%s->%s" % ("Y" if sr["flag_before"]["exists"] else "N", "Y" if sr["flag_after"]["exists"] else "N")
            print("%-12s %-4s %-5s %-7s %-9s %-14s %s" % (
                t, s, "PASS" if sr["pass"] else "FAIL", sr["router"], kinds, fl, sr["detail"]))
        print("%-12s total notify: down=%d up=%d  -> %s" % (t, tr["notify_down"], tr["notify_up"],
                                                             "PASS" if tr["pass"] else "FAIL"))
    partial = set(steps) != set(DEFAULT_STEPS)
    print("OVERALL: %s  (results: %s)" % (
        ("PARTIAL-%s" % ("PASS" if exit_ok else "FAIL")) if partial else ("PASS" if run["pass"] else "FAIL"), path))
    return 0 if exit_ok else 1


if __name__ == "__main__":
    sys.exit(main())

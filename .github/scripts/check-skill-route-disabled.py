#!/usr/bin/env python3
"""check-skill-route-disabled.py - proves the skill router makes NO network call and NO subprocess while disabled.

The router (scripts/skill-route.py) ships OFF: it runs only when AGENCY_SKILL_ROUTER is exactly "1". This
check runs the real script as a subprocess, through a small python wrapper that, before the script starts,
replaces socket.socket.connect / connect_ex, socket.create_connection, socket.getaddrinfo and
subprocess.Popen with versions that RECORD the attempt and then raise. At exit the wrapper writes what it saw
(attempts, spawns, whether jev_client / urllib.request were imported) to a report file.

Disabled cases (AGENCY_SKILL_ROUTER unset, "0", "true"; several argument shapes incl. --shadow with stdin,
--rebuild-menu, stdin text) must each: exit 0 in < 5 s, print exactly one line equal to the pinned JSON
object, record 0 network attempts and 0 spawns, never invoke the fake `claude` put first on PATH, never import
jev_client or urllib.request, and create or modify nothing under the temp HOME / AGENCY_HOME.

Positive control (proves the guard is not vacuous): AGENCY_SKILL_ROUTER=1 with a bogus key and
JEV_ENDPOINT=http://127.0.0.1:9/v1/systemone must record >= 1 network attempt (or invoke the fake claude)
and still exit 0 with a JSON result degraded to the grep router.

The fixture (3 tiny skills + a matching overlay) is self-contained, so the shipped overlay is not involved.

Usage: check-skill-route-disabled.py [path/to/skill-route.py]   (or env SKILL_ROUTE_SCRIPT)
Default script: <repo>/scripts/skill-route.py, resolved from this file's location.
Stdlib only. Exit 0 = PASS, 1 = FAIL. Prints one OK/FAIL line per assertion.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_SCRIPT = os.path.join(REPO, "scripts", "skill-route.py")

PINNED = {"router": "disabled", "enabled": False, "skills": [], "reason": "AGENCY_SKILL_ROUTER is not 1",
          "fallback": "pick 1-3 skills from skills/INDEX.md", "enable": "see scripts/skill-route/README.md"}
PINNED_LINE = ('{"router":"disabled","enabled":false,"skills":[],"reason":"AGENCY_SKILL_ROUTER is not 1",'
               '"fallback":"pick 1-3 skills from skills/INDEX.md","enable":"see scripts/skill-route/README.md"}')
MAX_SECONDS = 5.0

WRAPPER = r'''
import atexit, json, os, runpy, socket, subprocess, sys

_REPORT = os.environ["GUARD_REPORT"]
_net = []
_spawns = []


def _write_report():
    try:
        with open(_REPORT, "w") as fh:
            json.dump({"net": _net, "spawns": _spawns,
                       "jev_client_loaded": "jev_client" in sys.modules,
                       "urllib_request_loaded": "urllib.request" in sys.modules}, fh)
    except Exception:
        pass


atexit.register(_write_report)


def _blocked(kind, args):
    _net.append({"kind": kind, "args": repr(args)[:200]})
    return ConnectionRefusedError("network blocked by check-skill-route-disabled (%s)" % kind)


def _connect(self, *a, **k):
    raise _blocked("connect", a)


def _connect_ex(self, *a, **k):
    raise _blocked("connect_ex", a)


def _create_connection(*a, **k):
    raise _blocked("create_connection", a)


def _getaddrinfo(*a, **k):
    _net.append({"kind": "getaddrinfo", "args": repr(a)[:200]})
    raise socket.gaierror("lookup blocked by check-skill-route-disabled")


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.create_connection = _create_connection
socket.getaddrinfo = _getaddrinfo

_orig_popen_init = subprocess.Popen.__init__


def _popen_init(self, args, *a, **k):
    _spawns.append(repr(args)[:300])
    raise OSError("subprocess blocked by check-skill-route-disabled")


subprocess.Popen.__init__ = _popen_init

_script = sys.argv[1]
sys.argv = [_script] + sys.argv[2:]
runpy.run_path(_script, run_name="__main__")
'''

SKILLS = {
    "alpha-writer": ("Write blog posts, landing page copy and newsletters in a clear voice.", "writing"),
    "beta-coder": ("Build and refactor backend APIs, database schemas and tests.", "code"),
    "gamma-search": ("Research a topic on the web and summarise sources with citations.", "research"),
}

results = []


def check(ok, label, detail=""):
    results.append(bool(ok))
    line = "%s  %s" % ("OK  " if ok else "FAIL", label)
    if detail and not ok:
        line += "  -- " + detail
    print(line)


def snapshot(*dirs):
    """{path: (size, mtime_ns)} of everything under dirs: catches new files AND appends to existing ones."""
    out = {}
    for d in dirs:
        for base, subdirs, files in os.walk(d):
            for n in subdirs + files:
                p = os.path.join(base, n)
                try:
                    st = os.stat(p)
                    out[p] = (st.st_size if n in files else 0, st.st_mtime_ns if n in files else 0)
                except OSError:
                    pass
    return out


def changed(before, after):
    return sorted(p for p, sig in after.items() if before.get(p) != sig)


def build_fixture(tmp):
    skills = os.path.join(tmp, "fixture", "skills")
    domains = {}
    entries = {}
    for name, (desc, dom) in SKILLS.items():
        os.makedirs(os.path.join(skills, name))
        with open(os.path.join(skills, name, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: %s\ndescription: %s\n---\n\n# %s\n" % (name, desc, name))
        domains[dom] = "Tasks about %s." % dom
        entries[name] = {"domain": dom}
    overlay = os.path.join(tmp, "fixture", "overlay.json")
    with open(overlay, "w", encoding="utf-8") as fh:
        json.dump({"domains": domains, "skills": entries, "vi_map": {}, "en_only": []}, fh)
    return skills, overlay


def fake_claude(tmp):
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    log = os.path.join(tmp, "fake-claude.log")
    sh = os.path.join(bindir, "claude")
    with open(sh, "w") as fh:
        fh.write('#!/bin/sh\necho "$@" >> "%s"\nexit 1\n' % log)
    os.chmod(sh, 0o755)
    with open(os.path.join(bindir, "claude.cmd"), "w") as fh:
        fh.write('@echo %%* >> "%s"\r\n@exit /b 1\r\n' % log)
    return bindir, log


def base_env(tmp, home, root, skills, overlay, bindir, fake_log):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("JEV_", "SKILL_ROUTE_", "TYPESAFE_")) or k in (
                "AGENCY_SKILL_ROUTER", "CLAUDE_CONFIG_DIR", "ANTHROPIC_API_KEY", "PYTHONPATH"):
            env.pop(k)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["AGENCY_HOME"] = root
    env["JEV_ENV_FILE"] = os.path.join(tmp, "does-not-exist", ".env")
    env["SKILL_ROUTE_SKILLS_DIR"] = skills
    env["SKILL_ROUTE_OVERLAY"] = overlay
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env["FAKE_CLAUDE_LOG"] = fake_log
    return env


def run(script, wrapper, env, argv, stdin_text, report):
    env = dict(env, GUARD_REPORT=report)
    if os.path.exists(report):
        os.unlink(report)
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-I", wrapper, script] + argv,
                          input=(stdin_text or "").encode("utf-8"), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, timeout=60)
    wall = time.time() - t0
    try:
        with open(report) as fh:
            rep = json.load(fh)
    except (OSError, ValueError):
        rep = None
    return proc, wall, rep


def main(argv):
    script = (argv[1] if len(argv) > 1 else None) or os.environ.get("SKILL_ROUTE_SCRIPT") or DEFAULT_SCRIPT
    script = os.path.abspath(script)
    print("script: %s" % script)
    if not os.path.isfile(script):
        print("FAIL  script not found")
        return 1
    tmp = tempfile.mkdtemp(prefix="skill-route-disabled-")
    try:
        home = os.path.join(tmp, "home")
        root = os.path.join(tmp, "agency-root")
        os.makedirs(home)
        os.makedirs(root)
        skills, overlay = build_fixture(tmp)
        bindir, fake_log = fake_claude(tmp)
        wrapper = os.path.join(tmp, "guard_wrapper.py")
        with open(wrapper, "w") as fh:
            fh.write(WRAPPER)
        report = os.path.join(tmp, "guard-report.json")
        env0 = base_env(tmp, home, root, skills, overlay, bindir, fake_log)

        shadow_stdin = json.dumps({"prompt": "Write a landing page for a bakery.\nSkills: /alpha-writer",
                                   "description": "landing page", "spawn_id": "t1"})
        shapes = [
            ("task text", ["write a landing page for a bakery"], None),
            ("--shadow + stdin JSON", ["--shadow"], shadow_stdin),
            ("--rebuild-menu", ["--rebuild-menu"], None),
            ("stdin text", [], "build a REST API with tests"),
            ("--shadow-report", ["--shadow-report"], None),
        ]
        for switch in (None, "0", "true"):
            env = dict(env0)
            if switch is not None:
                env["AGENCY_SKILL_ROUTER"] = switch
            sw = "unset" if switch is None else repr(switch)
            for label, args, stdin_text in shapes:
                tag = "[AGENCY_SKILL_ROUTER=%s, %s]" % (sw, label)
                before = snapshot(home, root)
                proc, wall, rep = run(script, wrapper, env, args, stdin_text, report)
                out = proc.stdout.decode("utf-8", "replace")
                lines = out.splitlines()
                check(proc.returncode == 0, "%s exit 0" % tag,
                      "rc=%s stderr=%s" % (proc.returncode, proc.stderr.decode("utf-8", "replace")[-300:]))
                check(wall < MAX_SECONDS, "%s wall %.2fs < %.0fs" % (tag, wall, MAX_SECONDS))
                one_line = len(lines) == 1 and out.endswith("\n") and out.count("\n") == 1
                try:
                    parsed = json.loads(lines[0]) if len(lines) == 1 else None
                except ValueError:
                    parsed = None
                check(one_line and lines[0] == PINNED_LINE and parsed == PINNED,
                      "%s stdout is exactly the pinned disabled line" % tag, "stdout=%r" % out[:300])
                check(rep is not None, "%s guard report written" % tag)
                rep = rep or {}
                net = rep.get("net", [])
                spawns = rep.get("spawns", [])
                check(len(net) == 0, "%s 0 network attempts" % tag, "attempts=%s" % net[:3])
                check(len(spawns) == 0, "%s 0 subprocess spawns" % tag, "spawns=%s" % spawns[:3])
                check(not os.path.exists(fake_log), "%s fake claude never invoked" % tag)
                check(rep.get("jev_client_loaded") is False, "%s jev_client not imported" % tag)
                check(rep.get("urllib_request_loaded") is False, "%s urllib.request not imported" % tag)
                created = changed(before, snapshot(home, root))
                check(not created, "%s nothing created or modified under temp HOME / AGENCY_HOME" % tag,
                      "created=%s" % [os.path.relpath(p, tmp) for p in created[:5]])

        # ---- positive control: the guard must SEE the network attempt when the router is enabled
        keyfile = os.path.join(tmp, "typesafe.env")
        with open(keyfile, "w") as fh:
            fh.write("TYPESAFE_API_KEY=bogus-test-value-not-a-key\n")
        env = dict(env0, AGENCY_SKILL_ROUTER="1", JEV_ENV_FILE=keyfile,
                   JEV_ENDPOINT="http://127.0.0.1:9/v1/systemone", JEV_NOTIFY="0", JEV_EMIT="0")
        tag = "[positive control AGENCY_SKILL_ROUTER=1]"
        proc, wall, rep = run(script, wrapper, env, ["write a landing page for a bakery"], None, report)
        out = proc.stdout.decode("utf-8", "replace")
        rep = rep or {}
        net = rep.get("net", [])
        check(proc.returncode == 0, "%s exit 0" % tag,
              "rc=%s stderr=%s" % (proc.returncode, proc.stderr.decode("utf-8", "replace")[-300:]))
        check(len(net) >= 1 or os.path.exists(fake_log),
              "%s guard recorded %d network attempt(s) (guard is not vacuous)" % (tag, len(net)))
        try:
            res = json.loads(out.splitlines()[0]) if out.strip() else None
        except ValueError:
            res = None
        check(isinstance(res, dict) and res.get("router") == "grep" and "skills" in res,
              "%s JSON result degraded to the grep router" % tag, "stdout=%r" % out[:300])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = results.count(False)
    print("%s: %d checks, %d failed" % ("PASS" if not failed else "FAIL", len(results), failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

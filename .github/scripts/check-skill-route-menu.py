#!/usr/bin/env python3
"""check-skill-route-menu.py - CI gate: the shipped skill-router overlay matches the shipped skills.

The skill router (scripts/skill-route.py) is shipped DISABLED. Even so, its STRICT menu builder (the
default of load_menu; what this gate and jev-gate-check.py use) fails loudly on any shipped skill
without an overlay entry, and the maintainer-side
`jev-gate-check.py --only menu-build` relies on that. Two things can silently rot that:

  1. A skill is added to skills/ without an entry in scripts/skill-route/overlay.json
     (or an entry outlives its skill). A user who enables the router then gets a
     MenuError on every route call.
  2. The builder loses its loud failure and starts skipping unassigned skills, so the
     check in (1) can no longer be trusted. Hence the fail-safe proof below.

Checks (exit 0 PASS, 1 FAIL):
  a. overlay["skills"] keys == the set of shipped depth-1 skill dirs, exactly.
  b. load_menu(rebuild=True) succeeds on the real skills/ + overlay (stats are printed).
  c. Fail-safe proof: a temp overlay copy with one shipped skill removed must raise
     MenuError naming that skill; a skill with no domain, an unknown domain, or an
     unknown also_domains entry must raise MenuError too. If any of these does NOT
     raise, the builder lost its loud failure and this gate FAILS.
  c6-c9. Runtime is lenient (load_menu(strict=False), used by route() and the CLI): a skill dir with
     no overlay entry must NOT take the router down. It builds, the skill is excluded as "unassigned"
     and listed in menu["unassigned"]; a strict caller is never served that lenient cache; every other
     problem (unknown domain, no domain, bad also_domains, non-object entry, unreadable overlay) still
     raises MenuError; the CLI with the router on exits 0, prints the JSON on stdout and exactly one
     warning line on stderr naming the skill.
  d. If scripts/jev-gate-check.py exists: `--only menu-build` exits 0 on the real
     overlay and exits 1, naming the skill, on the stripped overlay.
  e. Zero network attempts (this process and every child process).

No network, no API key, no router switch: AGENCY_SKILL_ROUTER is removed from the
environment, and HOME / AGENCY_HOME / SKILL_ROUTE_STATE_DIR point at temp dirs, so
nothing here can read or write a real install. Stdlib only; Python 3.9 compatible;
paths via os.path so it also runs under Git Bash on Windows.
"""
import sys

sys.dont_write_bytecode = True  # never leave a __pycache__ inside scripts/ (it would be copied by the installers)

import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(REPO, "scripts")
SKILLS = os.path.join(REPO, "skills")
OVERLAY = os.path.join(SCRIPTS, "skill-route", "overlay.json")
ROUTER = os.path.join(SCRIPTS, "skill-route.py")
JEV_GATE = os.path.join(SCRIPTS, "jev-gate-check.py")

# --------------------------------------------------------------------------- network guard
# Installed BEFORE anything is loaded. Every attempt is counted and refused.
NET_ATTEMPTS = []

_GUARD_SRC = '''\
import atexit, os, socket
_LOG = os.environ.get("SKILL_ROUTE_GATE_NETLOG")
def _deny(what):
    def f(*a, **k):
        if _LOG:
            try:
                with open(_LOG, "a") as fh:
                    fh.write(what + "\\n")
            except OSError:
                pass
        raise OSError("network disabled by check-skill-route-menu.py (" + what + ")")
    return f
socket.socket.connect = _deny("socket.connect")
socket.socket.connect_ex = _deny("socket.connect_ex")
socket.create_connection = _deny("socket.create_connection")
socket.getaddrinfo = _deny("socket.getaddrinfo")
socket.gethostbyname = _deny("socket.gethostbyname")
'''


def _deny(what):
    def refuse(*_a, **_k):
        NET_ATTEMPTS.append(what)
        raise OSError("network disabled by check-skill-route-menu.py (%s)" % what)
    return refuse


socket.socket.connect = _deny("socket.connect")
socket.socket.connect_ex = _deny("socket.connect_ex")
socket.create_connection = _deny("socket.create_connection")
socket.getaddrinfo = _deny("socket.getaddrinfo")
socket.gethostbyname = _deny("socket.gethostbyname")

# --------------------------------------------------------------------------- helpers
FAILURES = []


def ok(tag, msg):
    print("PASS %s: %s" % (tag, msg))


def bad(tag, msg):
    FAILURES.append("%s: %s" % (tag, msg))
    print("FAIL %s: %s" % (tag, msg))


def shipped_skills(skills_dir):
    """Depth-1 dirs holding a SKILL.md; names starting with _ or . are skipped (same rule as the builder)."""
    out = set()
    for name in os.listdir(skills_dir):
        if name.startswith(("_", ".")):
            continue
        if os.path.isfile(os.path.join(skills_dir, name, "SKILL.md")):
            out.add(name)
    return out


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def load_router():
    spec = importlib.util.spec_from_file_location("skill_route_under_test", ROUTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expect_menu_error(mod, overlay_path, needles, tag, what, **load_kw):
    """load_menu(rebuild=True, **load_kw) with SKILL_ROUTE_OVERLAY=overlay_path must raise MenuError
    mentioning every needle. load_kw defaults to the strict default (no strict= argument)."""
    kw = dict(rebuild=True)
    kw.update(load_kw)
    os.environ["SKILL_ROUTE_OVERLAY"] = overlay_path
    try:
        mod.load_menu(**kw)
    except mod.MenuError as e:
        text = str(e)
        missing = [n for n in needles if n not in text]
        if missing:
            bad(tag, "%s: MenuError did not mention %s: %s" % (what, missing, text.splitlines()[0] if text else ""))
        else:
            ok(tag, "%s -> MenuError naming %s" % (what, ", ".join(needles)))
    except BaseException as e:  # noqa: BLE001 - any other failure mode is also a gate failure
        bad(tag, "%s: expected MenuError, got %s: %s" % (what, e.__class__.__name__, e))
    else:
        bad(tag, "%s: load_menu(%s) did NOT raise - the builder lost its loud failure" % (
            what, ", ".join("%s=%r" % kv for kv in sorted(kw.items()))))
    finally:
        os.environ["SKILL_ROUTE_OVERLAY"] = OVERLAY


def run_gate_child(args, env, tmp):
    return subprocess.run([sys.executable, JEV_GATE] + args, env=env, cwd=tmp, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, timeout=180)


def main():
    tmp = tempfile.mkdtemp(prefix="skill-route-gate-")
    try:
        # ---- environment: no switch, no real home, no real state
        env = dict(os.environ)
        for k in ("AGENCY_SKILL_ROUTER", "CLAUDE_CONFIG_DIR", "JEV_ENV_FILE", "SKILL_ROUTE_CHILD"):
            env.pop(k, None)
        home = os.path.join(tmp, "home")
        agency_home = os.path.join(tmp, "agency")
        state = os.path.join(tmp, "state")
        for d in (home, agency_home, state):
            os.makedirs(d)
        env.update({
            "HOME": home, "USERPROFILE": home, "AGENCY_HOME": agency_home,
            "SKILL_ROUTE_STATE_DIR": state,
            "SKILL_ROUTE_SKILLS_DIR": SKILLS, "SKILL_ROUTE_OVERLAY": OVERLAY,
            "SKILL_ROUTE_LOG": os.path.join(tmp, "route.jsonl"),
            "SKILL_ROUTE_SHADOW_LOG": os.path.join(tmp, "shadow.jsonl"),
            "JEV_USAGE_LOG": os.path.join(tmp, "usage.jsonl"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        os.environ.clear()
        os.environ.update(env)

        # Child processes get the same network guard through a sitecustomize on PYTHONPATH.
        guard_dir = os.path.join(tmp, "guard")
        os.makedirs(guard_dir)
        with open(os.path.join(guard_dir, "sitecustomize.py"), "w") as fh:
            fh.write(_GUARD_SRC)
        netlog = os.path.join(tmp, "child-net.log")
        child_env = dict(env)
        child_env["PYTHONPATH"] = guard_dir
        child_env["SKILL_ROUTE_GATE_NETLOG"] = netlog

        print("repo:      %s" % REPO)
        print("python:    %s" % sys.version.split()[0])

        # ---- a. overlay keys == shipped skills
        shipped = shipped_skills(SKILLS)
        try:
            with open(OVERLAY, "r", encoding="utf-8") as fh:
                overlay = json.load(fh)
            keys = set(overlay.get("skills") or {})
        except (OSError, ValueError) as e:
            bad("a", "cannot read %s: %s" % (OVERLAY, e.__class__.__name__))
            return
        missing, stale = sorted(shipped - keys), sorted(keys - shipped)
        if not shipped:
            bad("a", "no shipped skills found under %s" % SKILLS)
        elif missing or stale:
            bad("a", "overlay does not match skills/: %d missing %s; %d stale %s. Add entries with "
                "scripts/skill-route-overlay-add.py; delete entries of removed skills." % (
                    len(missing), missing, len(stale), stale))
        else:
            ok("a", "overlay covers exactly the %d shipped skills" % len(shipped))

        # ---- b. real build
        if not os.path.isfile(ROUTER):
            bad("b", "missing %s" % ROUTER)
            return
        try:
            mod = load_router()
        except BaseException as e:  # noqa: BLE001
            bad("b", "cannot import %s with the switch off: %s: %s" % (ROUTER, e.__class__.__name__, e))
            return
        for attr in ("MenuError", "load_menu", "menu_stats"):
            if not hasattr(mod, attr):
                bad("b", "skill-route.py does not expose %s" % attr)
                return
        try:
            menu = mod.load_menu(rebuild=True)
            stats = mod.menu_stats(menu)
        except BaseException as e:  # noqa: BLE001
            bad("b", "menu build failed: %s: %s" % (e.__class__.__name__, e))
            return
        synthetic = [n for n in (overlay.get("synthetic") or {}) if n not in shipped]
        want = len(shipped) + len(synthetic)
        got = stats["routable"] + stats["excluded"]
        if got != want:
            bad("b", "routable %d + excluded %d != %d shipped + %d synthetic" % (
                stats["routable"], stats["excluded"], len(shipped), len(synthetic)))
        else:
            ok("b", "menu built: routable=%d (incl. %d synthetic) excluded=%d domains=%d" % (
                stats["routable"], len(synthetic), stats["excluded"], len(stats["domains"])))
            print("   per-domain: %s" % ", ".join("%s=%d" % kv for kv in sorted(stats["domains"].items())))

        # ---- c. fail-safe proof: the builder must still refuse a broken overlay
        victim = sorted(n for n, e in overlay["skills"].items()
                        if n in shipped and not (e or {}).get("exclude") and (e or {}).get("domain"))[0]
        some_domain = sorted(overlay["domains"])[0]

        def variant(name, mutate):
            data = json.loads(json.dumps(overlay))
            mutate(data)
            path = os.path.join(tmp, "overlay-%s.json" % name)
            write_json(path, data)
            return path

        stripped = variant("missing", lambda d: d["skills"].pop(victim))
        expect_menu_error(mod, stripped, [victim], "c1", "overlay without the entry of '%s'" % victim)
        expect_menu_error(mod, variant("nodomain", lambda d: d["skills"].__setitem__(victim, {})),
                          [victim, "no domain"], "c2", "'%s' with neither domain nor exclude" % victim)
        expect_menu_error(mod, variant("unknown", lambda d: d["skills"].__setitem__(victim, {"domain": "no-such-domain"})),
                          [victim, "unknown domain"], "c3", "'%s' with an unknown domain" % victim)
        expect_menu_error(mod, variant("also", lambda d: d["skills"].__setitem__(
            victim, {"domain": some_domain, "also_domains": ["no-such-domain"]})),
            [victim, "unknown also_domains"], "c4", "'%s' with an unknown also_domains entry" % victim)
        # The real overlay must still build after the negative cases (nothing cached a bad state).
        try:
            mod.load_menu(rebuild=True)
            ok("c5", "real overlay still builds after the negative cases")
        except BaseException as e:  # noqa: BLE001
            bad("c5", "real overlay no longer builds: %s: %s" % (e.__class__.__name__, e))

        # ---- c6-c9. runtime is lenient: a skill with no overlay entry must not take the router down.
        # (Users keep personal skills in the same skills dir, and `agency upgrade` overwrites the overlay.)
        # c1-c4 above prove the STRICT default (what this gate and jev-gate-check.py use) still fails loud.
        os.environ["SKILL_ROUTE_OVERLAY"] = stripped
        try:
            lenient = mod.load_menu(rebuild=True, strict=False)
            lstats = mod.menu_stats(lenient)
        except BaseException as e:  # noqa: BLE001
            bad("c6", "lenient build with '%s' unassigned failed: %s: %s" % (victim, e.__class__.__name__, e))
        else:
            if lenient.get("excluded", {}).get(victim) != "unassigned" or victim in lenient["skills"]:
                bad("c6", "'%s' not excluded as 'unassigned' (excluded=%r)" % (victim, lenient.get("excluded", {}).get(victim)))
            elif lenient.get("unassigned") != [victim]:
                bad("c6", "menu['unassigned'] is %r, expected %r" % (lenient.get("unassigned"), [victim]))
            elif lstats["excluded_names"].get(victim) != "unassigned":
                bad("c6", "menu_stats excluded_names lacks '%s'" % victim)
            else:
                ok("c6", "lenient build (strict=False) without '%s' builds; it is excluded 'unassigned' and listed in menu['unassigned']" % victim)
        finally:
            os.environ["SKILL_ROUTE_OVERLAY"] = OVERLAY
        # The lenient build above wrote the cache. A strict caller must NOT be served that cache.
        expect_menu_error(mod, stripped, [victim], "c6b", "strict load_menu(rebuild=False) after a lenient build",
                          rebuild=False)
        # Every other problem still raises in lenient mode too.
        expect_menu_error(mod, variant("unknown", lambda d: d["skills"].__setitem__(victim, {"domain": "no-such-domain"})),
                          [victim, "unknown domain"], "c7", "lenient: '%s' with an unknown domain" % victim, strict=False)
        expect_menu_error(mod, variant("nodomain", lambda d: d["skills"].__setitem__(victim, {})),
                          [victim, "no domain"], "c7b", "lenient: '%s' with neither domain nor exclude" % victim, strict=False)
        expect_menu_error(mod, variant("also", lambda d: d["skills"].__setitem__(
            victim, {"domain": some_domain, "also_domains": ["no-such-domain"]})),
            [victim, "unknown also_domains"], "c7c", "lenient: '%s' with an unknown also_domains entry" % victim, strict=False)
        expect_menu_error(mod, variant("nonobj", lambda d: d["skills"].__setitem__(victim, "oops")),
                          [victim], "c7d", "lenient: '%s' with a non-object entry" % victim, strict=False)
        bad_overlay = os.path.join(tmp, "overlay-garbage.json")
        with open(bad_overlay, "w") as fh:
            fh.write("{not json")
        expect_menu_error(mod, bad_overlay, ["cannot read overlay"], "c7e", "lenient: unreadable overlay", strict=False)
        try:
            mod.load_menu(rebuild=True)
            ok("c8", "real overlay still builds (strict) after the lenient cases")
        except BaseException as e:  # noqa: BLE001
            bad("c8", "real overlay no longer builds: %s: %s" % (e.__class__.__name__, e))

        # c9. CLI end to end, router ON, stripped overlay: exit 0, one JSON line on stdout, ONE warning on stderr.
        def run_cli(overlay_path):
            cenv = dict(child_env)
            cenv.update({"AGENCY_SKILL_ROUTER": "1", "SKILL_ROUTE_OVERLAY": overlay_path,
                         "JEV_HAIKU_CMD": "/usr/bin/false", "JEV_NOTIFY": "0", "JEV_EMIT": "0",
                         "JEV_ENV_FILE": os.path.join(tmp, "no-such-env-file")})
            return subprocess.run([sys.executable, ROUTER, "--router", "grep", "--no-log", "fix the login page"],
                                  env=cenv, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True, timeout=60)
        try:
            r = run_cli(stripped)
            err_lines = [ln for ln in r.stderr.splitlines() if ln.strip()]
            try:
                out_json = json.loads(r.stdout)
            except ValueError:
                out_json = None
            if r.returncode != 0:
                bad("c9", "CLI on the stripped overlay exit %d, stderr: %s" % (r.returncode, r.stderr.strip()))
            elif not isinstance(out_json, dict) or len(r.stdout.strip().splitlines()) != 1 or "skills" not in out_json:
                bad("c9", "CLI stdout is not exactly one JSON contract line: %r" % r.stdout[:200])
            elif len(err_lines) != 1 or not err_lines[0].startswith("skill-route.py: warning: 1 skill(s) have no overlay entry") \
                    or victim not in err_lines[0]:
                bad("c9", "expected exactly one stderr warning naming '%s', got %d line(s): %r" % (victim, len(err_lines), err_lines))
            else:
                ok("c9", "CLI with the router on, '%s' unassigned: exit 0, JSON on stdout, exactly one stderr warning" % victim)
            r = run_cli(OVERLAY)
            if r.returncode != 0 or r.stderr.strip():
                bad("c9b", "CLI on the real overlay: exit %d, expected silent stderr, got %r" % (r.returncode, r.stderr.strip()[:200]))
            else:
                ok("c9b", "CLI on the real overlay: exit 0, no warning")
        except (OSError, subprocess.SubprocessError) as e:
            bad("c9", "could not run %s: %s" % (ROUTER, e))

        # ---- d. the maintainer gate's menu-build criterion
        if os.path.isfile(JEV_GATE):
            try:
                r = run_gate_child(["--only", "menu-build"], child_env, tmp)
                if r.returncode == 0:
                    ok("d1", "jev-gate-check.py --only menu-build exits 0 with the router switch off")
                else:
                    bad("d1", "jev-gate-check.py --only menu-build exit %d:\n%s" % (r.returncode, r.stdout.strip()))
                neg_env = dict(child_env)
                neg_env["SKILL_ROUTE_OVERLAY"] = stripped
                r = run_gate_child(["--only", "menu-build"], neg_env, tmp)
                if r.returncode == 1 and victim in r.stdout:
                    ok("d2", "jev-gate-check.py --only menu-build exits 1 naming '%s' on the stripped overlay" % victim)
                else:
                    bad("d2", "stripped overlay: expected exit 1 naming '%s', got exit %d:\n%s" % (
                        victim, r.returncode, r.stdout.strip()))
            except (OSError, subprocess.SubprocessError) as e:
                bad("d", "could not run jev-gate-check.py: %s" % e)
        else:
            print("SKIP d: scripts/jev-gate-check.py is not present")

        # ---- e. no network, in this process or any child
        child_hits = 0
        if os.path.isfile(netlog):
            with open(netlog, "r") as fh:
                child_hits = len([ln for ln in fh.read().splitlines() if ln.strip()])
        if NET_ATTEMPTS or child_hits:
            bad("e", "%d in-process + %d child network attempt(s): %s" % (len(NET_ATTEMPTS), child_hits, NET_ATTEMPTS))
        else:
            ok("e", "0 network attempts (this process and children)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:  # noqa: BLE001 - never exit 0 on an unexpected crash
        if not isinstance(exc, SystemExit):
            bad("gate", "unexpected %s: %s" % (exc.__class__.__name__, exc))
        elif exc.code not in (0, None):
            bad("gate", "unexpected SystemExit(%r)" % (exc.code,))
    if NET_ATTEMPTS:
        FAILURES.append("e: %d network attempt(s) after main: %s" % (len(NET_ATTEMPTS), NET_ATTEMPTS))
    if FAILURES:
        print("\ncheck-skill-route-menu: FAIL (%d)" % len(FAILURES))
        for f in FAILURES:
            print("  - " + f.splitlines()[0])
        sys.exit(1)
    print("\ncheck-skill-route-menu: PASS")
    sys.exit(0)

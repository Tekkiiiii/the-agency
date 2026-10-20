"""Tests for scripts/jev-spawn-gate.py, the CLI enforcer for binding Jev routing on spawns (ships DISABLED).

Every case runs the REAL CLI in a subprocess (stdin JSON -> one stdout JSON line, exit 0). NO real network: the Jev
endpoint is the counting stub from jev_stub.py; skills/overlay are the router fixtures. Everything that could be
written (route cache, state dir, decision/shadow/feedback/usage logs, the agency root) is an env override inside
test_jev_router.RouterEnv, so no test touches a real install.

DisabledDefaultTests prove the shipped default: with AGENCY_SKILL_ROUTER anything but exactly "1" the gate prints
{"action": "pass"} and does nothing else (no request to the stub, no fake-claude call, no file written, no
kill-switch file read). Every other class runs with the switch on (jev_stub sets AGENCY_SKILL_ROUTER=1).

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_spawn_gate*' -v   (also /usr/bin/python3)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import jev_stub  # noqa: E402
import test_jev_router as tr  # noqa: E402  (RouterEnv)
import jev_spawn  # noqa: E402

GATE = os.path.join(SCRIPTS, "jev-spawn-gate.py")
J = ["frontend", "tailwind"]
WINNERS = {"domain": "frontend-ui", "skill": "frontend"}
SEEN_IDS = set()    # every route id the tests saw


def parse_jev_gate(stdout):
    """Python port of parseJevGate in mods/spawn-ledger/hooks/register.ts (strict; None = fail open)."""
    lines = [x for x in stdout.strip().split("\n") if x]
    last = lines[-1] if lines else ""
    try:
        gate = json.loads(last)
    except ValueError:
        return None
    if not isinstance(gate, dict):
        return None

    def text(v):
        return v if isinstance(v, str) and v else None

    note, route_id = text(gate.get("note")), text(gate.get("route_id"))
    if gate.get("action") == "deny":
        deny = text(gate.get("deny"))
        return {"action": "deny", "deny": deny, "route_id": route_id} if deny else None
    if gate.get("action") == "rewrite":
        prompt = text(gate.get("prompt"))
        return {"action": "rewrite", "prompt": prompt, "note": note, "route_id": route_id} if prompt else None
    return {"action": "pass", "note": note, "route_id": route_id} if gate.get("action") == "pass" else None


def put_cache(skills=None, gate="pass", router="jev", confidential=False, none_fired=False, denies=0):
    rid = jev_spawn.cache_put({"skills": list(J if skills is None else skills), "gate": gate, "router": router,
                               "domain": "frontend-ui", "jev_down": False},
                              {"role": "exec", "none_fired": none_fired, "confidential": confidential})
    assert rid
    for _ in range(denies):
        jev_spawn.cache_bump_denies(rid)
    return rid


def spawn(prompt, **kw):
    d = {"tool_use_id": "toolu_1", "subagent_type": "general-purpose", "description": "Build the landing page",
         "prompt": prompt, "parent_agent": "root", "parent_spawn_id": "", "fork": False, "is_teammate": False,
         "workflow": False}
    d.update(kw)
    return d


class GateEnv(tr.RouterEnv):
    """RouterEnv (temp agency root = AGENCY_HOME, temp state dir) + a CLI runner. Returns (rc, stdout, stderr)."""

    def run_raw(self, stdin_text, extra_env=None):
        env = dict(os.environ)
        env.pop("JEV_GATE_OFF", None)
        env.update(extra_env or {})
        for k in [k for k, v in env.items() if v is None]:
            del env[k]
        p = subprocess.run([sys.executable, GATE], input=stdin_text, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=60)
        return p.returncode, p.stdout, p.stderr

    def run(self, data, extra_env=None):
        rc, out, err = self.run_raw(json.dumps(data) if not isinstance(data, str) else data, extra_env)
        assert rc == 0, (rc, out, err)
        assert err == "", err
        assert out.endswith("\n") and out.count("\n") == 1, repr(out)   # exactly ONE line
        obj = json.loads(out)
        assert parse_jev_gate(out) is not None, out                     # the mod would accept it
        if obj.get("route_id"):
            SEEN_IDS.add(obj["route_id"])
        assert os.environ["JEV_FEEDBACK_LOG"].startswith(self.tmp), os.environ["JEV_FEEDBACK_LOG"]
        assert os.environ["AGENCY_HOME"].startswith(tempfile.gettempdir()) or os.environ["AGENCY_HOME"].startswith(
            os.path.realpath(tempfile.gettempdir())), os.environ["AGENCY_HOME"]
        return obj

    def cache_files(self):
        d = os.path.join(self.state_dir, "jev-route-cache")
        return sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []

    def denies(self, rid):
        return jev_spawn.cache_get(rid)["denies"]

    def gate_denies(self):
        return [r for r in self.shadows() if r.get("event") == "gate_deny"]

    def assert_no_side_logs(self, tc):
        """The gate never writes feedback or decision rows; the shadow log may hold ONLY gate_deny rows (F4), and
        only for deny / deny_cap outcomes (checked per test via gate_denies())."""
        tc.assertEqual(self.feedbacks(), [])          # the gate never writes feedback
        tc.assertEqual([r for r in self.shadows() if r.get("event") != "gate_deny"], [])
        tc.assertEqual(self.decisions(), [])


class DisabledDefaultTests(unittest.TestCase):
    """The gate ships disabled: AGENCY_SKILL_ROUTER must be exactly "1". Anything else = pass and NOTHING else."""

    OFF_VALUES = (None, "", "0", "true", "yes", "on", " 1", "1 ")
    SPAWNS = (
        "Build a landing page",                                              # would rewrite when on
        "Skills: /humanizer\nBuild a landing page",                          # would deny when on
        "Skills: /frontend, /tailwind\nJev[r=deadbeef]: accept\nBuild",      # stale id
    )

    def tree(self, root):
        out = {}
        for base, dirs, files in os.walk(root):
            for n in dirs + files:
                p = os.path.join(base, n)
                st = os.stat(p)
                out[p] = (st.st_size, st.st_mtime_ns)
        return out

    def test_switch_parsing_matches_the_router(self):
        spec = importlib.util.spec_from_file_location("jev_spawn_gate_under_test", GATE)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        for value in self.OFF_VALUES + ("1",):
            with tr.RouterEnv(extra_env={"AGENCY_SKILL_ROUTER": value}):
                self.assertEqual(gate.router_enabled(), tr.sr.router_enabled(), repr(value))
                self.assertEqual(gate.router_enabled(), value == "1", repr(value))

    def test_disabled_passes_with_no_request_no_claude_no_file(self):
        for value in self.OFF_VALUES:
            with GateEnv(winners=WINNERS, extra_env={"AGENCY_SKILL_ROUTER": value}) as e:
                before = self.tree(e.tmp)
                for p in self.SPAWNS:
                    for st in ("general-purpose", "coord", "critique-design"):
                        rc, out, err = e.run_raw(json.dumps(spawn(p, subagent_type=st)))
                        self.assertEqual((rc, out, err), (0, '{"action": "pass"}\n', ""), (value, p, st))
                self.assertEqual(e.stub.count, 0, "gate reached the Jev endpoint with the switch %r" % (value,))
                self.assertEqual(jev_stub.fake_claude_records(e.fake_claude), [], repr(value))
                self.assertEqual(e.usage_records(), [], repr(value))
                self.assertFalse(e.flag_exists(), repr(value))
                self.assertEqual(self.tree(e.tmp), before, "gate wrote under the temp root with the switch %r" % (value,))

    def test_disabled_ignores_malformed_stdin(self):
        with GateEnv(winners=WINNERS, extra_env={"AGENCY_SKILL_ROUTER": None}) as e:
            for raw in ("", "not json", "{", "[]", "null"):
                self.assertEqual(e.run_raw(raw), (0, '{"action": "pass"}\n', ""), raw)

    def test_disabled_makes_no_socket_and_no_subprocess_call(self):
        """Same guard idea as .github/scripts/check-skill-route-disabled.py, run in-process over main()."""
        with GateEnv(winners=WINNERS, extra_env={"AGENCY_SKILL_ROUTER": None}) as e:
            wrapper = os.path.join(e.tmp, "guard.py")
            marker = os.path.join(e.tmp, "blocked-call.marker")     # the gate fails open, so record the attempt
            with open(wrapper, "w") as f:
                f.write("import runpy, socket, subprocess, sys\n"
                        "def _no(*a, **k):\n    open(%r, 'a').write('x')\n    raise SystemExit(99)\n" % marker +
                        "socket.socket.connect = socket.create_connection = socket.getaddrinfo = _no\n"
                        "subprocess.Popen.__init__ = _no\n"
                        "sys.argv = [sys.argv[1]]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n")
            p = subprocess.run([sys.executable, wrapper, GATE], input=json.dumps(spawn(self.SPAWNS[0])),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                               env=dict(os.environ), timeout=60)
            self.assertEqual((p.returncode, p.stdout, p.stderr), (0, '{"action": "pass"}\n', ""))
            self.assertFalse(os.path.exists(marker), "the disabled gate tried a socket or a subprocess")

    def test_enabled_control_still_routes(self):
        """Not vacuous: the same input with the switch on reaches the stub and rewrites."""
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn(self.SPAWNS[0]))
            self.assertEqual(obj["action"], "rewrite")
            self.assertGreater(e.stub.count, 0)


class CliContractTests(unittest.TestCase):
    def test_malformed_stdin_passes(self):
        with GateEnv() as e:
            for raw in ("", "   \n"):   # nothing on stdin is a plain pass
                rc, out, err = e.run_raw(raw)
                self.assertEqual((rc, out, err), (0, '{"action": "pass"}\n', ""), raw)
            # not JSON / not an object: still fail open, but self-explaining (a zsh `echo` that expands \\n inside
            # the JSON string produced raw newlines: the bare pass looked like a legitimate one)
            for raw in ("not json", "{", "[]", "null", "42", '"str"', '{"prompt": "a\nb"}'):
                rc, out, err = e.run_raw(raw)
                self.assertEqual((rc, out, err), (0, '{"action": "pass", "reason": "malformed_stdin"}\n', ""), raw)
                self.assertIsNotNone(parse_jev_gate(out), raw)   # the mod still accepts it as a pass
            self.assertEqual(e.stub.count, 0)

    def test_nothing_to_route_passes(self):
        with GateEnv(winners=WINNERS) as e:
            for d in ({}, {"prompt": "", "description": "  "}, {"subagent_type": "general-purpose"}):
                self.assertEqual(e.run(d), {"action": "pass"})
            self.assertEqual(e.stub.count, 0)

    def test_non_string_fields_do_not_crash(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run({"prompt": 5, "subagent_type": 7, "description": None, "parent_agent": ["x"]})
            self.assertIn(obj["action"], ("pass", "rewrite", "deny"))

    def test_parse_jev_gate_port_is_strict(self):
        self.assertIsNone(parse_jev_gate("garbage"))
        self.assertIsNone(parse_jev_gate('{"action":"deny"}'))                    # deny needs a message
        self.assertIsNone(parse_jev_gate('{"action":"rewrite"}'))                 # rewrite needs a prompt
        self.assertIsNone(parse_jev_gate('{"action":"explode"}'))
        self.assertEqual(parse_jev_gate('{"action":"pass"}')["action"], "pass")

    def test_stdout_is_json_line_even_when_stderr_would_be_noisy(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn("Skills: /frontend\nBuild a landing page"))
            self.assertIn("action", obj)


class KillSwitchTests(unittest.TestCase):
    def check_off(self, e, extra_env=None, before=None):
        obj = e.run(spawn("Build a landing page"), extra_env)
        self.assertEqual(obj, {"action": "pass"})
        self.assertEqual(e.stub.count, 0)                 # no routing call
        self.assertEqual(e.cache_files(), [])             # nothing done
        e.assert_no_side_logs(self)

    def test_env_kill_switch(self):
        with GateEnv(winners=WINNERS) as e:
            self.check_off(e, {"JEV_GATE_OFF": "1"})

    def test_env_zero_does_not_kill(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn("Build a landing page"), {"JEV_GATE_OFF": "0"})
            self.assertEqual(obj["action"], "rewrite")

    def test_flag_file(self):
        with GateEnv(winners=WINNERS) as e:
            open(os.path.join(e.state_dir, "jev-gate.off"), "w").close()
            self.check_off(e)

    def test_hook_profile_minimal(self):
        with GateEnv(winners=WINNERS) as e:
            with open(os.path.join(e.root, ".hook-profile"), "w") as f:
                f.write("minimal\n")
            self.check_off(e)

    def test_hook_profile_other_value_does_not_kill(self):
        with GateEnv(winners=WINNERS) as e:
            with open(os.path.join(e.root, ".hook-profile"), "w") as f:
                f.write("standard\n")
            self.assertEqual(e.run(spawn("Build a landing page"))["action"], "rewrite")

    def test_skill_route_child_is_a_noop(self):
        with GateEnv(winners=WINNERS) as e:
            self.check_off(e, {"SKILL_ROUTE_CHILD": "1"})

    def test_flag_file_in_root_state_dir_with_another_router_state_dir(self):
        with GateEnv(winners=WINNERS) as e:       # {root}/state/jev-gate.off, SKILL_ROUTE_STATE_DIR points elsewhere
            other = os.path.join(e.tmp, "other-state")
            os.makedirs(other)
            open(os.path.join(e.root, "state", "jev-gate.off"), "w").close()
            obj = e.run(spawn("Build a landing page"), {"SKILL_ROUTE_STATE_DIR": other})
            self.assertEqual(obj, {"action": "pass"})
            self.assertEqual(e.stub.count, 0)

    def test_default_router_state_dir_follows_the_root(self):
        with GateEnv(winners=WINNERS) as e:       # SKILL_ROUTE_STATE_DIR unset -> {root}/state/skill-route/jev-gate.off
            state = os.path.join(e.root, "state", "skill-route")
            os.makedirs(state)
            open(os.path.join(state, "jev-gate.off"), "w").close()
            obj = e.run(spawn("Build a landing page"), {"SKILL_ROUTE_STATE_DIR": None})
            self.assertEqual(obj, {"action": "pass"})
            self.assertEqual(e.stub.count, 0)

    def test_root_ladder_claude_config_dir(self):
        with GateEnv(winners=WINNERS) as e:       # AGENCY_HOME unset -> CLAUDE_CONFIG_DIR is the root
            alt = os.path.join(e.tmp, "alt-root")
            os.makedirs(alt)
            with open(os.path.join(alt, ".hook-profile"), "w") as f:
                f.write("minimal\n")
            obj = e.run(spawn("Build a landing page"), {"AGENCY_HOME": None, "CLAUDE_CONFIG_DIR": alt})
            self.assertEqual(obj, {"action": "pass"})
            self.assertEqual(e.stub.count, 0)


class ExemptTests(unittest.TestCase):
    def test_exempt_and_special_spawns_pass_untouched(self):
        with GateEnv(winners=WINNERS) as e:
            cases = [spawn("Build a landing page", subagent_type=t) for t in
                     ("critique-design", "Explore", "Plan", "codebase-search", "save-state-runner",
                      "project-scaffolder", "Delegator", "sag-critique", "council-opus", "caveman:cavecrew-builder",
                      "statusline-setup", "claude-code-guide", "architecture-analyzer", "article-analyzer",
                      "assemble-reviewer", "domain-analyzer", "file-analyzer", "graph-reviewer",
                      "knowledge-graph-guide", "project-scanner", "tour-builder", "foo-pd", "demo-project-pd")]
            cases += [spawn("Build a landing page", fork=True), spawn("Build a landing page", is_teammate=True),
                      spawn("Build a landing page", workflow=True)]
            for c in cases:
                self.assertEqual(e.run(c), {"action": "pass"}, c["subagent_type"])
            self.assertEqual(e.stub.count, 0)
            self.assertEqual(e.cache_files(), [])

    def test_binding_types_are_routed(self):
        with GateEnv(winners=WINNERS) as e:
            for t in ("general-purpose", "claude", "", "coord", "mini-coord", "pd-coordinator",
                      "never-heard-of"):
                e.stub.reset()
                obj = e.run(spawn("Build a landing page", subagent_type=t))
                self.assertGreater(e.stub.count, 0, t)
                self.assertNotEqual(obj, {"action": "pass"}, t)


class RoutedDecisionTests(unittest.TestCase):
    """evaluate() rows with NO cached id: the gate routes (stub Jev) and applies the table."""

    def test_no_line_gate_pass_skills_empty_injects_default(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn("Build a landing page"))
            self.assertEqual(obj["action"], "rewrite")
            self.assertRegex(obj["route_id"], r"^[0-9a-f]{8}$")
            self.assertEqual(obj["reason"], "auto_default")
            self.assertTrue(obj["prompt"].startswith("Skills: /frontend\n"))
            line = jev_spawn.parse_verdict_line(obj["prompt"])
            self.assertEqual((line["id"], line["verdict"]), (obj["route_id"], "accept"))
            self.assertIn("auto: Jev default (gate pass)", line["reason"])
            self.assertIn("injected Jev default skills /frontend", obj["note"])
            self.assertEqual(e.stub.count, 2)                      # two-stage router: ONE Jev route
            self.assertIsNotNone(jev_spawn.cache_get(obj["route_id"]))
            e.assert_no_side_logs(self)

    def test_no_line_gate_pass_skills_match_injects_auto_match_line(self):
        with GateEnv(winners=WINNERS) as e:
            p = "Skills: /frontend\nBuild a landing page"
            obj = e.run(spawn(p))
            self.assertEqual((obj["action"], obj["reason"]), ("rewrite", "auto_match"))
            self.assertTrue(obj["prompt"].startswith(p))
            line = jev_spawn.parse_verdict_line(obj["prompt"])
            self.assertEqual((line["id"], line["verdict"]), (obj["route_id"], "accept"))
            self.assertIn("auto: matches Jev", line["reason"])

    def test_no_line_gate_pass_skills_differ_denies(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn("Skills: /humanizer\nBuild a landing page"))
            self.assertEqual(obj["action"], "deny")
            self.assertIn("rule=no Jev line and Skills differ from Jev", obj["deny"])
            self.assertIn("Jev[r=%s]: accept" % obj["route_id"], obj["deny"])
            self.assertIn("Jev[r=%s]: modify" % obj["route_id"], obj["deny"])
            self.assertIn("Jev[r=%s]: reject" % obj["route_id"], obj["deny"])
            self.assertIn("jev_skills: /frontend", obj["deny"])
            self.assertIn("spawner_skills: /humanizer", obj["deny"])
            self.assertIn("skill-route.py --role exec", obj["deny"])
            self.assertEqual(e.denies(obj["route_id"]), 1)
            self.assertNotIn("prompt", obj)

    def test_no_line_low_confidence_denies(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            for p in ("Build a landing page", "Skills: /frontend\nBuild a landing page"):
                obj = e.run(spawn(p))
                self.assertEqual(obj["action"], "deny", p)
                self.assertIn("rule=no Jev line and gate is low_confidence", obj["deny"])
                self.assertIn("gate=low_confidence", obj["deny"])

    def test_no_line_none_fired_denies(self):
        with GateEnv(winners={"skill": "none"}, peak=0.9) as e:
            obj = e.run(spawn("Skills: /frontend\nBuild a landing page"))
            self.assertEqual(obj["action"], "deny")
            self.assertIn("none_fired=True", obj["deny"])

    def test_explicit_line_without_id_gets_the_fresh_id(self):
        with GateEnv(winners=WINNERS) as e:
            p = "Skills: /frontend\nJev: accept — fits\nBuild a landing page"
            obj = e.run(spawn(p))
            self.assertEqual((obj["action"], obj["reason"]), ("rewrite", "explicit"))
            line = jev_spawn.parse_verdict_line(obj["prompt"])
            self.assertEqual((line["id"], line["verdict"], line["reason"]), (obj["route_id"], "accept", "fits"))
            self.assertEqual(obj["prompt"].count("Jev"), 1)       # replaced, not duplicated
            self.assertIn("Build a landing page", obj["prompt"])

    def test_stale_id_not_in_cache_is_replaced_with_the_fresh_id(self):
        with GateEnv(winners=WINNERS) as e:
            p = "Skills: /frontend\nJev[r=deadbeef]: accept — fits\nBuild a landing page"
            obj = e.run(spawn(p))
            self.assertEqual(obj["action"], "rewrite")
            self.assertNotEqual(obj["route_id"], "deadbeef")
            self.assertNotIn("deadbeef", obj["prompt"])
            self.assertEqual(jev_spawn.parse_verdict_line(obj["prompt"])["id"], obj["route_id"])
            self.assertGreater(e.stub.count, 0)                    # a miss routes

    def test_every_rewrite_leaves_a_line_with_the_cache_id(self):
        with GateEnv(winners=WINNERS) as e:
            for p in ("Build a landing page", "Skills: /frontend\nBuild a landing page",
                      "Skills: /frontend\nJev: accept — fits\nBuild"):
                obj = e.run(spawn(p))
                self.assertEqual(obj["action"], "rewrite", p)
                self.assertEqual(jev_spawn.parse_verdict_line(obj["prompt"])["id"], obj["route_id"])
                self.assertIsNotNone(jev_spawn.cache_get(obj["route_id"]))

    def test_multiple_note_is_one_line(self):
        with GateEnv(winners=WINNERS) as e:
            obj = e.run(spawn("Build a landing page"))
            self.assertNotIn("\n", obj["note"])


    def test_cold_cache_idless_accept_with_differing_skills_denies(self):
        """No fail-open on a cold cache (empty state dir, no route cache): an id-less accept whose Skills header
        differs from Jev's is routed and denied. /humanizer stands in for a skill that differs from the fixture's
        Jev pick (/frontend)."""
        with GateEnv(winners=WINNERS) as e:
            self.assertEqual(e.cache_files(), [])
            obj = e.run(spawn("Skills: /humanizer\nJev: accept\nBuild a landing page"))
            self.assertEqual(obj["action"], "deny")
            self.assertIn("accept but Skills differ", obj["deny"])
            self.assertRegex(obj["route_id"], r"^[0-9a-f]{8}$")


class CacheHitTests(unittest.TestCase):
    """A prompt carrying Jev[r=<id>] that is in the cache: the cached Jev result is used, NO routing call."""

    def run_hit(self, e, prompt, **cache):
        rid = put_cache(**cache)
        e.stub.reset()
        obj = e.run(spawn(prompt.replace("<id>", rid)))
        self.assertEqual(e.stub.count, 0)                          # no routing call
        e.assert_no_side_logs(self)
        return rid, obj

    def test_accept_equal_skills_passes(self):
        with GateEnv() as e:
            rid, obj = self.run_hit(e, "Skills: /frontend, /tailwind\nJev[r=<id>]: accept\nBuild")
            self.assertEqual(obj, {"action": "pass", "route_id": rid, "reason": "explicit"})

    def test_accept_with_empty_skills_injects_jevs(self):
        with GateEnv() as e:
            rid, obj = self.run_hit(e, "Jev[r=<id>]: accept\nBuild a landing page")
            self.assertEqual(obj["action"], "rewrite")
            self.assertEqual(obj["prompt"], "Skills: /frontend, /tailwind\nJev[r=%s]: accept\nBuild a landing page" % rid)
            self.assertIn("injected Jev skills /frontend, /tailwind", obj["note"])

    def test_accept_but_skills_differ_denies(self):
        with GateEnv() as e:
            rid, obj = self.run_hit(e, "Skills: /frontend\nJev[r=<id>]: accept\nBuild")
            self.assertEqual(obj["action"], "deny")
            self.assertIn("accept but Skills differ: use modify", obj["deny"])
            self.assertEqual(e.denies(rid), 1)

    def test_modify_and_reject_need_a_reason(self):
        with GateEnv() as e:
            for v in ("modify", "reject"):
                rid, obj = self.run_hit(e, "Skills: /frontend\nJev[r=<id>]: %s\nBuild" % v)
                self.assertEqual(obj["action"], "deny", v)
                self.assertIn("reason required for modify/reject", obj["deny"])

    def test_modify_and_reject_with_reason_pass(self):
        with GateEnv() as e:
            rid, obj = self.run_hit(e, "Skills: /frontend\nJev[r=<id>]: modify — Jev missed the Tailwind side\nBuild")
            self.assertEqual(obj["action"], "pass")
            rid, obj = self.run_hit(e, "Skills: /humanizer\nJev[r=<id>]: reject — wrong domain\nBuild")
            self.assertEqual(obj["action"], "pass")

    def test_low_confidence_requires_a_reason_for_any_verdict(self):
        with GateEnv() as e:      # distinct task per case: the per-spawner guard keys on spawner + task
            for v in ("accept", "modify", "reject"):
                rid, obj = self.run_hit(e, "Skills: /frontend, /tailwind\nJev[r=<id>]: %s\nBuild %s" % (v, v), gate="low_confidence")
                self.assertEqual(obj["action"], "deny", v)
                self.assertIn("reason required on low_confidence", obj["deny"])
            # accept with no reason on low_confidence is denied even when Skills are empty (agreed deviation)
            rid, obj = self.run_hit(e, "Jev[r=<id>]: accept\nBuild bare", gate="low_confidence")
            self.assertEqual(obj["action"], "deny")
            rid, obj = self.run_hit(e, "Skills: /frontend, /tailwind\nJev[r=<id>]: accept — I checked\nBuild checked",
                                    gate="low_confidence")
            self.assertEqual(obj["action"], "pass")

    def test_confidential_and_none_fired_are_low_confidence(self):
        with GateEnv() as e:
            for kw in ({"confidential": True, "router": "grep"}, {"none_fired": True, "skills": []}):
                rid, obj = self.run_hit(e, "Skills: /frontend\nJev[r=<id>]: reject\nBuild", gate="pass", **kw)
                self.assertEqual(obj["action"], "deny", kw)
                self.assertIn("reason required on low_confidence", obj["deny"])
                rid, obj = self.run_hit(e, "Skills: /frontend\nJev[r=<id>]: reject — mine\nBuild", gate="pass", **kw)
                self.assertEqual(obj["action"], "pass", kw)

    def test_outage_cache_entry_with_line_passes_and_never_denies(self):
        with GateEnv() as e:
            rid, obj = self.run_hit(e, "Skills: /humanizer\nJev[r=<id>]: reject\nBuild", router="haiku",
                                    gate="low_confidence")
            self.assertEqual(obj["action"], "pass")

    def test_loop_guard_third_deny_becomes_pass(self):
        with GateEnv() as e:
            rid = put_cache(gate="low_confidence")
            p = spawn("Skills: /frontend\nJev[r=%s]: modify\nBuild" % rid)
            self.assertEqual(e.run(p)["action"], "deny")
            self.assertEqual(e.denies(rid), 1)
            self.assertEqual(e.run(p)["action"], "deny")
            self.assertEqual(e.denies(rid), 2)
            obj = e.run(p)                                       # >= 2 prior denies: pass
            self.assertEqual((obj["action"], obj["reason"], obj["route_id"]), ("pass", "deny_cap", rid))
            self.assertIn("deny cap reached", obj["note"])
            self.assertEqual(e.denies(rid), 2)                   # a pass does not bump
            self.assertEqual(e.stub.count, 0)

    def test_loop_guard_with_prebumped_entry(self):
        with GateEnv() as e:
            rid = put_cache(gate="low_confidence", denies=2)
            obj = e.run(spawn("Jev[r=%s]: accept\nBuild" % rid))
            self.assertEqual((obj["action"], obj["reason"]), ("pass", "deny_cap"))

    def test_deny_then_reissue_with_line_hits_cache(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            first = e.run(spawn("Skills: /frontend\nBuild a landing page"))
            self.assertEqual(first["action"], "deny")
            n = e.stub.count
            rid = first["route_id"]
            second = e.run(spawn("Skills: /frontend\nJev[r=%s]: modify — Jev also wanted tailwind\nBuild a landing page" % rid))
            self.assertEqual(second["action"], "pass")
            self.assertEqual(e.stub.count, n)                    # the re-issue made no routing call

    def test_uppercase_and_decorated_line_still_hits(self):
        with GateEnv() as e:
            rid = put_cache()
            e.stub.reset()
            obj = e.run(spawn("Skills: /frontend, /tailwind\n> JEV[R=%s]: ACCEPT\nBuild" % rid))
            # LINE_RE is case-insensitive and tolerates a leading quote/bullet marker; the id stays lowercase hex
            self.assertEqual(e.stub.count, 0)
            self.assertEqual(obj["action"], "pass")


class OutageTests(unittest.TestCase):
    def test_deadline_without_line_injects_unavailable(self):
        with GateEnv(stub_mode="slow", slow_seconds=5.0) as e:
            t0 = time.time()
            obj = e.run(spawn("Build a landing page"), {"JEV_GATE_DEADLINE": "0.4"})
            self.assertLess(time.time() - t0, 4.0)
            self.assertEqual(obj["action"], "rewrite")
            self.assertEqual(obj["reason"], "jev_unavailable")
            self.assertTrue(obj["prompt"].endswith("Jev: unavailable — router=timeout"))
            self.assertNotIn("route_id", obj)                    # no id: routing never answered
            self.assertNotIn("Skills:", obj["prompt"])
            self.assertNotEqual(obj["action"], "deny")

    def test_deadline_with_line_passes(self):
        with GateEnv(stub_mode="slow", slow_seconds=5.0) as e:
            obj = e.run(spawn("Skills: /frontend\nJev: modify — I know best\nBuild"), {"JEV_GATE_DEADLINE": "0.4"})
            self.assertEqual(obj["action"], "pass")

    def test_deadline_even_with_low_confidence_prone_input_never_denies(self):
        with GateEnv(stub_mode="slow", slow_seconds=5.0) as e:
            obj = e.run(spawn("Skills: /humanizer\nBuild"), {"JEV_GATE_DEADLINE": "0.4"})
            self.assertNotEqual(obj["action"], "deny")

    def test_router_error_falls_back_and_is_an_outage(self):
        with GateEnv(stub_mode="500") as e:               # Jev 500 -> Haiku fallback (fake claude) = router haiku
            obj = e.run(spawn("Build a landing page"))
            self.assertEqual(obj["action"], "rewrite")
            self.assertEqual(obj["reason"], "jev_unavailable")
            line = jev_spawn.parse_verdict_line(obj["prompt"])
            self.assertEqual((line["verdict"], line["id"]), ("unavailable", obj["route_id"]))
            self.assertRegex(line["reason"], r"^router=(haiku|grep)$")
            e.assert_no_side_logs(self)

    def test_router_error_with_line_passes(self):
        with GateEnv(stub_mode="500") as e:
            obj = e.run(spawn("Skills: /humanizer\nJev: reject — mine\nBuild"))
            self.assertEqual(obj["action"], "pass")

    def test_broken_menu_is_an_outage_not_a_crash(self):
        with GateEnv(winners=WINNERS) as e:
            bad = os.path.join(e.tmp, "bad-overlay.json")
            with open(e.overlay) as f:
                ov = json.load(f)
            ov["role_excludes"] = {"exec": ["no-such-skill"]}      # names an unroutable skill -> MenuError
            with open(bad, "w") as f:
                json.dump(ov, f)
            for t in ("general-purpose", "coord"):
                obj = e.run(spawn("Build a landing page", subagent_type=t), {"SKILL_ROUTE_OVERLAY": bad})
                self.assertEqual(obj["action"], "rewrite", t)
                self.assertTrue(obj["prompt"].endswith("Jev: unavailable \u2014 router=error"), obj["prompt"])

    def test_no_python_exception_leaks_on_unwritable_state_dir(self):
        with GateEnv(winners=WINNERS) as e:
            blocker = os.path.join(e.tmp, "state-is-a-file")
            open(blocker, "w").close()
            rc, out, err = e.run_raw(json.dumps(spawn("Build a landing page")),
                                     {"SKILL_ROUTE_STATE_DIR": blocker})
            self.assertEqual((rc, err), (0, ""))
            self.assertIsNotNone(parse_jev_gate(out))          # cache write failed: still one valid JSON line


class SideEffectTests(unittest.TestCase):
    def test_gate_never_writes_feedback_shadow_or_decision_logs(self):
        with GateEnv(winners=WINNERS) as e:
            for p in ("Build a landing page", "Skills: /humanizer\nBuild", "Skills: /frontend\nBuild"):
                e.run(spawn(p))
            e.assert_no_side_logs(self)
            usage = [u for u in e.usage_records() if u["router"] == "jev"]
            self.assertTrue(usage and all(u["shadow"] is False for u in usage))   # LIVE accounting

    def test_cache_entries_hold_no_task_text(self):
        with GateEnv(winners=WINNERS) as e:
            e.run(spawn("Build a landing page for ACME-UNIQUE-TOKEN"))
            d = os.path.join(e.state_dir, "jev-route-cache")
            for f in e.cache_files():
                with open(os.path.join(d, f)) as fh:
                    self.assertNotIn("ACME-UNIQUE-TOKEN", fh.read())

    def test_second_run_reusing_the_rewritten_prompt_hits_the_cache(self):
        with GateEnv(winners=WINNERS) as e:
            first = e.run(spawn("Build a landing page"))
            n = e.stub.count
            second = e.run(spawn(first["prompt"]))
            self.assertEqual(e.stub.count, n)                    # idempotent: no second Jev call
            self.assertEqual((second["action"], second["route_id"]), ("pass", first["route_id"]))


class SpawnerLoopGuardTests(unittest.TestCase):
    """Second deny loop-guard keyed per spawner + task: a spawner that re-issues WITHOUT the Jev line gets a fresh
    route id every time, so only the spawner key can stop the loop. Temp state dir only (GateEnv)."""

    TASK = "Build a landing page"

    def guard_files(self, e):
        d = os.path.join(e.state_dir, "jev-gate-denies")
        return sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []

    def test_reissue_without_line_deny_deny_pass_deny_cap(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            outs = [e.run(spawn(self.TASK)) for _ in range(3)]
            self.assertEqual([o["action"] for o in outs], ["deny", "deny", "pass"])
            self.assertEqual(outs[2]["reason"], "deny_cap")
            self.assertIn("deny cap reached", outs[2]["note"])
            self.assertEqual(len(set(o["route_id"] for o in outs)), 3)   # fresh id each time: per-id guard blind
            self.assertEqual(len(self.guard_files(e)), 1)
            e.assert_no_side_logs(self)

    def guard_denies(self, e):
        d = os.path.join(e.state_dir, "jev-gate-denies")
        out = []
        for f in self.guard_files(e):
            with open(os.path.join(d, f)) as fh:
                out.append(json.load(fh)["denies"])
        return out

    def test_cap_holds_on_the_fourth_call_and_a_pass_does_not_bump(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            outs = [e.run(spawn(self.TASK)) for _ in range(4)]
            self.assertEqual([o["action"] for o in outs], ["deny", "deny", "pass", "pass"])
            self.assertEqual(self.guard_denies(e), [2])

    def test_different_spawner_same_text_is_independent(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            a = [e.run(spawn(self.TASK, parent_spawn_id="sp-A")) for _ in range(3)]
            self.assertEqual([o["action"] for o in a], ["deny", "deny", "pass"])
            b = e.run(spawn(self.TASK, parent_spawn_id="sp-B"))
            self.assertEqual(b["action"], "deny")                        # B has its own budget
            c = e.run(spawn(self.TASK, parent_agent="coord"))            # no spawn id: keyed on the agent type
            self.assertEqual(c["action"], "deny")
            self.assertEqual(len(self.guard_files(e)), 3)

    def test_different_task_same_spawner_is_independent(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            for _ in range(3):
                e.run(spawn(self.TASK))
            self.assertEqual(e.run(spawn("Write the pricing copy"))["action"], "deny")

    def test_key_is_stable_across_skills_and_stale_line(self):
        with GateEnv(winners=WINNERS) as e:     # gate pass + Skills differ from Jev -> deny every time
            variants = ["Skills: /humanizer\n" + self.TASK,
                        "Skills: /proofreader\n" + self.TASK,
                        "Skills: /humanizer\nJev[r=deadbeef]: accept\n" + self.TASK]
            outs = [e.run(spawn(p)) for p in variants]
            self.assertEqual([o["action"] for o in outs], ["deny", "deny", "pass"])
            self.assertEqual(outs[2]["reason"], "deny_cap")
            self.assertEqual(len(self.guard_files(e)), 1)

    def test_per_route_id_guard_is_kept(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            rid = put_cache(gate="low_confidence")
            for _ in range(2):
                e.run(spawn("Skills: /frontend\nJev[r=%s]: modify\nBuild" % rid))
            obj = e.run(spawn("Skills: /frontend\nJev[r=%s]: modify\nBuild" % rid))
            self.assertEqual((obj["action"], obj["reason"]), ("pass", "deny_cap"))

    def test_effective_denies_is_max_of_both_counters(self):
        with GateEnv(winners=WINNERS) as e:
            rid = put_cache(gate="low_confidence")
            p = spawn("Skills: /frontend\nJev[r=%s]: modify\nBuild" % rid)
            self.assertEqual(e.run(p)["action"], "deny")        # route counter 1, spawner counter 1
            (f,) = self.guard_files(e)
            key = f[:-5]
            jev_spawn.spawner_bump_denies(key)                  # spawner counter 2 (cap), route counter stays 1
            self.assertEqual(e.denies(rid), 1)
            obj = e.run(p)
            self.assertEqual((obj["action"], obj["reason"]), ("pass", "deny_cap"))

    def test_deny_bumps_both_counters(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            obj = e.run(spawn(self.TASK))
            self.assertEqual(obj["action"], "deny")
            self.assertEqual(e.denies(obj["route_id"]), 1)
            self.assertEqual(self.guard_denies(e), [1])

    def test_expired_spawner_entry_does_not_count(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            for _ in range(2):
                e.run(spawn(self.TASK))
            d = os.path.join(e.state_dir, "jev-gate-denies")
            old = time.time() - jev_spawn.SPAWNER_TTL_SECONDS - 120
            for f in self.guard_files(e):
                os.utime(os.path.join(d, f), (old, old))
                with open(os.path.join(d, f)) as fh:
                    ent = json.load(fh)
                ent["ts"] = old
                with open(os.path.join(d, f), "w") as fh:
                    json.dump(ent, fh)
            self.assertEqual(e.run(spawn(self.TASK))["action"], "deny")     # budget is fresh again

    def test_corrupt_spawner_file_counts_as_zero_and_gate_still_answers(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            e.run(spawn(self.TASK))
            d = os.path.join(e.state_dir, "jev-gate-denies")
            for f in os.listdir(d):
                with open(os.path.join(d, f), "w") as fh:
                    fh.write("{corrupt")
            self.assertEqual(e.run(spawn(self.TASK))["action"], "deny")

    def test_unusable_guard_dir_fails_open_to_per_id_behaviour(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            with open(os.path.join(e.state_dir, "jev-gate-denies"), "w") as fh:
                fh.write("blocks the directory")
            outs = [e.run(spawn(self.TASK)) for _ in range(3)]
            self.assertEqual([o["action"] for o in outs], ["deny", "deny", "deny"])   # no spawner guard, no crash

    def test_state_files_hold_no_task_text(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            e.run(spawn("Build a landing page for ACME-UNIQUE-TOKEN"))
            d = os.path.join(e.state_dir, "jev-gate-denies")
            for f in self.guard_files(e):
                with open(os.path.join(d, f)) as fh:
                    self.assertNotIn("ACME-UNIQUE-TOKEN", fh.read())


class GateDenyLogTests(unittest.TestCase):
    """F4: every deny and deny_cap appends ONE gate_deny line to the shadow log (fail open); nothing else does."""

    KEYS = {"ts", "event", "decision", "route_id", "rule", "gate", "router", "none_fired", "confidential",
            "jev_skills", "spawner_skills", "subagent_type", "parent_agent", "spawner", "denies_after",
            "task_excerpt"}

    def test_deny_writes_exactly_one_full_gate_deny_row(self):
        with GateEnv() as e:
            rid = put_cache()
            obj = e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\nBuild the page" % rid, parent_agent="demo-project-pd",
                              parent_spawn_id="sp-9"))
            self.assertEqual(obj["action"], "deny")
            rows = e.gate_denies()
            self.assertEqual(len(rows), 1)
            r = rows[0]
            self.assertEqual(set(r), self.KEYS)
            self.assertEqual((r["event"], r["decision"], r["route_id"]), ("gate_deny", "deny", rid))
            self.assertIn("accept but Skills differ: use modify", r["rule"])
            self.assertEqual((r["gate"], r["router"], r["none_fired"], r["confidential"]),
                             ("pass", "jev", False, False))
            self.assertEqual(r["jev_skills"], J)
            self.assertEqual(r["spawner_skills"], ["frontend"])
            self.assertEqual((r["subagent_type"], r["parent_agent"], r["spawner"]),
                             ("general-purpose", "demo-project-pd", "sp-9"))
            self.assertEqual(r["denies_after"], 1)
            self.assertIn("Build the page", r["task_excerpt"])
            self.assertRegex(r["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertEqual(e.feedbacks(), [])
            self.assertEqual(e.decisions(), [])

    def test_spawner_defaults_to_parent_agent_then_root(self):
        with GateEnv() as e:
            rid = put_cache()
            e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\nBuild one" % rid, parent_agent="coord"))
            e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\nBuild two" % rid))
            self.assertEqual([r["spawner"] for r in e.gate_denies()], ["coord", "root"])

    def test_denies_after_counts_up_and_deny_cap_row_follows(self):
        with GateEnv() as e:
            rid = put_cache(gate="low_confidence")
            p = spawn("Skills: /frontend\nJev[r=%s]: modify\nBuild" % rid)
            outs = [e.run(p) for _ in range(3)]
            self.assertEqual([o["action"] for o in outs], ["deny", "deny", "pass"])
            rows = e.gate_denies()
            self.assertEqual([(r["decision"], r["denies_after"]) for r in rows],
                             [("deny", 1), ("deny", 2), ("deny_cap", 2)])
            self.assertTrue(rows[2]["rule"])

    def test_deny_cap_pass_on_prebumped_entry_logs_deny_cap(self):
        with GateEnv() as e:
            rid = put_cache(gate="low_confidence", denies=2)
            obj = e.run(spawn("Jev[r=%s]: accept\nBuild" % rid))
            self.assertEqual((obj["action"], obj["reason"]), ("pass", "deny_cap"))
            (r,) = e.gate_denies()
            self.assertEqual((r["event"], r["decision"], r["route_id"], r["denies_after"]),
                             ("gate_deny", "deny_cap", rid, 2))
            self.assertEqual(set(r), self.KEYS)

    def test_confidential_deny_excerpt_is_redacted_literal(self):
        with GateEnv() as e:
            rid = put_cache(confidential=True, router="grep")
            obj = e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\nSECRET-CONFIDENTIAL-TOKEN build" % rid))
            self.assertEqual(obj["action"], "deny")
            self.assertIn("reason required on low_confidence", obj["deny"])
            (r,) = e.gate_denies()
            self.assertTrue(r["confidential"])
            self.assertEqual(r["task_excerpt"], "[REDACTED:confidential]")
            with open(e.shadow_log, encoding="utf-8") as fh:
                self.assertNotIn("SECRET-CONFIDENTIAL-TOKEN", fh.read())

    def test_task_excerpt_is_capped_at_200_and_whitespace_squashed(self):
        with GateEnv() as e:
            rid = put_cache()
            body = "word   \n\n  " * 120
            e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\n%s" % (rid, body)))
            (r,) = e.gate_denies()
            self.assertLessEqual(len(r["task_excerpt"]), 200)
            self.assertGreater(len(r["task_excerpt"]), 100)
            self.assertNotIn("\n", r["task_excerpt"])
            self.assertNotIn("  ", r["task_excerpt"])

    def test_task_excerpt_redacts_secrets(self):
        with GateEnv() as e:
            rid = put_cache()
            e.run(spawn("Skills: /frontend\nJev[r=%s]: accept\nUse API_KEY=sk-supersecretvalue1234567890 here" % rid))
            (r,) = e.gate_denies()
            self.assertNotIn("sk-supersecretvalue1234567890", r["task_excerpt"])

    def test_unwritable_shadow_log_changes_nothing(self):
        with GateEnv() as e:
            blocker = os.path.join(e.tmp, "log-is-a-file")
            open(blocker, "w").close()
            bad = os.path.join(blocker, "sub", "shadow.jsonl")
            rid = put_cache()
            rc, out, err = e.run_raw(json.dumps(spawn("Skills: /frontend\nJev[r=%s]: accept\nBuild" % rid)),
                                     {"SKILL_ROUTE_SHADOW_LOG": bad})
            self.assertEqual((rc, err), (0, ""))
            obj = json.loads(out)
            self.assertEqual(out.count("\n"), 1)
            self.assertEqual(obj["action"], "deny")                 # same output as with a healthy log
            self.assertIn("accept but Skills differ: use modify", obj["deny"])
            self.assertEqual(e.denies(rid), 1)                      # counters still bumped
            self.assertEqual(e.shadows(), [])

    def test_pass_and_rewrite_paths_write_no_gate_deny_row(self):
        with GateEnv(winners=WINNERS) as e:
            e.run(spawn("Build a landing page"))                                    # rewrite auto_default
            e.run(spawn("Skills: /frontend\nBuild a landing page"))                  # rewrite auto_match
            e.run(spawn("Skills: /frontend\nJev: accept \u2014 fits\nBuild a page"))   # rewrite explicit
            e.run(spawn("Build", subagent_type="Explore"))                          # exempt pass
            rid = put_cache()
            e.run(spawn("Skills: /frontend, /tailwind\nJev[r=%s]: accept\nBuild" % rid))   # cached pass
            self.assertEqual(e.shadows(), [])
            e.assert_no_side_logs(self)

    def test_outage_writes_no_gate_deny_row(self):
        with GateEnv(stub_mode="slow", slow_seconds=5.0) as e:
            e.run(spawn("Build a landing page"), {"JEV_GATE_DEADLINE": "0.4"})
            self.assertEqual(e.shadows(), [])

    def test_logging_never_touches_feedback_and_keeps_one_stdout_line(self):
        with GateEnv(winners=WINNERS, peak=0.3) as e:
            for _ in range(3):
                e.run(spawn("Build a landing page"))        # deny, deny, deny_cap pass (run() asserts one line, no stderr)
            self.assertEqual([r["decision"] for r in e.gate_denies()], ["deny", "deny", "deny_cap"])
            self.assertEqual(e.feedbacks(), [])


class AutoEmptyAndConfidentialLocalTests(unittest.TestCase):
    """F1/F2 gate surface: the spawner note names the real reason (not the generic "set the route id" fallback)."""

    def test_auto_empty_note_and_line(self):
        with GateEnv(winners={"skill": "none"}, peak=0.9) as e:
            obj = e.run(spawn("Build a landing page"))
            self.assertEqual((obj["action"], obj["reason"]), ("rewrite", "auto_empty"))
            self.assertEqual(obj["note"], "jev-gate: Jev found nothing and no Skills named; injected Jev line, "
                                          "recorded accept")
            self.assertNotIn("set the route id", obj["note"])
            line = jev_spawn.parse_verdict_line(obj["prompt"])
            self.assertEqual((line["id"], line["verdict"]), (obj["route_id"], "accept"))
            self.assertIsNotNone(jev_spawn.cache_get(obj["route_id"]))


if __name__ == "__main__":
    unittest.main()

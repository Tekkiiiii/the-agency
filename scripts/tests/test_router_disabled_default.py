"""Regression tests: the skill router ships DISABLED, and disabled means no network call, ever.

AGENCY_SKILL_ROUTER must be exactly "1" for anything to reach Jev or the Claude CLI. These tests point the
client at a local counting stub and a fake `claude`, switch the router off (unset, "0", "true", "") and assert
zero requests and zero fake-claude invocations on every entry point: jev_client.ask(), route(), the CLI (all
argument shapes, stdin, --shadow, --rebuild-menu) and the recorder. Everything lives in temp dirs.

The end-to-end proof with a socket/subprocess guard is .github/scripts/check-skill-route-disabled.py (CI);
this file keeps the same guarantee inside the unit suite.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_router_disabled_default*' -v
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import jev_stub  # noqa: E402
import jev_client  # noqa: E402
import test_jev_router as tr  # noqa: E402  (RouterEnv, run_main, sr)

sr = tr.sr
OFF_VALUES = (None, "", "0", "true", "yes", "on", " 1", "1 ")


def off(value):
    """extra_env that switches the router off: None removes the variable."""
    return {"AGENCY_SKILL_ROUTER": value}


class DisabledDefaultTests(unittest.TestCase):
    def assert_silent(self, e, what):
        self.assertEqual(e.stub.count, 0, "%s reached the Jev endpoint" % what)
        self.assertEqual(jev_stub.fake_claude_records(e.fake_claude), [], "%s invoked the claude CLI" % what)
        self.assertEqual(e.usage_records(), [], "%s wrote a usage record" % what)
        self.assertFalse(e.flag_exists(), "%s wrote the jev-down flag" % what)

    def test_switch_is_exactly_one(self):
        for value in OFF_VALUES:
            with tr.RouterEnv(extra_env=off(value)) as e:
                self.assertFalse(jev_client.router_enabled(), repr(value))
                self.assertFalse(sr.router_enabled(), repr(value))
                self.assertEqual(os.environ.get("AGENCY_SKILL_ROUTER"), value)
        with tr.RouterEnv(extra_env=off("1")):
            self.assertTrue(jev_client.router_enabled())
            self.assertTrue(sr.router_enabled())

    def test_client_ask_refuses_and_makes_no_request(self):
        for value in OFF_VALUES:
            with tr.RouterEnv(extra_env=off(value)) as e:
                for allow_jev in (True, False):
                    with self.assertRaises(jev_client.RouterUnavailable) as cm:
                        jev_client.ask("build a landing page", {"model": {"type": "choice", "criteria": {"a": "x"}}},
                                       "skill-route", allow_jev=allow_jev)
                    self.assertEqual(cm.exception.reason, "disabled", repr(value))
                self.assert_silent(e, "jev_client.ask with the switch %r" % (value,))

    def test_route_in_process_degrades_to_grep_without_a_call(self):
        for value in OFF_VALUES:
            with tr.RouterEnv(extra_env=off(value)) as e:
                for router in (None, "jev", "haiku"):
                    res = sr.route("build a responsive landing page with tailwind", router=router, log=False)
                    self.assertEqual(res["router"], "grep", (value, router))
                    self.assertEqual(res["gate"], "low_confidence")
                self.assert_silent(e, "route() with the switch %r" % (value,))

    def test_cli_prints_the_pinned_line_for_every_argument_shape(self):
        shapes = (
            (["build a landing page"], None),
            (["--router", "jev", "--mode", "flat", "x"], None),
            (["--rebuild-menu"], None),
            (["--shadow"], json.dumps({"description": "d", "prompt": "Skills: /frontend\nBuild", "subagent_type": "general-purpose"})),
            (["--shadow-report"], None),
            ([], "text on stdin"),
        )
        for value in OFF_VALUES:
            with tr.RouterEnv(extra_env=off(value)) as e:
                for argv, stdin in shapes:
                    rc, out, err = tr.run_main(argv, stdin or "")
                    self.assertEqual((rc, out.strip(), err), (0, sr.DISABLED_LINE, ""), (value, argv))
                    self.assertEqual(json.loads(out)["router"], "disabled")
                self.assert_silent(e, "the CLI with the switch %r" % (value,))
                # nothing written either: no shadow log, no decision log, no feedback record, no menu cache
                for path in (e.shadow_log, e.decision_log, e.feedback_log,
                             os.path.join(e.state_dir, "skill-route-menu.json")):
                    self.assertFalse(os.path.exists(path) and os.path.getsize(path) > 0, path)

    def test_subprocess_cli_is_silent_and_makes_no_request(self):
        with tr.RouterEnv(extra_env=off(None)) as e:
            env = dict(os.environ)
            env.pop("AGENCY_SKILL_ROUTER", None)
            p = subprocess.run([sys.executable, tr.ROUTER_PATH, "build a landing page"], env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.decode().strip(), sr.DISABLED_LINE)
            self.assertEqual(p.stderr, b"")
            self.assert_silent(e, "the CLI subprocess")

    def test_recorder_does_nothing_while_disabled(self):
        with tr.RouterEnv(extra_env=off(None)) as e:
            rc, out, err = tr.run_main(["--shadow"], json.dumps(
                {"spawn_id": "sp-1", "subagent_type": "general-purpose", "description": "Build the page",
                 "prompt": "Skills: /frontend\nJev[r=3fa9c1d2]: accept\nBuild a landing page"}))
            self.assertEqual((rc, err), (0, ""))
            self.assertEqual(out.strip(), sr.DISABLED_LINE)
            self.assertEqual((e.shadows(), e.feedbacks()), ([], []))
            self.assert_silent(e, "the recorder")

    def test_enabled_control_does_reach_the_stub(self):
        # a positive control: the same setup with the switch on DOES call the stub, so the zero counts above mean something
        with tr.RouterEnv(extra_env=off("1")) as e:
            res = sr.route("build a landing page", log=False)
            self.assertEqual(res["router"], "jev")
            self.assertGreater(e.stub.count, 0)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for scripts/jev-drill.py safe defaults. Temp dirs only; no network, no Haiku, no real `claude`.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_drill*' -v

The module constants that point at LIVE paths (REAL_STATE, DEFAULT_NOTIFY_LOG, EVENTS_FILE, ...) are patched to
a temp "fake live" tree, and run_cli is replaced by a fake child that writes where the real child would write
(flag in SKILL_ROUTE_STATE_DIR, a line in JEV_NOTIFY_LOG, an OS-notification marker unless JEV_NOTIFY=0, an
event line unless JEV_EMIT=0). So even a failing test can never touch a real install.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_00_isolation  # noqa: E402,F401  (run alone, inputs_fingerprint -> skill-route load_menu wrote the REAL state/skill-route-menu.json; no-op under discover)
SCRIPT = os.path.join(os.path.dirname(HERE), "jev-drill.py")

_spec = importlib.util.spec_from_file_location("jev_drill_under_test", SCRIPT)
drill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drill)

REAL_ROOT = os.path.join(os.path.expanduser("~"), ".claude")


def under(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


class DrillSafeDefaults(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="jd-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.live = os.path.join(self.tmp, "live")          # fake "live" root
        self.state = os.path.join(self.live, "state")
        self.logs = os.path.join(self.live, "logs")
        self.notify = os.path.join(self.logs, "jev-notify.log")
        self.events = os.path.join(self.live, "events.jsonl")
        self.usage = os.path.join(self.logs, "jev-usage.jsonl")
        self.osa = os.path.join(self.live, "osascript-fired")
        self.out = os.path.join(self.tmp, "out")
        os.makedirs(self.state)
        os.makedirs(self.logs)
        os.makedirs(self.out)
        for p, body in ((self.notify, "seed-notify\n"), (self.events, '{"event":"seed"}\n'),
                        (self.usage, '{"seed":1}\n')):
            with open(p, "w") as fh:
                fh.write(body)
        self.flag = os.path.join(self.state, "jev-down")
        self.envs = []          # env of every fake child call
        self.raise_after_flag = False

        env = mock.patch.dict(os.environ, {"AGENCY_SKILL_ROUTER": "1", "AGENCY_HOME": self.live})  # the drill needs the switch
        env.start()
        self.addCleanup(env.stop)
        for name, val in (("ROOT", self.live), ("REAL_STATE", self.state),
                          ("ISOLATED_STATE", os.path.join(self.state, "jev-drill")),
                          ("DEFAULT_NOTIFY_LOG", self.notify), ("DEFAULT_USAGE_LOG", self.usage),
                          ("EVENTS_FILE", self.events), ("DEFAULT_RESULTS", os.path.join(self.live, "results"))):
            p = mock.patch.object(drill, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(drill, "run_cli", self.fake_run_cli)
        p.start()
        self.addCleanup(p.stop)

    # fake child: mimics what skill-route.py / jev_client.py do on an outage
    def fake_run_cli(self, step_env):
        self.envs.append(dict(step_env))
        sd = step_env["SKILL_ROUTE_STATE_DIR"]
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "jev-down"), "w") as fh:
            json.dump({"failures": 1, "reason": "http"}, fh)
        with open(step_env["JEV_NOTIFY_LOG"], "a") as fh:
            fh.write("2026-10-12T00:00:00\tdown\n")
        if step_env.get("JEV_NOTIFY") != "0":
            with open(self.osa, "a") as fh:
                fh.write("osascript fired\n")
        if step_env.get("JEV_EMIT") != "0":
            with open(drill.EVENTS_FILE, "a") as fh:
                fh.write('{"event":"jev_down"}\n')
        if self.raise_after_flag:
            raise RuntimeError("boom")
        return {"rc": 0, "elapsed_s": 0.0, "out": {"router": "haiku"}, "err": ""}

    def snap(self):
        out = {}
        for p in (self.notify, self.events, self.usage, self.flag, self.osa):
            try:
                with open(p, "rb") as fh:
                    out[p] = fh.read()
            except OSError:
                out[p] = None
        return out

    def run_main(self, *extra):
        argv = ["--steps", "s1", "--results-dir", self.out,
                "--usage-log", os.path.join(self.out, "u.jsonl")] + list(extra)
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = drill.main(argv)
        return rc, buf.getvalue(), err.getvalue()

    # ---- default run: nothing live is touched
    def test_default_leaves_live_state_notify_events_untouched(self):
        before = self.snap()
        self.run_main()
        self.assertEqual(self.snap(), before)
        self.assertFalse(os.path.exists(self.osa), "OS notification fired in a default run")

    def test_default_child_env_is_safe(self):
        self.run_main()
        env = self.envs[0]
        self.assertEqual(env.get("JEV_NOTIFY"), "0")
        self.assertEqual(env.get("JEV_EMIT"), "0")
        self.assertEqual(env.get("JEV_PURPOSE"), "drill")
        self.assertFalse(under(env["SKILL_ROUTE_STATE_DIR"], self.live), "state dir is under live")
        self.assertNotEqual(os.path.realpath(env["JEV_NOTIFY_LOG"]), os.path.realpath(self.notify))
        self.assertFalse(under(env["JEV_NOTIFY_LOG"], self.live), "notify log is under live")

    def test_default_temp_dirs_removed_at_exit(self):
        self.run_main()
        env = self.envs[0]
        self.assertFalse(os.path.exists(env["SKILL_ROUTE_STATE_DIR"]))
        self.assertFalse(os.path.exists(env["JEV_NOTIFY_LOG"]))

    def test_default_reports_flag_left_before_removing(self):
        rc, _, _ = self.run_main()
        self.assertNotEqual(rc, 0)    # the fake child leaves a flag behind -> drill fails
        with open(self._results_path()) as fh:
            doc = json.load(fh)
        self.assertTrue(doc["flag_left"])
        self.assertFalse(doc["notify_real"])
        self.assertFalse(doc["events_checked"])
        self.assertFalse(under(doc["state_dir"], self.live))

    def _results_path(self):
        names = [n for n in os.listdir(self.out) if n.endswith(".json")]
        self.assertEqual(len(names), 1)
        return os.path.join(self.out, names[0])

    # ---- --real-state: opt-in, flag always restored
    def test_real_state_removes_flag_it_created(self):
        self.run_main("--real-state")
        self.assertTrue(self.envs[0]["SKILL_ROUTE_STATE_DIR"] == self.state)
        self.assertFalse(os.path.exists(self.flag), "drill left the live flag behind")

    def test_real_state_removes_flag_even_when_run_raises(self):
        self.raise_after_flag = True
        with self.assertRaises(RuntimeError):
            self.run_main("--real-state")
        self.assertFalse(os.path.exists(self.flag), "flag survived an exception")

    def test_real_state_removes_flag_on_keyboard_interrupt(self):
        def ctrl_c(*a, **k):
            with open(self.flag, "w") as fh:
                fh.write("{}")
            raise KeyboardInterrupt
        with mock.patch.object(drill, "run_tool", side_effect=ctrl_c):
            with self.assertRaises(KeyboardInterrupt):
                self.run_main("--real-state")
        self.assertFalse(os.path.exists(self.flag))

    def test_real_state_refuses_when_flag_exists_and_keeps_it(self):
        with open(self.flag, "w") as fh:
            fh.write('{"failures": 9}')
        rc, _, err = self.run_main("--real-state")
        self.assertEqual(rc, 2)
        self.assertIn("refusing", err)
        self.assertEqual(self.envs, [])
        with open(self.flag) as fh:
            self.assertEqual(fh.read(), '{"failures": 9}')

    def test_real_state_with_default_notify_stays_off_live_notify(self):
        before = self.snap()
        self.run_main("--real-state")
        after = self.snap()
        self.assertEqual(after[self.notify], before[self.notify])
        self.assertEqual(after[self.events], before[self.events])
        self.assertFalse(os.path.exists(self.osa))
        self.assertEqual(self.envs[0].get("JEV_NOTIFY"), "0")

    # ---- opt-ins
    def test_real_notify_uses_live_log_and_unsets_jev_notify(self):
        self.run_main("--real-notify")
        env = self.envs[0]
        self.assertEqual(env["JEV_NOTIFY_LOG"], self.notify)
        self.assertNotIn("JEV_NOTIFY", env)
        self.assertTrue(os.path.exists(self.osa))
        with open(self.notify) as fh:
            self.assertIn("down", fh.read())

    def test_no_notify_overrides_real_notify(self):
        self.run_main("--real-notify", "--no-notify")
        self.assertEqual(self.envs[0].get("JEV_NOTIFY"), "0")
        self.assertFalse(os.path.exists(self.osa))

    def test_events_on_is_opt_in(self):
        self.run_main("--events", "on")
        self.assertNotEqual(self.envs[0].get("JEV_EMIT"), "0")
        with open(self.events) as fh:
            self.assertIn("jev_down", fh.read())

    def test_explicit_notify_log_honoured(self):
        mine = os.path.join(self.tmp, "mine.log")
        before = self.snap()
        self.run_main("--notify-log", mine)
        self.assertEqual(self.envs[0]["JEV_NOTIFY_LOG"], mine)
        self.assertEqual(self.envs[0].get("JEV_NOTIFY"), "0")
        with open(mine) as fh:
            self.assertIn("down", fh.read())
        self.assertEqual(self.snap(), before)

    def test_notify_log_pointing_at_live_log_refused_without_real_notify(self):
        before = self.snap()
        rc, _, err = self.run_main("--notify-log", self.notify)
        self.assertEqual(rc, 2)
        self.assertIn("--real-notify", err)
        self.assertEqual(self.envs, [])
        self.assertEqual(self.snap(), before)


class DrillDisabledByDefault(unittest.TestCase):
    """Without AGENCY_SKILL_ROUTER=1 the drill refuses before it imports anything router-related or writes a file."""

    def test_disabled_prints_one_line_and_writes_nothing(self):
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="jd-off-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        out = os.path.join(tmp, "results")
        buf = io.StringIO()
        env = dict(os.environ)
        env.pop("AGENCY_SKILL_ROUTER", None)
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(buf):
            with mock.patch.object(drill, "_drill", side_effect=AssertionError("ran while disabled")):
                rc = drill.main(["--results-dir", out, "--usage-log", os.path.join(tmp, "u.jsonl")])
        self.assertEqual(rc, 0)
        self.assertIn("skill router disabled", buf.getvalue())
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 1)
        self.assertEqual(os.listdir(tmp), [])


if __name__ == "__main__":
    unittest.main()

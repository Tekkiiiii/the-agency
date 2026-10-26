"""Unit tests for scripts/jev_client.py. No network except 127.0.0.1 stubs (jev_stub.py); no real
notifications; no real `claude`; the key in every test is the BOGUS literal from jev_stub.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_client*' -v
(and the same with /usr/bin/python3, 3.9).
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import jev_stub  # noqa: E402
import jev_client  # noqa: E402

BOGUS = jev_stub.BOGUS_KEY
FIXTURES = os.path.join(HERE, "fixtures", "jev")

QUESTIONS = {
    "domain": {"type": "choice", "instructions": "Which domain?",
               "criteria": {"frontend-ui": "web ui", "backend": "apis", "writing-en": "english copy"}},
    "complexity": {"type": "score", "instructions": "How complex?",
                   "criteria": ["trivial", "small", "medium", "large", "huge"]},
}


class EnvCase(unittest.TestCase):
    """Fresh temp env + stub + fake claude per test."""

    claude_behavior = "valid"
    extra_env = None

    def setUp(self):
        self._cm = jev_stub.jev_test_env(claude_behavior=self.claude_behavior, extra_env=self.extra_env)
        self.env = self._cm.__enter__()
        self.stub = self.env.stub

    def tearDown(self):
        self._cm.__exit__(None, None, None)

    def ask(self, state="route this task", **kw):
        kw.setdefault("purpose", "skill-route")
        return jev_client.ask(state, QUESTIONS, **kw)


# --------------------------------------------------------------------------- redaction / state
def _samples():
    # Built by concatenation so this file never contains a literal that looks like a real secret.
    return {
        "sk-ant": "sk-" + "ant-api03-" + "A" * 24,
        "sk-": "sk-" + "B" * 32,
        "jwt": "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + ".abcDEF123_-xyz",
        "ghp": "gh" + "p_" + "C" * 30,
        "github_pat": "github" + "_pat_" + "D" * 30,
        "xox": "xo" + "xb-" + "1234567890-abcdefghij",
        "ya29": "ya" + "29." + "E" * 30,
        "akia": "AK" + "IA" + "ABCDEFGHIJKLMNOP",
        "bearer": "Bearer " + "F" * 24,
    }


class RedactTests(unittest.TestCase):
    def test_each_secret_family_is_redacted(self):
        for name, secret in _samples().items():
            out = jev_client.redact("before %s after" % secret)
            self.assertNotIn(secret, out, name)
            self.assertIn("[REDACTED]", out, name)
            self.assertTrue(out.startswith("before ") and out.endswith(" after"), name)

    def test_assignment_values_redacted(self):
        cases = ["MY_API_KEY=supersecretvalue1", "GITHUB_TOKEN=abcd1234efgh", 'DB_PASSWORD: "hunter2hunter2"',
                 '{"client_secret": "zzzz9999yyyy"}', "export STRIPE_SECRET_KEY=thisisnotreal99"]
        for c in cases:
            out = jev_client.redact(c)
            self.assertIn("[REDACTED]", out, c)
            for frag in ("supersecretvalue1", "abcd1234efgh", "hunter2hunter2", "zzzz9999yyyy", "thisisnotreal99"):
                self.assertNotIn(frag, out)

    def test_plain_text_untouched(self):
        t = "Build a React landing page. Skills: /frontend, /tailwind. Tiếng Việt ok. sk-short"
        self.assertEqual(jev_client.redact(t), t)

    def test_prepare_state_dict_and_cap(self):
        out = jev_client.prepare_state({"a": "x" * 9000, "vi": "Việt"})
        self.assertEqual(len(out), jev_client.STATE_CAP)
        self.assertEqual(jev_client.STATE_CAP, 6000)
        self.assertIn("Việt", jev_client.prepare_state({"vi": "Việt"}))

    def test_cap_applies_after_redaction_no_partial_secret(self):
        secret = _samples()["sk-ant"]
        out = jev_client.prepare_state("a" * 5990 + secret + "tail")
        self.assertEqual(len(out), 6000)
        self.assertNotIn("sk-" + "ant", out)
        self.assertNotIn(secret[:12], out)

    def test_prepare_state_scrubs_loaded_key_literal(self):
        with jev_stub.jev_test_env(stub=False):
            out = jev_client.prepare_state("hello %s world" % BOGUS)
        self.assertNotIn(BOGUS, out)
        self.assertIn("[REDACTED]", out)


class ImportAndConfigTests(unittest.TestCase):
    def test_import_has_no_side_effects(self):
        home = tempfile.mkdtemp(prefix="jev-home-")
        env = dict(os.environ, HOME=home, PYTHONDONTWRITEBYTECODE="1")
        for k in ("JEV_ENV_FILE", "SKILL_ROUTE_STATE_DIR", "JEV_USAGE_LOG", "JEV_NOTIFY_LOG"):
            env.pop(k, None)
        code = "import sys; sys.path.insert(0, %r); import jev_client" % os.path.dirname(HERE)
        r = subprocess.run([sys.executable, "-c", code], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.listdir(home), [])

    def test_load_config_never_returns_key(self):
        with jev_stub.jev_test_env() as env:
            cfg = jev_client.load_config()
            self.assertEqual(sorted(cfg), ["endpoint", "env_file", "has_key", "model"])
            self.assertTrue(cfg["has_key"])
            self.assertNotIn(BOGUS, json.dumps(cfg))
            self.assertEqual(cfg["endpoint"], env.stub.url)
            self.assertEqual(cfg["model"], "jev-stub")  # from the env file

    def test_env_overrides_file_for_model_and_no_key(self):
        with jev_stub.jev_test_env(stub=False, extra_env={"JEV_MODEL": "jev-override"}) as env:
            self.assertEqual(jev_client.load_config()["model"], "jev-override")
            env.write_env_file(key="")
            self.assertFalse(jev_client.load_config()["has_key"])

    def test_constants(self):
        self.assertEqual(jev_client.JEV_USD_PER_M_INPUT, 0.042)
        self.assertEqual(jev_client.DEFAULT_TIMEOUT, 2.0)
        self.assertEqual(jev_client.HAIKU_TIMEOUT, 60)
        self.assertIn("score", jev_client.SCORE_SHAPE_NOTE)
        self.assertNotIn("pending", jev_client.SCORE_SHAPE_NOTE)


# --------------------------------------------------------------------------- happy path + secrecy
class JevOkTests(EnvCase):
    def test_ok_shape_and_request_body(self):
        self.stub.winners = {"domain": "backend"}
        res = self.ask("build an API")
        self.assertEqual(res["router"], "jev")
        self.assertEqual(res["model"], "jev-stub")
        self.assertIsNone(res["jev_error"])
        self.assertEqual(self.stub.count, 1)
        a = res["answers"]["domain"]
        self.assertEqual(a["choice"], "backend")
        self.assertEqual(sorted(a["probabilities"]), sorted(QUESTIONS["domain"]["criteria"]))
        self.assertAlmostEqual(sum(a["probabilities"].values()), 1.0, places=6)
        body = self.stub.last_body
        self.assertEqual(body["model"], "jev-stub")
        self.assertEqual(body["state"], "build an API")
        self.assertEqual(body["questions"], QUESTIONS)
        self.assertEqual(self.stub.last_auth, "Bearer " + BOGUS)
        self.assertEqual(res["usage"]["input_tokens"], self.env.usage_records()[0]["input_tokens"])
        self.assertAlmostEqual(res["usd"], res["usage"]["input_tokens"] * 0.042 / 1e6, places=12)

    def test_choice_probabilities_always_contain_every_key(self):
        raw = {"domain": {"type": "choice", "choice": "backend", "probabilities": {"backend": 1.0}},
               "complexity": {"type": "score", "score": 1.0, "probabilities": {"1": 1.0}}}
        out = jev_client._normalize_answers(raw, QUESTIONS)
        self.assertEqual(out["domain"]["probabilities"],
                         {"frontend-ui": 0.0, "backend": 1.0, "writing-en": 0.0})
        # choice missing but probabilities present -> argmax
        out = jev_client._normalize_answers({"domain": {"probabilities": {"writing-en": 0.9}},
                                             "complexity": raw["complexity"]}, QUESTIONS)
        self.assertEqual(out["domain"]["choice"], "writing-en")

    def test_unanswered_or_invalid_choice_is_outage_garbage(self):
        for bad in ({"domain": {"type": "choice", "choice": "not-a-key", "probabilities": {}}},
                    {}):
            with self.subTest(bad=bad):
                class Partial(jev_stub.JevStub):
                    def _build_ok(inner, body):
                        d = jev_stub.JevStub._build_ok(inner, body)
                        d["answers"].pop("complexity")
                        d["answers"].update(bad)
                        return d
                p = Partial().start()
                try:
                    os.environ["JEV_ENDPOINT"] = p.url
                    res = self.ask()
                finally:
                    p.stop()
                self.assertEqual(res["router"], "haiku")
                self.assertEqual(res["jev_error"]["class"], "outage")
                self.assertEqual(res["jev_error"]["reason"], "garbage_body")
                self.env.flag_exists() and os.remove(self.env.flag)

    def test_state_secrets_redacted_before_send(self):
        secret = _samples()["ghp"]
        self.ask("deploy with %s and OPENAI_API_KEY=abcdef123456 ok" % secret)
        raw = self.stub.last_raw
        self.assertNotIn(secret, raw)
        self.assertNotIn("abcdef123456", raw)
        self.assertIn("[REDACTED]", raw)

    def test_state_cap_on_the_wire(self):
        self.ask("y" * 20000)
        self.assertEqual(len(self.stub.last_body["state"]), 6000)
        self.ask({"k": ["z" * 20000]})
        self.assertEqual(len(self.stub.last_body["state"]), 6000)

    def test_bogus_key_never_leaks_anywhere(self):
        out, err = io.StringIO(), io.StringIO()
        collected = []
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            # state carries the key literal; run success, every outage mode, and double failure
            self.ask("my key is %s ok" % BOGUS)
            for mode in ("401", "403", "429", "500", "529", "garbage", "422"):
                self.stub.set_mode(mode)
                self.ask("my key is %s ok" % BOGUS)
            jev_stub.set_fake_behavior(self.env.fake_claude, "always_malformed")
            for allow in (True, False):
                try:
                    self.ask("key %s" % BOGUS, allow_jev=allow)
                except jev_client.RouterUnavailable as e:
                    collected.append(str(e))
                    collected.append(repr(e))
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")
        self.assertTrue(collected)
        blobs = collected + [json.dumps(self.env.usage_records()), "\n".join(self.env.notify_lines()),
                             json.dumps(jev_stub.fake_claude_records(self.env.fake_claude)),
                             json.dumps(self.env.flag_info())]
        for blob in blobs:
            self.assertNotIn(BOGUS, blob)
        for r in self.stub.requests:  # only the Authorization header may carry it
            self.assertNotIn(BOGUS, r["body"])
        self.assertNotIn(BOGUS, json.dumps(jev_client.load_config()))
        self.assertTrue(jev_stub.fake_claude_records(self.env.fake_claude))

    def test_no_key_is_outage_without_request(self):
        self.env.write_env_file(key="")
        res = self.ask()
        self.assertEqual(self.stub.count, 0)
        self.assertEqual(res["router"], "haiku")
        self.assertEqual(res["jev_error"]["reason"], "no_key")
        self.assertTrue(self.env.flag_exists())

    def test_nonloopback_http_endpoint_refused_without_network(self):
        os.environ["JEV_ENDPOINT"] = "http://jev.example.invalid/v1/systemone"
        res = self.ask()
        self.assertEqual(res["router"], "haiku")
        self.assertEqual(res["jev_error"]["class"], "bad_request")
        self.assertEqual(res["jev_error"]["reason"], "endpoint_scheme")
        self.assertFalse(self.env.flag_exists())

    def test_redirect_not_followed(self):
        self.stub.set_mode("302")
        res = self.ask()
        self.assertEqual(res["router"], "haiku")
        self.assertEqual(res["jev_error"]["class"], "outage")
        self.assertEqual(self.stub.count, 1)


# --------------------------------------------------------------------------- outage state machine
OUTAGE_CASES = [
    ("401", {"status": 401, "reason": "http_401"}),
    ("403", {"status": 403, "reason": "http_403"}),
    ("429", {"status": 429, "reason": "http_429"}),
    ("500", {"status": 500, "reason": "http_500"}),
    ("529", {"status": 529, "reason": "http_529"}),
    ("garbage", {"status": 200, "reason": "garbage_body"}),
    ("badshape", {"status": 200, "reason": "garbage_body"}),
    ("slow", {"status": None, "reason": "timeout"}),
    ("refused", {"status": None, "reason": "connection_error"}),
]


class OutageTests(EnvCase):
    def _trigger(self, mode):
        if mode == "refused":
            os.environ["JEV_ENDPOINT"] = "http://127.0.0.1:%d/v1/systemone" % jev_stub.free_port()
            return self.ask(timeout=2.0)
        self.stub.set_mode(mode)
        self.stub.slow_seconds = 1.5
        return self.ask(timeout=0.4 if mode == "slow" else 2.0)

    def test_each_outage_class_falls_back_flags_and_alerts_once(self):
        for mode, expect in OUTAGE_CASES:
            with self.subTest(mode=mode):
                self.setUp_clean()
                res = self._trigger(mode)
                self.assertEqual(res["router"], "haiku", mode)
                self.assertEqual(res["jev_error"]["class"], "outage")
                self.assertEqual(res["jev_error"]["status"], expect["status"])
                self.assertEqual(res["jev_error"]["reason"], expect["reason"])
                self.assertEqual(res["answers"]["domain"]["choice"], "frontend-ui")  # fake claude's answer
                info = self.env.flag_info()
                self.assertEqual(info["failures"], 1)
                self.assertEqual(info["reason"], expect["reason"])
                for k in ("since", "last_failure"):
                    self.assertRegex(info[k], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
                self.assertTrue(jev_client.is_down())
                self.assertEqual(jev_client.down_info()["failures"], 1)
                self.assertEqual(len(self.env.notify_lines()), 1)
                self.assertEqual(len(self.env.notify_lines("down")), 1)
                # 2nd outage: failures 2, NO new notify line
                res2 = self._trigger(mode)
                self.assertEqual(res2["router"], "haiku")
                self.assertEqual(self.env.flag_info()["failures"], 2)
                self.assertEqual(len(self.env.notify_lines()), 1)

    def setUp_clean(self):
        """Reset flag/logs/stub between subTests of one test method."""
        for p in (self.env.flag, self.env.notify_log, self.env.usage_log):
            try:
                os.remove(p)
            except OSError:
                pass
        os.environ["JEV_ENDPOINT"] = self.stub.url
        self.stub.set_mode("ok")
        self.stub.reset()

    def test_bad_request_falls_back_without_flag_or_alert(self):
        for status in ("400", "422", "404"):
            with self.subTest(status=status):
                self.setUp_clean()
                self.stub.set_mode(status)
                res = self.ask()
                self.assertEqual(res["router"], "haiku")
                self.assertEqual(res["jev_error"], {"class": "bad_request", "status": int(status),
                                                    "reason": "http_" + status})
                self.assertFalse(self.env.flag_exists())
                self.assertEqual(self.env.notify_lines(), [])

    def test_bad_request_does_not_touch_existing_flag(self):
        self.stub.set_mode("500")
        self.ask()
        with open(self.env.flag) as fh:
            before = fh.read()
        self.stub.set_mode("422")
        self.ask()
        with open(self.env.flag) as fh:
            self.assertEqual(fh.read(), before)
        self.assertEqual(len(self.env.notify_lines()), 1)

    def test_recovery_removes_flag_and_alerts_once(self):
        self.stub.set_mode("500")
        self.ask()
        self.ask()
        self.assertEqual(self.env.flag_info()["failures"], 2)
        self.stub.set_mode("ok")
        res = self.ask()
        self.assertEqual(res["router"], "jev")
        self.assertFalse(self.env.flag_exists())
        self.assertEqual(self.env.notify_lines("up").__len__(), 1)
        self.assertEqual([l.split("\t")[1] for l in self.env.notify_lines()], ["down", "up"])
        self.ask()  # another success: no new alert
        self.assertEqual(len(self.env.notify_lines("up")), 1)
        leftovers = [f for f in os.listdir(self.env.state_dir)]
        self.assertEqual(leftovers, [])  # no .recover.* temp files left behind

    def test_success_without_flag_sends_no_alert(self):
        self.ask()
        self.assertEqual(self.env.notify_lines(), [])

    def test_down_then_haiku_failure_still_flags(self):
        jev_stub.set_fake_behavior(self.env.fake_claude, "exit_nonzero")
        self.stub.set_mode("500")
        with self.assertRaises(jev_client.RouterUnavailable):
            self.ask()
        self.assertTrue(self.env.flag_exists())
        self.assertEqual(len(self.env.notify_lines("down")), 1)


WORKER = r'''
import json, sys, time
sys.path.insert(0, sys.argv[1])
import jev_client
t = float(sys.argv[2])
while time.time() < t:
    pass
try:
    r = jev_client.ask("state", json.loads(sys.argv[3]), "skill-route")
    print(json.dumps({"router": r["router"]}))
except jev_client.RouterUnavailable:
    print(json.dumps({"router": "unavailable"}))
'''


class ConcurrencyTests(EnvCase):
    N = 10

    def _burst(self):
        start = time.time() + 2.0
        procs = [subprocess.Popen(
            [sys.executable, "-c", WORKER, os.path.dirname(HERE), repr(start), json.dumps(QUESTIONS)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ)) for _ in range(self.N)]
        routers = []
        for p in procs:
            out, err = p.communicate(timeout=90)
            self.assertEqual(p.returncode, 0, err)
            routers.append(json.loads(out.decode())["router"])
        return routers

    def test_concurrent_outage_exactly_one_down_alert(self):
        self.stub.set_mode("500")
        routers = self._burst()
        self.assertEqual(routers, ["haiku"] * self.N)
        self.assertEqual(self.stub.count, self.N)
        self.assertEqual(len(self.env.notify_lines("down")), 1)
        self.assertEqual(len(self.env.notify_lines()), 1)
        info = self.env.flag_info()
        self.assertIsNotNone(info)  # flag is valid JSON (no torn write)
        self.assertEqual(info["failures"], self.N)

    def test_concurrent_recovery_exactly_one_up_alert(self):
        self.stub.set_mode("500")
        self.ask()
        self.ask()
        self.assertEqual(len(self.env.notify_lines("down")), 1)
        self.stub.set_mode("ok")
        routers = self._burst()
        self.assertEqual(routers, ["jev"] * self.N)
        self.assertEqual(len(self.env.notify_lines("up")), 1)
        self.assertEqual(len(self.env.notify_lines("down")), 1)
        self.assertFalse(self.env.flag_exists())
        self.assertEqual(os.listdir(self.env.state_dir), [])

    def test_mixed_outage_and_recovery_flag_stays_consistent(self):
        # flapping endpoint: alerts are paired down/up, never two downs in a row without an up
        self.stub.set_mode("500")
        self.ask()
        self.stub.set_mode("ok")
        self.ask()
        self.stub.set_mode("500")
        self.ask()
        kinds = [l.split("\t")[1] for l in self.env.notify_lines()]
        self.assertEqual(kinds, ["down", "up", "down"])


# --------------------------------------------------------------------------- allow_jev / haiku / recursion
class HaikuTests(EnvCase):
    def test_allow_jev_false_makes_zero_requests(self):
        res = self.ask(allow_jev=False)
        self.assertEqual(self.stub.count, 0)
        self.assertEqual(res["router"], "haiku")
        self.assertIsNone(res["jev_error"])
        self.assertEqual(res["model"], "claude-haiku-fake")
        self.assertFalse(self.env.flag_exists())
        self.assertEqual(self.env.notify_lines(), [])
        recs = self.env.usage_records()
        self.assertEqual([r["router"] for r in recs], ["haiku"])
        self.assertEqual(recs[0]["input_tokens"], 400)

    def test_haiku_answers_follow_pinned_shape(self):
        res = self.ask(allow_jev=False)
        d = res["answers"]["domain"]
        self.assertEqual(d["type"], "choice")
        self.assertEqual(sorted(d["probabilities"]), sorted(QUESTIONS["domain"]["criteria"]))
        self.assertAlmostEqual(sum(d["probabilities"].values()), 1.0, places=6)
        s = res["answers"]["complexity"]
        self.assertEqual(s["type"], "score")
        self.assertEqual(s["score"], 2)
        self.assertAlmostEqual(jev_client.score01(s, 5), 0.5, places=6)

    def test_malformed_then_valid_is_repaired_once(self):
        jev_stub.set_fake_behavior(self.env.fake_claude, "malformed_then_valid")
        res = self.ask(allow_jev=False)
        self.assertEqual(res["router"], "haiku")
        recs = jev_stub.fake_claude_records(self.env.fake_claude)
        self.assertEqual(len(recs), 2)
        self.assertNotIn("previous reply was invalid", recs[0]["prompt"])
        self.assertIn("previous reply was invalid", recs[1]["prompt"])
        usage = self.env.usage_records()
        self.assertEqual([u["ok"] for u in usage], [False, True])
        self.assertEqual(res["usage"]["input_tokens"], 800)  # both attempts summed

    def test_always_malformed_raises_after_one_repair(self):
        jev_stub.set_fake_behavior(self.env.fake_claude, "always_malformed")
        with self.assertRaises(jev_client.RouterUnavailable):
            self.ask(allow_jev=False)
        self.assertEqual(len(jev_stub.fake_claude_records(self.env.fake_claude)), 2)

    def test_exit_nonzero_raises_no_retry(self):
        jev_stub.set_fake_behavior(self.env.fake_claude, "exit_nonzero")
        with self.assertRaises(jev_client.RouterUnavailable) as cm:
            self.ask(allow_jev=False)
        self.assertIn("haiku_exit_3", str(cm.exception))
        self.assertEqual(len(jev_stub.fake_claude_records(self.env.fake_claude)), 1)
        self.assertFalse(self.env.usage_records()[-1]["ok"])

    def test_missing_claude_binary_raises(self):
        os.environ["JEV_HAIKU_CMD"] = os.path.join(self.env.root, "no-such-claude")
        with self.assertRaises(jev_client.RouterUnavailable):
            self.ask(allow_jev=False)

    def test_code_fenced_json_is_tolerated(self):
        obj = jev_client._extract_json_object("```json\n{\"a\": 1}\n```")
        self.assertEqual(obj, {"a": 1})
        self.assertEqual(jev_client._extract_json_object("noise {\"a\": 2} tail"), {"a": 2})
        with self.assertRaises(Exception):
            jev_client._extract_json_object("no json here")


class ChildEnvTests(EnvCase):
    extra_env = {"CLAUDE_CODE_PLUGIN_DIRS": "/tmp/some-mods", "ANTHROPIC_API_KEY": "not-a-real-key-value",
                 "CLAUDECODE": "1"}

    def test_child_env_and_argv(self):
        self.ask("hello state", allow_jev=False)
        rec = jev_stub.fake_claude_records(self.env.fake_claude)[0]
        self.assertEqual(rec["skill_route_child"], "1")
        self.assertIsNone(rec["plugin_dirs"])          # mods must not load in the child
        self.assertFalse(rec["anthropic_key_set"])     # subscription only, never a billed key
        self.assertEqual(rec["max_thinking_tokens"], "0")  # no thinking tokens in the router child
        argv = rec["argv"]
        for flag in ("-p", "--model", "claude-haiku-5-5", "--output-format", "json", "--no-session-persistence",
                     "--setting-sources", "--strict-mcp-config", "--tools", "--disable-slash-commands",
                     "--system-prompt"):
            self.assertIn(flag, argv)
        self.assertNotIn("--bare", argv)
        self.assertEqual(argv[argv.index("--model") + 1], "claude-haiku-5-5")  # full ID: the alias resolved to 4.5 on some paths
        self.assertNotIn(BOGUS, json.dumps(argv))
        self.assertIn("hello state", rec["prompt"])
        # the parent process env is untouched
        self.assertEqual(os.environ.get("CLAUDE_CODE_PLUGIN_DIRS"), "/tmp/some-mods")
        self.assertIsNone(os.environ.get("SKILL_ROUTE_CHILD"))


class RecursionGuardTests(EnvCase):
    extra_env = {"SKILL_ROUTE_CHILD": "1"}

    def test_child_never_spawns_claude(self):
        with self.assertRaises(jev_client.RouterUnavailable):
            self.ask(allow_jev=False)
        self.stub.set_mode("500")
        with self.assertRaises(jev_client.RouterUnavailable):
            self.ask()
        self.assertEqual(jev_stub.fake_claude_records(self.env.fake_claude), [])
        self.assertEqual(self.stub.count, 1)  # only the allow_jev=True call reached Jev
        self.assertTrue(self.env.flag_exists())  # the outage is still recorded

    def test_child_can_still_use_jev(self):
        res = self.ask()
        self.assertEqual(res["router"], "jev")
        self.assertEqual(jev_stub.fake_claude_records(self.env.fake_claude), [])


# --------------------------------------------------------------------------- usage log
class UsageLogTests(EnvCase):
    KEYS = ["ts", "purpose", "router", "model", "input_tokens", "output_tokens", "usd", "latency_ms", "ok",
            "shadow"]

    def _check(self, rec):
        self.assertEqual(sorted(rec), sorted(self.KEYS))
        self.assertRegex(rec["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIn(rec["router"], ("jev", "haiku"))
        self.assertIsInstance(rec["model"], str)
        self.assertIsInstance(rec["input_tokens"], int)
        self.assertIsInstance(rec["output_tokens"], int)
        self.assertIsInstance(rec["usd"], float)
        self.assertIsInstance(rec["latency_ms"], int)
        self.assertIsInstance(rec["ok"], bool)
        self.assertIsInstance(rec["shadow"], bool)

    def test_schema_for_jev_failed_jev_and_haiku_lines(self):
        self.ask(shadow=True)
        self.stub.set_mode("500")
        self.ask(purpose="spawn-plan")
        self.ask(allow_jev=False)
        recs = self.env.usage_records()
        self.assertEqual(len(recs), 4)  # jev ok, jev fail, haiku (after fail), haiku
        for r in recs:
            self._check(r)
        ok, fail, h1, h2 = recs
        self.assertEqual((ok["router"], ok["ok"], ok["shadow"], ok["purpose"]), ("jev", True, True, "skill-route"))
        self.assertGreater(ok["input_tokens"], 0)
        self.assertAlmostEqual(ok["usd"], ok["input_tokens"] * 0.042 / 1e6, places=8)
        self.assertEqual((fail["router"], fail["ok"], fail["input_tokens"], fail["usd"], fail["purpose"]),
                         ("jev", False, 0, 0.0, "spawn-plan"))
        self.assertEqual((h1["router"], h1["ok"], h1["shadow"]), ("haiku", True, False))
        self.assertEqual(h2["purpose"], "skill-route")

    def test_purpose_passed_through_without_override(self):
        self.ask(purpose="spawn-plan")
        self.assertEqual(self.env.usage_records()[0]["purpose"], "spawn-plan")


class PurposeOverrideTests(EnvCase):
    extra_env = {"JEV_PURPOSE": "drill"}

    def test_env_overrides_purpose_on_every_line(self):
        self.ask(purpose="skill-route")
        self.stub.set_mode("500")
        self.ask(purpose="spawn-plan")
        recs = self.env.usage_records()
        self.assertEqual(len(recs), 3)
        self.assertEqual(set(r["purpose"] for r in recs), set(["drill"]))


# --------------------------------------------------------------------------- score01 / top_choices
class ScoreTests(unittest.TestCase):
    def live(self):
        with open(os.path.join(FIXTURES, "client-live-response-2026-10-07.json")) as fh:
            return json.load(fh)

    def test_real_live_score_shape(self):
        data = self.live()
        sc = data["answers"]["complexity"]
        self.assertIsInstance(sc["score"], float)           # a float level INDEX, not text
        self.assertEqual(sorted(sc["legend"]), ["0", "1", "2", "3", "4"])
        out = jev_client._normalize_answers(data["answers"], QUESTIONS)
        got = jev_client.score01(out["complexity"], 5)
        self.assertAlmostEqual(got, (1 * 0.01 + 2 * 0.99) / 1.0 / 4, places=6)
        self.assertGreater(got, 0.49)
        self.assertLess(got, 0.51)
        # keeps the live extras
        self.assertEqual(out["complexity"]["legend"]["2"], "medium multi-file change")
        self.assertEqual(out["complexity"]["score"], 2.0)

    def test_score01_variants(self):
        f = jev_client.score01
        self.assertAlmostEqual(f({"probabilities": {"0": 0.5, "4": 0.5}}, 5), 0.5)
        self.assertAlmostEqual(f({"probabilities": {"4": 1.0}}, 5), 1.0)
        self.assertAlmostEqual(f({"probabilities": {"0": 1.0}}, 5), 0.0)
        self.assertAlmostEqual(f({"probabilities": {"0": 2.0, "1": 2.0}}, 5), 0.125)  # unnormalised ok
        self.assertAlmostEqual(f({"score": 4.0}, 5), 1.0)           # no probabilities -> score/(n-1)
        self.assertAlmostEqual(f({"score": 1}, 3), 0.5)
        self.assertAlmostEqual(f({"score": "3"}, 5), 0.75)
        self.assertEqual(f({"score": 99.0}, 5), 1.0)                # clamped
        self.assertEqual(f({"score": -3}, 5), 0.0)
        self.assertEqual(f({"score": "medium"}, 5), 0.0)            # level text without probs: unknown -> 0
        self.assertEqual(f({}, 5), 0.0)
        self.assertEqual(f(None, 5), 0.0)
        self.assertEqual(f({"score": True}, 5), 0.0)
        self.assertAlmostEqual(f({"score": 1}, 1), 1.0)             # n<2 treated as 2 levels
        self.assertAlmostEqual(f({"probabilities": {"0": 0.0, "1": 0.0}, "score": 1.0}, 3), 0.5)

    def test_score01_through_stub_all_shapes(self):
        for shape in ("float", "index", "text"):
            with self.subTest(shape=shape):
                with jev_stub.jev_test_env(score_shape=shape, score_level=3) as env:
                    res = jev_client.ask("s", QUESTIONS, "skill-route")
                    sc = res["answers"]["complexity"]
                    self.assertEqual(res["router"], "jev")
                    # stub: p(3)=0.6, others 0.1 -> expected level 2.5 -> 0.625
                    self.assertAlmostEqual(jev_client.score01(sc, 5), 0.625, places=6)

    def test_top_choices(self):
        ans = {"probabilities": {"a": 0.2, "b": 0.5, "c": 0.3}}
        self.assertEqual(jev_client.top_choices(ans), [("b", 0.5), ("c", 0.3), ("a", 0.2)])
        self.assertEqual(jev_client.top_choices(ans, 1), [("b", 0.5)])
        self.assertEqual(jev_client.top_choices(ans, 2), [("b", 0.5), ("c", 0.3)])
        self.assertEqual(jev_client.top_choices({"probabilities": {"y": 0.5, "x": 0.5}}),
                         [("x", 0.5), ("y", 0.5)])                 # ties -> key order
        self.assertEqual(jev_client.top_choices({"choice": "z"}), [("z", 1.0)])
        self.assertEqual(jev_client.top_choices({}), [])
        self.assertEqual(jev_client.top_choices(None), [])
        live = jev_client._normalize_answers(self.live()["answers"], QUESTIONS)
        self.assertEqual(jev_client.top_choices(live["domain"])[0], ("frontend-ui", 1.0))
        self.assertEqual(jev_client.top_choices(live["complexity"], 2)[0], ("2", 0.99))


if __name__ == "__main__":
    unittest.main()

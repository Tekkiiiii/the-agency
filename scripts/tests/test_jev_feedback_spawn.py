"""Tests for the spawn-record extension of scripts/jev-feedback.py. Temp dirs only; never touches a real install.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_feedback_spawn*' -v
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "jev-feedback.py")


def load():
    spec = importlib.util.spec_from_file_location("jev_feedback_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


jf = load()


def spawn_rec(**over):
    rec = {
        "ts": "2026-10-09T03:00:00Z", "project": "demo-project", "task_id": "route-1", "tool": "skill-route",
        "jev_verdict": "frontend", "router": "jev",
        "pd_review": "agree", "pd_reason": "", "outcome": None, "outcome_mismatch": None,
        "task_text": "build a landing page",
        "source": "spawn", "spawn_verdict": "accept", "verdict_raw": "accept", "verdict_source": "explicit",
        "gate": "post", "none_fired": False, "jev_skills": ["frontend"], "spawner_skills": ["frontend"],
        "subagent_type": "general-purpose", "parent_agent": "root", "role": "exec", "route_id": "route-1",
        "spawn_id": "sp-1", "consult": "post",
    }
    rec.update(over)
    return rec


def old_rec(**over):
    rec = {
        "ts": "2026-10-07T01:02:03Z", "project": "p", "task_id": "t1", "tool": "skill-route", "jev_verdict": "frontend",
        "router": "jev", "pd_review": "agree", "pd_reason": "",
        "outcome": None, "outcome_mismatch": None, "task_text": "do a thing",
    }
    rec.update(over)
    return rec


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jf-spawn-test-")
        self.fb = os.path.join(self.tmp, "jev-feedback.jsonl")
        self._old = os.environ.get("JEV_FEEDBACK_LOG")
        os.environ["JEV_FEEDBACK_LOG"] = self.fb

    def tearDown(self):
        if self._old is None:
            os.environ.pop("JEV_FEEDBACK_LOG", None)
        else:
            os.environ["JEV_FEEDBACK_LOG"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lines(self, path=None):
        path = path or self.fb
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(x) for x in f if x.strip()]

    def write(self, recs, path=None):
        with open(path or self.fb, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = jf.main(list(argv))
        return rc, out.getvalue(), err.getvalue()


class TestValidate(Base):
    def test_valid_spawn_record(self):
        self.assertEqual(jf.validate_record(spawn_rec()), [])

    def test_none_verdict_and_unreviewed(self):
        r = spawn_rec(jev_verdict="(none)", jev_skills=[], none_fired=True, pd_review="unreviewed",
                      spawn_verdict="unreviewed", verdict_source="auto_default")
        self.assertEqual(jf.validate_record(r), [])

    def test_disagree_without_reason_ok_for_spawn_only(self):
        self.assertEqual(jf.validate_record(spawn_rec(pd_review="disagree", spawn_verdict="modify", pd_reason="")), [])
        self.assertTrue(jf.validate_record(old_rec(tool="skill-route", jev_verdict="x", pd_review="disagree")))

    def test_enums_rejected(self):
        for k, v in (("spawn_verdict", "maybe"), ("verdict_source", "guess"), ("consult", "later"), ("source", "other")):
            errs = jf.validate_record(spawn_rec(**{k: v}))
            self.assertTrue(any(k in e for e in errs), (k, errs))

    def test_all_enum_values_accepted(self):
        for v in ("accept", "modify", "reject", "unreviewed"):
            self.assertEqual(jf.validate_record(spawn_rec(spawn_verdict=v)), [])
        for v in ("explicit", "auto_default", "auto_match", "auto_empty", "confidential_local", "inferred",
                  "jev_unavailable", "deny_cap"):
            self.assertEqual(jf.validate_record(spawn_rec(verdict_source=v)), [])
        for v in ("pre", "gate", "post"):
            self.assertEqual(jf.validate_record(spawn_rec(consult=v)), [])

    def test_type_errors(self):
        self.assertTrue(jf.validate_record(spawn_rec(jev_skills="frontend")))
        self.assertTrue(jf.validate_record(spawn_rec(spawner_skills=[1])))
        self.assertTrue(jf.validate_record(spawn_rec(none_fired="no")))
        self.assertTrue(jf.validate_record(spawn_rec(parent_agent=5)))
        self.assertEqual(jf.validate_record(spawn_rec(parent_agent=None, role=None)), [])

    def test_spawn_requires_skill_route_tool(self):
        self.assertTrue(jf.validate_record(spawn_rec(tool="spawn-plan", jev_verdict="ready")))   # any other tool

    def test_unknown_key_still_rejected(self):
        self.assertTrue(any("unknown key" in e for e in jf.validate_record(spawn_rec(bogus=1))))

    def test_old_records_unchanged(self):
        self.assertEqual(jf.validate_record(old_rec()), [])
        self.assertEqual(jf.validate_record(old_rec(correct_skills=["a"], sample=True)), [])
        self.assertTrue(jf.validate_record(old_rec(pd_review="bogus")))
        r = old_rec()
        del r["pd_reason"]
        self.assertTrue(jf.validate_record(r))


class TestAppend(Base):
    def test_append_writes_one_line_and_returns_empty(self):
        self.assertEqual(jf.append_spawn_record(spawn_rec()), [])
        got = self.lines()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["spawn_id"], "sp-1")

    def test_explicit_path_overrides_env(self):
        other = os.path.join(self.tmp, "sub", "other.jsonl")
        self.assertEqual(jf.append_spawn_record(spawn_rec(), path=other), [])
        self.assertEqual(len(self.lines(other)), 1)
        self.assertEqual(self.lines(), [])

    def test_defaults_source_and_ts(self):
        r = spawn_rec()
        del r["source"], r["ts"]
        self.assertEqual(jf.append_spawn_record(r), [])
        got = self.lines()[0]
        self.assertEqual(got["source"], "spawn")
        self.assertTrue(jf.TS_RE.match(got["ts"]))

    def test_secret_in_task_text_is_rejected_and_never_written(self):
        text = "deploy with TYPESAFE_API_KEY=abc123def456ghi789jkl and run the build"
        errs = jf.append_spawn_record(spawn_rec(task_text=text))
        self.assertTrue(any("secret" in e for e in errs), errs)
        self.assertEqual(self.lines(), [])

    def test_invalid_returns_errors_and_writes_nothing(self):
        errs = jf.append_spawn_record(spawn_rec(spawn_verdict="nope"))
        self.assertTrue(errs)
        self.assertEqual(self.lines(), [])

    def test_never_raises(self):
        self.assertTrue(jf.append_spawn_record(None))
        self.assertTrue(jf.append_spawn_record("x"))
        # parent of the target is a regular file -> makedirs/open fails -> error list, no exception
        blocker = os.path.join(self.tmp, "blocker")
        open(blocker, "w").close()
        errs = jf.append_spawn_record(spawn_rec(), path=os.path.join(blocker, "x", "f.jsonl"))
        self.assertTrue(errs and errs[0].startswith("error:"))

    def test_does_not_mutate_input(self):
        r = spawn_rec(task_text="hello")
        before = json.dumps(r, sort_keys=True)
        jf.append_spawn_record(r)
        self.assertEqual(json.dumps(r, sort_keys=True), before)

    def test_concurrent_appends_keep_every_record(self):
        def work(i):
            self.assertEqual(jf.append_spawn_record(spawn_rec(task_id="r%d" % i, spawn_id="s%d" % i)), [])
        ts = [threading.Thread(target=work, args=(i,)) for i in range(12)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sorted(r["task_id"] for r in self.lines()), sorted("r%d" % i for i in range(12)))

    def test_lock_file_created_next_to_log(self):
        jf.append_spawn_record(spawn_rec())
        self.assertTrue(os.path.exists(self.fb + ".lock"))


class TestMismatch(Base):
    def test_ok_is_false(self):
        self.assertEqual(jf.compute_mismatch(spawn_rec(), "ok"), (False, None))

    def test_wrong_skill_true_only_when_jev_pick_ran(self):
        self.assertEqual(jf.compute_mismatch(spawn_rec(jev_skills=["a", "b"], spawner_skills=["b", "a"]), "wrong_skill"),
                         (True, None))
        self.assertEqual(jf.compute_mismatch(spawn_rec(jev_skills=["a"], spawner_skills=["z"]), "wrong_skill"),
                         (False, None))
        self.assertEqual(jf.compute_mismatch(spawn_rec(jev_skills=["a"], spawner_skills=["a", "z"]), "wrong_skill"),
                         (False, None))

    def test_wrong_skill_false_when_jev_had_no_pick(self):
        self.assertEqual(jf.compute_mismatch(spawn_rec(jev_skills=[], spawner_skills=[]), "wrong_skill"), (False, None))

    def test_non_spawn_skill_route_unchanged(self):
        r = old_rec(jev_verdict="x")
        self.assertEqual(jf.compute_mismatch(r, "wrong_skill"), (True, None))
        self.assertEqual(jf.compute_mismatch(r, "ok"), (False, None))
        self.assertIsNotNone(jf.compute_mismatch(r, "nack")[1])

    def test_outcome_subcommand_on_spawn_record(self):
        self.write([spawn_rec(task_id="route-9", jev_skills=["a"], spawner_skills=["a"])])
        rc, out, err = self.cli("outcome", "route-9", "wrong_skill", "--correct-skills", "b,c")
        self.assertEqual(rc, 0, err)
        rec = self.lines()[0]
        self.assertEqual((rec["outcome"], rec["outcome_mismatch"], rec["correct_skills"]), ("wrong_skill", True, ["b", "c"]))
        self.assertEqual(jf.validate_record(rec), [])

    def test_outcome_ok_on_spawn_record(self):
        self.write([spawn_rec()])
        rc, _, err = self.cli("outcome", "route-1", "ok")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.lines()[0]["outcome_mismatch"], False)


class TestReconcile(Base):
    def setUp(self):
        Base.setUp(self)
        self.log_a = os.path.join(self.tmp, "a", "spawns.jsonl")
        self.log_b = os.path.join(self.tmp, "b", "spawns.jsonl")
        os.makedirs(os.path.dirname(self.log_a))
        os.makedirs(os.path.dirname(self.log_b))

    def end(self, sid, outcome="DONE", mism=False):
        return {"event": "spawn_end", "spawn_id": sid, "outcome": outcome, "skill_mismatch": mism}

    def test_reconcile_across_logs(self):
        self.write([
            spawn_rec(task_id="t-ok", spawn_id="s-ok"),
            spawn_rec(task_id="t-wrong", spawn_id="s-wrong"),
            spawn_rec(task_id="t-wrong-other", spawn_id="s-wrong2", jev_skills=["a"], spawner_skills=["z"]),
            spawn_rec(task_id="t-blocked", spawn_id="s-blocked"),
            spawn_rec(task_id="t-noend", spawn_id="s-noend"),
            spawn_rec(task_id="t-nosid", spawn_id=None),
            spawn_rec(task_id="t-done", spawn_id="s-done", outcome="ok", outcome_mismatch=False),
            spawn_rec(task_id="t-sample", spawn_id="s-ok", sample=True),
            old_rec(),
        ])
        with open(self.log_a, "w") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "s-ok"}) + "\n")
            f.write(json.dumps(self.end("s-ok")) + "\n")
            f.write(json.dumps(self.end("s-wrong", "DONE", True)) + "\n")
            f.write("not json {\n")
        with open(self.log_b, "w") as f:
            f.write(json.dumps(self.end("s-wrong2", "DONE", True)) + "\n")
            f.write(json.dumps(self.end("s-blocked", "BLOCKED")) + "\n")
        summary = jf.reconcile(self.fb, [self.log_a, self.log_b, os.path.join(self.tmp, "missing.jsonl")])
        self.assertEqual(summary, {"checked": 5, "updated_ok": 1, "updated_wrong_skill": 2})
        by = {r["task_id"]: r for r in self.lines()}
        self.assertEqual((by["t-ok"]["outcome"], by["t-ok"]["outcome_mismatch"]), ("ok", False))
        self.assertEqual((by["t-wrong"]["outcome"], by["t-wrong"]["outcome_mismatch"]), ("wrong_skill", True))
        self.assertEqual((by["t-wrong-other"]["outcome"], by["t-wrong-other"]["outcome_mismatch"]), ("wrong_skill", False))
        self.assertIsNone(by["t-blocked"]["outcome"])
        self.assertIsNone(by["t-noend"]["outcome"])
        self.assertIsNone(by["t-nosid"]["outcome"])
        self.assertIsNone(by["t-sample"]["outcome"])
        self.assertEqual((by["t-done"]["outcome"], by["t-done"]["outcome_mismatch"]), ("ok", False))
        self.assertIsNone(by["t1"]["outcome"])  # non-spawn record untouched
        for r in by.values():
            self.assertEqual(jf.validate_record(r), [])

    def test_reconcile_idempotent(self):
        self.write([spawn_rec(spawn_id="s1")])
        with open(self.log_a, "w") as f:
            f.write(json.dumps(self.end("s1")) + "\n")
        self.assertEqual(jf.reconcile(self.fb, [self.log_a])["updated_ok"], 1)
        self.assertEqual(jf.reconcile(self.fb, [self.log_a]), {"checked": 0, "updated_ok": 0, "updated_wrong_skill": 0})

    def test_missing_feedback_file_is_noop(self):
        self.assertEqual(jf.reconcile(self.fb, [self.log_a]), {"checked": 0, "updated_ok": 0, "updated_wrong_skill": 0})
        self.assertFalse(os.path.exists(self.fb))

    def test_cli_reconcile_prints_one_line_json(self):
        self.write([spawn_rec(spawn_id="s1")])
        with open(self.log_a, "w") as f:
            f.write(json.dumps(self.end("s1")) + "\n")
        rc, out, err = self.cli("reconcile", "--spawn-logs", self.log_a, self.log_b)
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out), {"checked": 1, "updated_ok": 1, "updated_wrong_skill": 0})
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_default_spawn_logs_parse_medium_term(self):
        home = tempfile.mkdtemp(prefix="jf-home-")
        try:
            os.makedirs(os.path.join(home, ".claude", "memory"))
            with open(os.path.join(home, ".claude", "memory", "medium-term.md"), "w") as f:
                f.write("## Active Projects\n| slug | path |\n|---|---|\n"
                        "| billing-app | `~/projects/billing-app` | pd |\n| si | `~/.claude/projects/demo-project/memory` | pd |\n")
            saved = dict((k, os.environ.get(k)) for k in ("HOME", "AGENCY_HOME", "CLAUDE_CONFIG_DIR"))
            os.environ["HOME"] = home
            os.environ["AGENCY_HOME"] = os.path.join(home, ".claude")
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
            try:
                logs = jf.default_spawn_logs()
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            self.assertEqual(logs[0], os.path.join(home, ".claude/logs/spawns.jsonl"))
            self.assertIn(os.path.join(home, "projects/billing-app/memory/spawns.jsonl"), logs)
            self.assertIn(os.path.join(home, ".claude/projects/demo-project/memory/spawns.jsonl"), logs)
        finally:
            shutil.rmtree(home, ignore_errors=True)


class TestSpawnStats(Base):
    def test_stats(self):
        self.write([
            spawn_rec(task_id="a", gate="pre", spawn_verdict="accept", verdict_source="explicit", parent_agent="root"),
            spawn_rec(task_id="b", gate="pre", spawn_verdict="modify", verdict_source="auto_match", parent_agent="coord",
                      outcome="wrong_skill", outcome_mismatch=True),
            spawn_rec(task_id="c", gate="post", spawn_verdict="accept", verdict_source="explicit", parent_agent="root",
                      outcome="ok", outcome_mismatch=False),
            spawn_rec(task_id="d", gate="post", spawn_verdict="unreviewed", pd_review="unreviewed",
                      verdict_source="auto_default", parent_agent="root"),
            spawn_rec(task_id="e", sample=True),
            old_rec(),
        ])
        rc, out, err = self.cli("spawn-stats")
        self.assertEqual(rc, 0, err)
        s = json.loads(out)
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["by_gate_spawn_verdict"], {"pre": {"accept": 1, "modify": 1},
                                                      "post": {"accept": 1, "unreviewed": 1}})
        self.assertEqual(s["by_verdict_source"], {"explicit": 2, "auto_match": 1, "auto_default": 1})
        self.assertEqual(s["by_parent_agent"], {"root": 3, "coord": 1})
        self.assertEqual(s["agreement_rate"], 0.5)
        self.assertEqual(s["agreement_rate_reviewed"], round(2 / 3.0, 4))
        self.assertEqual(s["agreement_rate_by_gate"], {"pre": 0.5, "post": 0.5})
        self.assertEqual(s["outcomes"], {"pending": 2, "wrong_skill": 1, "ok": 1})
        self.assertEqual(s["jev_mismatch_count"], 1)

    def test_stats_empty_or_missing_file(self):
        rc, out, _ = self.cli("spawn-stats")
        self.assertEqual(rc, 0)
        s = json.loads(out)
        self.assertEqual((s["total"], s["agreement_rate"], s["jev_mismatch_count"]), (0, None, 0))


class TestReaders(Base):
    """Existing readers keep working on a log that mixes old and spawn records."""

    def test_old_cli_add_still_works_and_rejects_unreviewed_flag(self):
        rc, _, err = self.cli("add", "--project", "p", "--task-id", "t", "--tool", "skill-route", "--verdict", "frontend",
                              "--router", "jev", "--review", "agree")
        self.assertEqual(rc, 0, err)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.cli("add", "--project", "p", "--task-id", "t2", "--tool", "skill-route", "--verdict", "frontend",
                         "--router", "jev", "--review", "unreviewed")


if __name__ == "__main__":
    unittest.main()

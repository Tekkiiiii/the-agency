"""Unit tests for the optional `verdicts` payload key in scripts/save-state.py.

Calls write_next_session() / write_session_log() directly (never main()) against
a temp project dir only: no metric emits, no overseer brief, no real project writes.

Run: python3 -m unittest discover -s scripts/tests -p 'test_save_state_verdicts*' -v
"""
import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "save-state.py")
DATE = "2026-10-23"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def payload(**extra):
    p = {"slug": "tmp-proj", "phase": "testing", "next": "run tests"}
    p.update(extra)
    return p


def V(i, q="Ship it?", rec="yes", door="two-way"):
    return {"id": i, "question": q, "rec": rec, "door": door}


class VerdictsTest(unittest.TestCase):
    def setUp(self):
        self.m = load(SCRIPT, "save_state_verdicts_under_test")
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="save-state-verdicts-"))
        (self.tmp / "memory").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ns(self, p, inbound=()):
        self.m.write_next_session(self.tmp, p, DATE, list(inbound))
        return (self.tmp / "memory/next-session.md").read_text()

    def ns_err(self, p):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = self.ns(p)
        return out, err.getvalue()

    # --- backward compat: no verdicts -> byte-identical legacy output
    def test_legacy_zero_blockers(self):
        self.assertEqual(self.ns(payload()), (
            "# tmp-proj\nPhase: testing\nNext: run tests\nBlockers: none\n"
            "Decisions: see decisions.md\nMid-flight: none\nDelegated: none\n"
            "Pending inbound: none\nLast saved: 2026-10-23\n"))

    def test_legacy_one_blocker(self):
        self.assertIn("Blockers: waiting on X\nDecisions:", self.ns(payload(blockers=["waiting on X"])))

    def test_legacy_two_blockers(self):
        self.assertIn("Blockers: \n  a\n  b\nDecisions:", self.ns(payload(blockers=["a", "b"])))

    def test_empty_verdicts_list_is_legacy(self):
        self.assertEqual(self.ns(payload(verdicts=[])), self.ns(payload()))

    # --- rendering
    def test_verdict_line_format_and_order(self):
        out = self.ns(payload(verdicts=[V("D1", "Q one?", "go", "one-way"), V("D2")], blockers=["free text"]))
        lines = out.splitlines()
        i = lines.index("Blockers:")
        self.assertEqual(lines[i + 1], "  Verdict: D1 | Q one? | rec: go | door: one-way")
        self.assertEqual(lines[i + 2], "  Verdict: D2 | Ship it? | rec: yes | door: two-way")
        self.assertEqual(lines[i + 3], "  free text")
        self.assertTrue(lines[i + 4].startswith("Decisions:"))

    def test_single_verdict_not_inline(self):
        out = self.ns(payload(verdicts=[V("D1")]))
        self.assertIn("\nBlockers:\n  Verdict: D1 |", out)

    def test_sanitize_and_truncate(self):
        q = "a|b\nc   d " + "x" * 300
        out = self.ns(payload(verdicts=[V("D|1", q, "r|\nec", "maybe")]))
        line = [l for l in out.splitlines() if "Verdict:" in l][0]
        body = line.strip()[len("Verdict: "):]
        self.assertEqual(len(body.split(" | ")), 4)
        self.assertEqual(len(out.splitlines()), 9 + 1)
        qpart = body.split(" | ")[1]
        self.assertTrue(qpart.startswith("a b c d "))
        self.assertTrue(qpart.endswith("…"))
        self.assertLessEqual(len(qpart), 120)
        self.assertIn("door: unknown", line)
        self.assertIn("rec: r ec", line)

    def test_missing_rec_omitted(self):
        for rec in (None, "", "  "):
            out = self.ns(payload(verdicts=[V("D1", rec=rec)]))
            self.assertIn("  Verdict: D1 | Ship it? | door: two-way\n", out)

    def test_missing_door_unknown(self):
        v = {"id": "D1", "question": "Q?"}
        self.assertIn("| door: unknown\n", self.ns(payload(verdicts=[v])))

    def test_invalid_entries_skipped_with_warning(self):
        bad = [{"question": "no id"}, {"id": "D9"}, "str", None, V("D1")]
        out, err = self.ns_err(payload(verdicts=bad))
        self.assertEqual(out.count("Verdict:"), 1)
        self.assertIn("D1", out)
        self.assertGreaterEqual(err.count("warning"), 4)

    def test_non_list_verdicts_ignored(self):
        out, err = self.ns_err(payload(verdicts="nope"))
        self.assertIn("Blockers: none", out)
        self.assertIn("warning", err)

    # --- hard cap / tail preserved
    def test_cap_15_and_tail_preserved_with_verdicts(self):
        p = payload(verdicts=[V(f"D{i}") for i in range(9)], blockers=["f1", "f2"])
        out = self.ns(p, inbound=["x.md — t"])
        lines = out.splitlines()
        self.assertEqual(len(lines), 15)
        self.assertEqual(lines[-1], "Last saved: 2026-10-23")
        self.assertTrue(lines[-2].startswith("Pending inbound: x.md"))
        self.assertEqual(lines[-6], "  (+6 more blockers — see session log)")
        self.assertEqual(sum("Verdict:" in l for l in lines), 5)

    def test_cap_exactly_six_fits(self):
        out = self.ns(payload(verdicts=[V(f"D{i}") for i in range(6)]))
        self.assertEqual(len(out.splitlines()), 15)
        self.assertNotIn("more blockers", out)

    def test_cap_legacy_many_free_blockers_keeps_tail(self):
        out = self.ns(payload(blockers=[f"b{i}" for i in range(10)]))
        lines = out.splitlines()
        self.assertEqual(len(lines), 15)
        self.assertEqual(lines[-1], "Last saved: 2026-10-23")
        self.assertIn("(+5 more blockers — see session log)", out)

    # --- session log carries everything untruncated
    def test_session_log_has_untruncated_verdicts(self):
        q = "q" * 300
        p = payload(verdicts=[V("D1", q)], blockers=["free"])
        self.m.write_session_log(self.tmp, p, DATE)
        log = (self.tmp / "memory/sessions" / f"{DATE}.md").read_text()
        self.assertIn(f"- Verdict: D1 | {q} | rec: yes | door: two-way", log)
        self.assertIn("- free", log)
        self.assertLess(log.index("Verdict: D1"), log.index("- free"))

    def test_session_log_verdict_only_has_blockers_section(self):
        self.m.write_session_log(self.tmp, payload(verdicts=[V("D1")]), DATE)
        log = (self.tmp / "memory/sessions" / f"{DATE}.md").read_text()
        self.assertIn("### Blockers\n- Verdict: D1", log)


if __name__ == "__main__":
    unittest.main()

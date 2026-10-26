"""Pins what spawn_end `outcome` UNKNOWN and `continuation` MEAN (real Windows ledger, 2026-10-13: 38 UNKNOWN ends, 59 continuations).

Verdict (see ledger.py module docstring, "OUTCOME / CONTINUATION"): UNKNOWN is the default of a plain substring scan of
the agent's final message for DONE / COMPLETE / BLOCKED / ESCALATE / KILLED tokens. It means "no such token", not a parse
failure. The scan is line-ending and code-page independent for every ASCII token; only the em-dash forms ("— BLOCKED",
"— ESCALATE") need the text to arrive as real UTF-8 (tests/test_utf8_roundtrip.py covers that path).
`continuation: true` = a SECOND (or later) stop of the same agent_id (resumed via SendMessage); its outcome is judged on
that turn's own last message, so a short acknowledgement is UNKNOWN too.
Synthetic text only. Temp log via SPAWN_LOG_FILE; nothing touches a real ledger.
Run: python3 -m unittest discover -s <repo>/mods/spawn-ledger/tests -v"""
import importlib.util
import json
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ledger_outcome", os.path.join(HERE, "..", "bin", "ledger.py"))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class DetectOutcome(unittest.TestCase):
    def test_no_token_is_unknown(self):
        for text in ("", None, "Acknowledged. Standing by.", "Đã xong phần việc, chờ bước tiếp theo.", "ok\r\nnext"):
            self.assertEqual(ledger.detect_outcome(text), "UNKNOWN", repr(text))

    def test_ascii_tokens_ignore_line_endings(self):
        for crlf, want in (("Result:\r\nDONE\r\n", "DONE"), ("x\r\nBLOCKED: no access\r\n", "BLOCKED"),
                           ("x\r\nESCALATE: need Dev\r\n", "ESCALATE"), ("x\r\n\r\nall tasks COMPLETE\r\n", "DONE"),
                           ("Status: BLOCKED\r\n", "BLOCKED")):
            self.assertEqual(ledger.detect_outcome(crlf), want, repr(crlf))
            self.assertEqual(ledger.detect_outcome(crlf.replace("\r\n", "\n")), want)

    def test_cp1252_roundtrip_keeps_ascii_tokens_but_loses_the_em_dash_form(self):
        """A summary decoded with the wrong code page (the pre-e5a3d7d Windows state) still finds ASCII tokens;
        the em-dash forms only match as real UTF-8, which is why the UTF-8 stdio/transcript fixes matter."""
        good = "Hoàn tất — BLOCKED"
        garbled = good.encode("utf-8").decode("cp1252", errors="replace")
        self.assertEqual(ledger.detect_outcome(good), "BLOCKED")
        self.assertEqual(ledger.detect_outcome(garbled), "UNKNOWN")
        self.assertEqual(ledger.detect_outcome("Hoàn tất. DONE".encode("utf-8").decode("cp1252", errors="replace")), "DONE")
        self.assertEqual(ledger.detect_outcome("lỗi: BLOCKED: thiếu quyền".encode("utf-8").decode("cp1252", errors="replace")), "BLOCKED")

    def test_precedence_killed_blocked_escalate_done(self):
        self.assertEqual(ledger.detect_outcome("DONE but KILLED by user"), "KILLED")
        self.assertEqual(ledger.detect_outcome("BLOCKED: x. ESCALATE: y. DONE"), "BLOCKED")
        self.assertEqual(ledger.detect_outcome("ESCALATE: y. DONE"), "ESCALATE")


class Continuation(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.log = os.path.join(tmp, "spawns.jsonl")
        with open(self.log, "w", encoding="utf-8") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "sid-1", "tool_use_id": "tu-1"}) + "\n")
            f.write(json.dumps({"event": "spawn_launched", "spawn_id": "sid-1", "tool_use_id": "tu-1", "agent_id": "a1"}) + "\n")
        for p in (mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": self.log}),
                  mock.patch.object(ledger, "reconcile", lambda lf: None)):
            p.start()
            self.addCleanup(p.stop)

    def end_rows(self):
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(l) for l in f if '"spawn_end"' in l]

    def test_second_stop_of_the_same_agent_is_continuation_and_judged_on_its_own_message(self):
        ledger.end({"agent_id": "a1", "agent_type": "general-purpose", "last_assistant_message": "Report\r\nDONE\r\n"})
        ledger.end({"agent_id": "a1", "agent_type": "general-purpose", "last_assistant_message": "Đã nhận, tiếp tục."})
        first, second = self.end_rows()
        self.assertEqual((first["outcome"], first.get("continuation")), ("DONE", None))
        self.assertEqual((second["outcome"], second.get("continuation")), ("UNKNOWN", True))
        self.assertEqual(second["summary_excerpt"], "Đã nhận, tiếp tục.")


if __name__ == "__main__":
    unittest.main()

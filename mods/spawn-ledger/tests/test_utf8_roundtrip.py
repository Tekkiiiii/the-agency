"""End-to-end UTF-8 round trip through the real hook entry (`python ledger.py <cmd>` with the hook JSON on stdin).

Why: a real Windows ledger (written before e5a3d7d, 2026-10-12/13) held rows with an em dash stored as mojibake
(UTF-8 bytes decoded as cp1252). Node writes UTF-8 JSON to the python child; Windows python decodes its stdin and
opens files with the ANSI code page unless told otherwise. This drives the production entry the way register.ts does
(stdin bytes = UTF-8 JSON, ensure_ascii=False like JSON.stringify) with every UTF-8 switch OFF
(PYTHONIOENCODING unset, PYTHONUTF8=0) and, off Windows, an ASCII C locale so the process default is genuinely not
UTF-8 (on windows-latest the default is cp1252 already). Then it reads spawns.jsonl as BYTES and requires the stored
strings to equal what was sent.

Covered paths: stdin decode (start: description, prompt_excerpt; end: last_assistant_message), the transcript read
(end: SubagentHandback text -> summary_excerpt and the outcome token "— BLOCKED"), and the file write.
Synthetic text only. Isolation: HOME/USERPROFILE and SPAWN_LOG_FILE are in a temp dir; nothing touches a real log.
Run: python3 -m unittest discover -s <repo>/mods/spawn-ledger/tests -v"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_PY = os.path.join(HERE, "..", "bin", "ledger.py")

DASH_VI = "Kiểm tra — tiếng Việt"          # em dash + Vietnamese (precomposed)
PROMPT = "Skills: /frontend\n" + DASH_VI + " — Đường dẫn: Hà Nội, Thành phố Hồ Chí Minh ệ ữ ơ"
DESC = DASH_VI + " (mô tả)"
HANDBACK = "Báo cáo xong — BLOCKED"          # only the "— BLOCKED" outcome pattern can match this


def hostile_env(tmp):
    """Process env with every UTF-8 switch off. PYTHONUTF8=0 (not just unset) so a CI runner exporting it cannot hide
    the bug; the ASCII locale makes open()/stdio default non-UTF-8 on POSIX where cp1252 is not the default."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO")}
    env.update(HOME=tmp, USERPROFILE=tmp, SPAWN_LOG_FILE=os.path.join(tmp, "spawns.jsonl"),
               SPAWN_LEDGER_METRICS_FILE=os.path.join(tmp, "events.jsonl"), SKILL_ROUTE_CHILD="1",
               SPAWN_LEDGER_TEST="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="0")
    if os.name != "nt":
        env.update(LC_ALL="C", LANG="C", PYTHONCOERCECLOCALE="0")
    return env


class Utf8RoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "spawns.jsonl")
        self.env = hostile_env(self.tmp)

    def run_ledger(self, cmd, payload):
        r = subprocess.run([sys.executable, LEDGER_PY, cmd],
                           input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                           env=self.env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def rows(self):
        with open(self.log, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")  # must be valid UTF-8
        self.assertNotIn("â€", text, "mojibake in the ledger bytes")
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def test_start_row_round_trips_em_dash_and_vietnamese(self):
        self.run_ledger("start", {"tool_use_id": "tu-1", "subagent_type": "general-purpose",
                                  "description": DESC, "prompt": PROMPT, "model": "sonnet"})
        (row,) = self.rows()
        self.assertEqual(row["event"], "spawn_start")
        self.assertEqual(row["description"], DESC)
        self.assertEqual(row["prompt_excerpt"], PROMPT[:200])

    def test_end_row_round_trips_stdin_summary(self):
        self.run_ledger("end", {"agent_id": "a1", "agent_type": "general-purpose",
                                "last_assistant_message": HANDBACK + " " + DASH_VI})
        (row,) = self.rows()
        self.assertEqual(row["event"], "spawn_end")
        self.assertEqual(row["summary_excerpt"], HANDBACK + " " + DASH_VI)
        self.assertEqual(row["outcome"], "BLOCKED")

    def test_end_row_reads_the_utf8_transcript_as_utf8(self):
        """The handback text comes from the transcript file (claude_pricing.usage_from_transcript), not stdin."""
        transcript = os.path.join(self.tmp, "t.jsonl")
        line = {"type": "assistant", "timestamp": "2026-10-13T10:00:00Z",
                "message": {"id": "m1", "model": "claude-sonnet-5-5", "usage": {"input_tokens": 1, "output_tokens": 1},
                            "content": [{"type": "tool_use", "name": "SubagentHandback", "input": {"message": HANDBACK}}]}}
        early = {"type": "user", "timestamp": "2026-10-13T09:58:00Z", "message": {"content": "go"}}  # >5s span: not a silent no-op
        with open(transcript, "wb") as f:  # raw UTF-8 and CRLF, like a Windows transcript
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\r\n" for r in (early, line)).encode("utf-8"))
        self.run_ledger("end", {"agent_id": "a2", "agent_type": "general-purpose", "agent_transcript_path": transcript,
                                "last_assistant_message": "ignored: the transcript handback wins"})
        (row,) = self.rows()
        self.assertEqual(row["summary_excerpt"], HANDBACK)
        self.assertEqual(row["outcome"], "BLOCKED")  # "— BLOCKED" survives only if the em dash did


if __name__ == "__main__":
    unittest.main()

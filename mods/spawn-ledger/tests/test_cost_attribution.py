"""B1 cost attribution: spawn_start records skills (case-insensitive 'Skills:' line, leading '/' stripped) and
jev_route_id (Jev[r=<id>] from the FULL prompt, not the 200-char excerpt). Additive fields.

Hermetic: SPAWN_LOG_FILE and SPAWN_LEDGER_METRICS_FILE point at a temp dir, ledger.ROOT/HOME are patched to the temp tree,
AGENCY_HOME / CLAUDE_CONFIG_DIR are dropped, SKILL_ROUTE_CHILD=1 keeps fire_shadow quiet. Nothing real is written.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ledger", os.path.join(HERE, "..", "bin", "ledger.py"))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
import test_home  # noqa: E402  (ledger.py put hooks/lib on sys.path)


class CostAttribution(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ledger-cost-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude"))
        self.log = os.path.join(self.tmp, "spawns.jsonl")
        env = {"SPAWN_LOG_FILE": self.log, "SKILL_ROUTE_CHILD": "1",
               "SPAWN_LEDGER_METRICS_FILE": os.path.join(self.tmp, "ev.jsonl"),
               "SKILL_ROUTE_STATE_DIR": os.path.join(self.tmp, "state")}
        env.update({k: test_home.home_env(self.home, base={})[k] for k in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")})
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        for k in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR", "SPAWN_LEDGER_EXTRA_LOGS"):
            os.environ.pop(k, None)
        for name, val in (("HOME", self.home), ("ROOT", os.path.join(self.home, ".claude"))):
            p = mock.patch.object(ledger, name, val)
            p.start()
            self.addCleanup(p.stop)

    def row(self, prompt):
        d = {"tool_use_id": "tu", "subagent_type": "general-purpose", "description": "d", "prompt": prompt, "model": "sonnet"}
        with contextlib.redirect_stdout(io.StringIO()):
            ledger.start(d)
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()][-1]

    def test_skills_mixed_case_and_slash(self):
        self.assertEqual(self.row("Skills: /backend, /frontend\nbody")["skills"], ["backend", "frontend"])

    def test_skills_uppercase_still_works(self):
        self.assertEqual(self.row("SKILLS: backend")["skills"], ["backend"])

    def test_route_id_beyond_excerpt(self):
        r = self.row("x" * 500 + "\nJev[r=3c386462]: modify - why\n")
        self.assertEqual(r["jev_route_id"], "3c386462")
        self.assertNotIn("Jev[", r["prompt_excerpt"])

    def test_no_route_id_is_empty_string(self):
        self.assertEqual(self.row("plain")["jev_route_id"], "")

    def test_existing_fields_kept(self):
        r = self.row("Jev[r=abcd1234]: accept")
        for k in ("spawn_id", "prompt_hash", "prompt_excerpt", "skills", "project", "model"):
            self.assertIn(k, r)


if __name__ == "__main__":
    unittest.main()

"""ledger.py project resolution: a spawn's start/launched/end rows land in the SAME per-project spawns.jsonl.

PD sessions run with cwd ~/.claude, so a cwd-only resolution put nearly every row in the global log. start now resolves
from the payload (Project: line, parent_agent/subagent_type {slug}-pd, then cwd); launched (tool_use_id only) and end
(agent_id only) follow the start row wherever it sits.

Hermetic: HOME + USERPROFILE (+ HOMEDRIVE/HOMEPATH: hooks/lib/test_home.py, so it is hermetic on Windows too, where
expanduser ignores HOME), SPAWN_MEDIUM_TERM, CLAUDE_PROJECT_DIR point at a temp tree; SKILL_ROUTE_CHILD=1 keeps fire_shadow quiet;
SPAWN_LEDGER_METRICS_FILE is a temp file; reconcile (a shell sweep) is patched out in-process. Nothing real is written.
Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "..", "bin", "ledger.py")
spec = importlib.util.spec_from_file_location("ledger", LEDGER)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
import claude_pricing  # noqa: E402  (ledger.py put hooks/lib on sys.path)
import test_home  # noqa: E402  (shared hermetic-home helper, hooks/lib/test_home.py)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="ledger-proj-test-"))
        self.home = os.path.join(self.tmp, "home")
        self.dl_root = os.path.join(self.home, ".claude", "projects", "delta")
        self.gamma_root = os.path.join(self.tmp, "projects", "gamma")
        self.cwd = os.path.join(self.home, ".claude")  # where PD sessions run
        os.makedirs(os.path.join(self.home, ".claude", "memory"))
        self.mt = os.path.join(self.tmp, "medium-term.md")
        with open(self.mt, "w") as f:
            f.write("| Project | Memory Path | PD | Flag |\n|---|---|---|---|\n")
            f.write("| delta | `~/.claude/projects/delta/memory/` | delta-pd | active |\n")
            f.write("| gamma | `%s/memory/` | gamma-pd | active |\n" % self.gamma_root)
        self.metrics = os.path.join(self.tmp, "events.jsonl")
        self.transcript = os.path.join(self.tmp, "t.jsonl")
        open(self.transcript, "w").close()
        env = {"SPAWN_MEDIUM_TERM": self.mt, "CLAUDE_PROJECT_DIR": self.cwd,
               "SPAWN_LEDGER_METRICS_FILE": self.metrics, "SKILL_ROUTE_CHILD": "1",
               "SKILL_ROUTE_STATE_DIR": os.path.join(self.tmp, "state")}
        env.update({k: test_home.home_env(self.home, base={})[k] for k in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")})
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        self.home_patch = mock.patch.object(ledger, "HOME", self.home)  # ledger.HOME is read at import: never the real one
        self.home_patch.start()
        for k in ("SPAWN_LOG_FILE", "SPAWN_LEDGER_EXTRA_LOGS", "AGENCY_HOME", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(k, None)  # the agency root must come from HOME here, never from the caller's env
        self.root_patch = mock.patch.object(ledger, "ROOT", os.path.join(self.home, ".claude"))
        self.root_patch.start()
        self.rec = mock.patch.object(ledger, "reconcile", lambda lf: None)
        self.rec.start()
        self.dl_log = os.path.join(self.dl_root, "memory", "spawns.jsonl")
        self.gamma_log = os.path.join(self.gamma_root, "memory", "spawns.jsonl")
        self.glog = os.path.join(self.home, ".claude", "logs", "spawns.jsonl")

    def tearDown(self):
        self.rec.stop()
        self.root_patch.stop()
        self.home_patch.stop()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rows(self, path):
        try:
            with open(path) as f:
                return [json.loads(l) for l in f if l.strip()]
        except FileNotFoundError:
            return []

    def events(self, path):
        return [r["event"] for r in self.rows(path)]

    def start(self, **kw):
        d = {"tool_use_id": "tu-1", "subagent_type": "general-purpose", "description": "d", "prompt": "do it",
             "model": "sonnet", "parent_spawn_id": "", "parent_agent": "root"}
        d.update(kw)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ledger.start(d)
        return out.getvalue().strip()

    def end(self, agent_id="a1"):
        u = {"first_ts": "2026-10-08T10:00:00+00:00", "last_ts": "2026-10-08T10:05:00+00:00", "tool_uses": 7,
             "handback_text": "DONE", "last_text": "DONE", "totals": {"cost_usd": 0.0}, "by_model": {}}
        d = {"agent_id": agent_id, "agent_type": "general-purpose", "agent_transcript_path": self.transcript,
             "last_assistant_message": "DONE"}
        with mock.patch.object(claude_pricing, "usage_from_transcript", lambda p: u), \
                contextlib.redirect_stdout(io.StringIO()):
            ledger.end(d)


class StartResolution(Base):
    def test_project_line_prompt_lands_in_project_log(self):
        sid = self.start(prompt="Project: delta -- ~/.claude/projects/delta/\nTask: x")
        rows = self.rows(self.dl_log)
        self.assertEqual([r["event"] for r in rows], ["spawn_start"])
        self.assertEqual(rows[0]["spawn_id"], sid)
        self.assertEqual(rows[0]["project"], "delta")
        self.assertEqual(self.rows(self.glog), [])

    def test_project_line_slug_first_word(self):
        self.start(prompt="Project: gamma\nbody")
        self.assertEqual(self.events(self.gamma_log), ["spawn_start"])
        self.assertEqual(self.rows(self.gamma_log)[0]["project"], "gamma")

    def test_parent_agent_pd(self):
        self.start(parent_agent="gamma-pd")
        self.assertEqual(self.events(self.gamma_log), ["spawn_start"])
        self.assertEqual(self.rows(self.glog), [])

    def test_subagent_type_pd(self):
        self.start(subagent_type="delta-pd")
        self.assertEqual(self.events(self.dl_log), ["spawn_start"])

    def test_cwd_project_still_resolves_without_hint(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.gamma_root + "/src"}):
            self.start()
        self.assertEqual(self.events(self.gamma_log), ["spawn_start"])

    def test_no_hint_pd_cwd_goes_global(self):
        self.start()
        self.assertEqual(self.events(self.glog), ["spawn_start"])
        # not ".claude" (the basename of the global log's grandparent): that read as a project of its own and hid that a
        # Windows machine's spawns had resolved to no project at all (the same label skill-route's recorder uses)
        self.assertEqual(self.rows(self.glog)[0]["project"], "global")

    def test_sibling_prefix_cwd_does_not_match(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.gamma_root + "bis"}):
            self.start()
        self.assertEqual(self.rows(self.gamma_log), [])
        self.assertEqual(self.events(self.glog), ["spawn_start"])

    def test_spawn_log_file_override_beats_hint(self):
        o = os.path.join(self.tmp, "override.jsonl")
        with mock.patch.dict(os.environ, {"SPAWN_LOG_FILE": o}):
            self.start(prompt="Project: gamma")
        self.assertEqual(self.events(o), ["spawn_start"])
        self.assertEqual(self.rows(self.gamma_log), [])

    def test_row_field_order_unchanged(self):
        self.start(prompt="Project: gamma")
        self.assertEqual(list(self.rows(self.gamma_log)[0]), [
            "event", "spawn_id", "tool_use_id", "parent_spawn_id", "parent_agent", "child_agent", "subagent_type",
            "description", "prompt_hash", "prompt_excerpt", "model", "model_source", "skills", "ts", "project"])


class LaunchedAndEndFollowStart(Base):
    PROMPT = "Project: delta -- ~/.claude/projects/delta/\nTask: x"

    def test_launched_and_end_append_next_to_start_row(self):
        sid = self.start(prompt=self.PROMPT)
        # the cwd/default resolution (PD cwd ~/.claude) would pick the global log: it must stay empty
        ledger.launched({"tool_use_id": "tu-1", "agent_id": "a1", "resolved_model": "claude-sonnet-5-5"})
        self.end("a1")
        self.assertEqual(self.events(self.dl_log), ["spawn_start", "spawn_launched", "spawn_end"])
        self.assertEqual(self.rows(self.glog), [])
        la, en = self.rows(self.dl_log)[1:]
        self.assertEqual((la["spawn_id"], en["spawn_id"]), (sid, sid))
        self.assertEqual(en["agent_id"], "a1")

    def test_launched_finds_start_in_global_log_when_cwd_resolves_a_project(self):
        sid = self.start()  # global (PD cwd)
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": self.gamma_root}):
            ledger.launched({"tool_use_id": "tu-1", "agent_id": "a1", "resolved_model": ""})
        self.assertEqual(self.events(self.glog), ["spawn_start", "spawn_launched"])
        self.assertEqual(self.rows(self.glog)[1]["spawn_id"], sid)
        self.assertEqual(self.rows(self.gamma_log), [])

    def test_launched_unknown_tool_use_id_appends_to_resolved_log(self):
        ledger.launched({"tool_use_id": "tu-unknown", "agent_id": "a9", "resolved_model": ""})
        rows = self.rows(self.glog)
        self.assertEqual([r["event"] for r in rows], ["spawn_launched"])
        self.assertEqual(rows[0]["spawn_id"], "")

    def test_two_projects_spawns_do_not_cross(self):
        s1 = self.start(tool_use_id="tu-1", prompt="Project: gamma")
        s2 = self.start(tool_use_id="tu-2", prompt=self.PROMPT)
        ledger.launched({"tool_use_id": "tu-2", "agent_id": "a2", "resolved_model": ""})
        ledger.launched({"tool_use_id": "tu-1", "agent_id": "a1", "resolved_model": ""})
        self.assertEqual([r.get("spawn_id") for r in self.rows(self.gamma_log)], [s1, s1])
        self.assertEqual([r.get("spawn_id") for r in self.rows(self.dl_log)], [s2, s2])

    def test_other_logs_uses_shared_module(self):
        self.start(prompt="Project: gamma")
        self.start(tool_use_id="tu-2", prompt=self.PROMPT)
        out = ledger.other_logs(self.dl_log)
        self.assertIn(os.path.abspath(self.gamma_log), out)
        self.assertNotIn(os.path.abspath(self.dl_log), out)


class WindowsHomeSemantics:
    """Mixin, regression for a real windows-latest CI run (15F+1E): on Windows
    os.path.expanduser("~") reads USERPROFILE and ignores HOME, and ledger.py called spawn_project WITHOUT home=,
    so spawn_project resolved the REAL runner home while the test (HOME only) thought it was in a temp tree; the
    write then hit refuses_real_ledger(). Re-runs every resolution test with expanduser = ntpath.expanduser and a
    DECOY USERPROFILE: the rows must still land in the ledger.HOME tree, and nothing may appear under the decoy."""

    def setUp(self):
        super().setUp()
        self.decoy = os.path.join(self.tmp, "decoy-userprofile")
        os.makedirs(os.path.join(self.decoy, ".claude", "memory"))
        self.win_env = mock.patch.dict(os.environ, {"USERPROFILE": self.decoy, "HOMEDRIVE": "", "HOMEPATH": self.decoy})
        self.win_env.start()
        self.win = test_home.windows_expanduser()
        self.win.__enter__()

    def tearDown(self):
        self.win.__exit__(None, None, None)
        self.win_env.stop()
        super().tearDown()

    def assertNothingUnderDecoy(self):
        for root, _d, files in os.walk(self.decoy):
            self.assertNotIn("spawns.jsonl", files, root)


class StartResolutionWinHome(WindowsHomeSemantics, StartResolution):
    def tearDown(self):
        try:
            self.assertNothingUnderDecoy()
        finally:
            super().tearDown()


class LaunchedAndEndFollowStartWinHome(WindowsHomeSemantics, LaunchedAndEndFollowStart):
    def tearDown(self):
        try:
            self.assertNothingUnderDecoy()
        finally:
            super().tearDown()


class CliExitZero(Base):
    def test_cli_start_with_project_prompt_exit_0_and_lands_in_project_log(self):
        env = dict(os.environ)  # HOME/SPAWN_MEDIUM_TERM/... already point at the temp tree
        r = subprocess.run([sys.executable, LEDGER, "start"], env=env, capture_output=True, text=True, timeout=30,
                           input=json.dumps({"tool_use_id": "tu-cli", "subagent_type": "general-purpose",
                                             "prompt": "Project: gamma", "parent_agent": "root"}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.events(self.gamma_log), ["spawn_start"])
        self.assertEqual(r.stdout.strip(), self.rows(self.gamma_log)[0]["spawn_id"])

    def test_cli_bad_stdin_exit_0(self):
        r = subprocess.run([sys.executable, LEDGER, "launched"], env=dict(os.environ), capture_output=True,
                           text=True, timeout=30, input="not json")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()

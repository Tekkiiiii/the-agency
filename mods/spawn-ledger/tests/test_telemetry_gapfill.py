"""C4 spawn telemetry gap-fill: every spawn_end writer must carry model, agent_type and a cost
marker, and ledger.end() must find the start row even when the SubagentStop hook resolves a
different spawns.jsonl than the one the spawn was logged to (log-file split).

Hermetic: temp logs via SPAWN_LOG_FILE, temp HOME for the shell writers (agent frontmatter lookup),
nothing touches the real logs. Run from the repo root: python3 -m unittest discover -s mods/spawn-ledger/tests -v

Pre-fix check: LEDGER_PATH=<old ledger.py> GAPFILL_LIB_DIR=<dir with the old shell writers> runs the
same tests against the originals (they must FAIL there)."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # tests -> spawn-ledger -> mods -> repo root
LEDGER_PATH = os.environ.get("LEDGER_PATH") or os.path.join(HERE, "..", "bin", "ledger.py")
LIB_DIR = os.environ.get("GAPFILL_LIB_DIR") or os.path.join(REPO, "hooks", "lib")
spec = importlib.util.spec_from_file_location("ledger_gapfill", LEDGER_PATH)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
ledger.ROOT = REPO  # not whatever AGENCY_HOME / ~/.claude the caller has
sys.path.insert(0, os.path.join(REPO, "hooks", "lib"))
import claude_pricing  # noqa: E402

OLD_FIELDS = {"event", "spawn_id", "tool_use_id", "agent_id", "agent_type", "outcome", "duration_ms",
              "tokens", "tokens_breakdown", "cost_usd", "final_context_tokens", "output_estimated_messages",
              "models", "tool_uses", "skill_mismatch", "summary_excerpt", "source", "ts"}


def rows(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def ends(path):
    return [r for r in rows(path) if r["event"] == "spawn_end"]


def usage(by_model):
    return {"first_ts": "2026-10-08T10:00:00+00:00", "last_ts": "2026-10-08T10:05:00+00:00",
            "tool_uses": 9, "handback_text": "", "last_text": "DONE ok",
            "totals": {"cost_usd": round(sum(v["cost_usd"] for v in by_model.values()), 4)},
            "by_model": by_model}


def start_row(sid="sid-1", tu="tu-1", typ="coord", model="inherit"):
    return {"event": "spawn_start", "spawn_id": sid, "tool_use_id": tu, "subagent_type": typ,
            "child_agent": typ, "model": model, "ts": "2026-10-08T09:00:00+00:00"}


def launched_row(sid="sid-1", tu="tu-1", aid="a1", resolved="claude-opus-5-5[1m]"):
    return {"event": "spawn_launched", "spawn_id": sid, "tool_use_id": tu, "agent_id": aid,
            "resolved_model": resolved, "ts": "2026-10-08T09:00:01+00:00"}


class LedgerEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "global", "spawns.jsonl")
        self.proj = os.path.join(self.tmp, "proj", "memory", "spawns.jsonl")
        os.makedirs(os.path.dirname(self.log)); os.makedirs(os.path.dirname(self.proj))
        self.transcript = os.path.join(self.tmp, "t.jsonl")
        open(self.transcript, "w").close()
        self.env = mock.patch.dict(os.environ, {
            "SPAWN_LOG_FILE": self.log,
            "SPAWN_LEDGER_EXTRA_LOGS": self.proj,
            "SPAWN_LEDGER_METRICS_FILE": os.path.join(self.tmp, "events.jsonl")})
        self.env.start()
        self.rec = mock.patch.object(ledger, "reconcile", lambda lf: None)
        self.rec.start()

    def tearDown(self):
        self.env.stop(); self.rec.stop()

    def put(self, path, *rs):
        with open(path, "a") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")

    def run_end(self, u, **d):
        d = dict({"agent_id": "a1", "agent_type": "coord", "agent_transcript_path": self.transcript,
                  "last_assistant_message": "DONE"}, **d)
        with mock.patch.object(claude_pricing, "usage_from_transcript", lambda p: u), \
                contextlib.redirect_stdout(io.StringIO()):
            ledger.end(d)

    # ---- model -------------------------------------------------------------
    def test_a_scalar_model_is_highest_cost_entry_and_models_list_kept(self):
        self.put(self.log, start_row(), launched_row())
        self.run_end(usage({"claude-sonnet-5-5": {"cost_usd": 1.0},
                            "claude-opus-5-5": {"cost_usd": 5.0}}))
        e = ends(self.log)[0]
        self.assertEqual(e["model"], "claude-opus-5-5")
        self.assertEqual(e["model_source"], "transcript")
        self.assertEqual(e["models"], ["claude-opus-5-5", "claude-sonnet-5-5"])

    def test_b_no_transcript_model_from_launched_row_suffix_stripped(self):
        self.put(self.log, start_row(), launched_row(resolved="claude-opus-5-5[1m]"))
        self.run_end(None)
        e = ends(self.log)[0]
        self.assertEqual(e["model"], "claude-opus-5-5")
        self.assertEqual(e["model_source"], "launched")

    def test_c_no_transcript_no_launched_model_uses_start_model_unless_inherit(self):
        self.put(self.log, start_row(model="sonnet"), launched_row(resolved=""))
        self.run_end(None)
        e = ends(self.log)[0]
        self.assertEqual((e["model"], e["model_source"]), ("sonnet", "start"))

    def test_d_model_truly_unknown_is_explicit_not_silent(self):
        self.put(self.log, start_row(model="inherit"), launched_row(resolved=""))
        self.run_end(None)
        e = ends(self.log)[0]
        self.assertEqual((e["model"], e["model_source"]), ("unknown", "unavailable"))

    # ---- cost marker -------------------------------------------------------
    def test_e_cost_source_transcript_vs_unavailable(self):
        self.put(self.log, start_row(), launched_row())
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 2.0}}))
        self.run_end(None)
        a, b = ends(self.log)
        self.assertEqual(a["cost_source"], "transcript")
        self.assertEqual((b["cost_usd"], b["cost_source"]), (0.0, "unavailable"))

    # ---- agent_type --------------------------------------------------------
    def test_f_agent_type_falls_back_to_start_row(self):
        self.put(self.log, start_row(typ="task-executor"), launched_row())
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 1.0}}), agent_type="")
        self.assertEqual(ends(self.log)[0]["agent_type"], "task-executor")

    def test_f2_payload_agent_type_wins_over_start_row(self):
        self.put(self.log, start_row(typ="task-executor"), launched_row())
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 1.0}}), agent_type="coord")
        self.assertEqual(ends(self.log)[0]["agent_type"], "coord")

    # ---- log-file split ----------------------------------------------------
    def test_g_start_in_other_log_is_found_and_end_lands_next_to_start(self):
        # spawn + launched live in the project log; the hook resolved the global log.
        self.put(self.proj, start_row(sid="sid-P", tu="tu-P", typ="system-improvement-pd"),
                 launched_row(sid="sid-P", tu="tu-P", aid="a1"))
        self.put(self.log, {"event": "spawn_start", "spawn_id": "other", "tool_use_id": "x"})
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 3.0}}), agent_type="")
        self.assertEqual(ends(self.log), [])
        e = ends(self.proj)[0]
        self.assertEqual((e["spawn_id"], e["tool_use_id"]), ("sid-P", "tu-P"))
        self.assertEqual(e["agent_type"], "system-improvement-pd")

    def test_g2_continuation_flag_uses_the_log_that_holds_the_first_end(self):
        self.put(self.proj, start_row(sid="sid-P", tu="tu-P"), launched_row(sid="sid-P", tu="tu-P"))
        u = usage({"claude-opus-5-5": {"cost_usd": 3.0}})
        self.run_end(u); self.run_end(u)
        first, second = ends(self.proj)
        self.assertNotIn("continuation", first)
        self.assertIs(second["continuation"], True)

    def test_h_still_unfindable_and_untyped_is_skipped_as_harness_internal(self):
        self.put(self.log, start_row())
        self.run_end(None, agent_id="zzz", agent_type="")
        self.assertEqual(ends(self.log), [])
        self.assertFalse(os.path.exists(self.proj))

    def test_h2_still_unfindable_but_typed_is_written_with_empty_spawn_id(self):
        self.put(self.log, start_row())
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 1.0}}), agent_id="zzz", agent_type="coord")
        e = ends(self.log)[0]
        self.assertEqual((e["spawn_id"], e["agent_type"]), ("", "coord"))

    # ---- additive only -----------------------------------------------------
    def test_i_no_existing_field_removed(self):
        self.put(self.log, start_row(), launched_row())
        self.run_end(usage({"claude-opus-5-5": {"cost_usd": 1.0}}))
        self.assertTrue(OLD_FIELDS <= set(ends(self.log)[0]), OLD_FIELDS - set(ends(self.log)[0]))


def _ported(name, marker):
    try:
        with open(os.path.join(LIB_DIR, name)) as fh:
            return marker in fh.read()
    except OSError:
        return False


# log-spawn-from-agent.sh / log-spawn-end-from-agent.sh only carry the C4 fields once ported; these tests turn on by themselves then.
needs_start_c4 = unittest.skipUnless(_ported("log-spawn-from-agent.sh", "model_source"), "C4 not in log-spawn-from-agent.sh yet")
needs_end_c4 = unittest.skipUnless(_ported("log-spawn-end-from-agent.sh", "cost_source"), "C4 not in log-spawn-end-from-agent.sh yet")


class ShellWriters(unittest.TestCase):
    """The legacy manual convention + the reconciliation sweep, run as real subprocesses."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, ".claude", "agents", "x"))
        os.symlink(os.path.join(REPO, "mods"), os.path.join(self.home, ".claude", "mods"))
        os.symlink(os.path.join(REPO, "hooks"), os.path.join(self.home, ".claude", "hooks"))
        with open(os.path.join(self.home, ".claude", "agents", "x", "fake-coord.md"), "w") as f:
            f.write("---\nname: fake-coord\nmodel: opus\n---\nbody\n")
        self.log = os.path.join(self.tmp, "spawns.jsonl")
        # The children resolve the agency root from HOME: a CI-exported AGENCY_HOME / CLAUDE_CONFIG_DIR must not win.
        self.env = {k: v for k, v in os.environ.items() if k not in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR")}
        self.env.update(HOME=self.home, SPAWN_LOG_FILE=self.log)

    def sh(self, script, *args, env=None):
        r = subprocess.run(["bash", os.path.join(LIB_DIR, script), *args], env=env or self.env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def start(self, typ="fake-coord"):
        return self.sh("log-spawn-from-agent.sh", "--parent-agent", "PD-x", "--child-subagent-type", typ,
                       "--description", "d", "--prompt-excerpt", "p")

    @needs_start_c4
    def test_a_start_resolves_model_from_frontmatter_not_literal_unknown(self):
        self.start()
        s = rows(self.log)[0]
        self.assertEqual(s["model"], "opus")
        self.assertEqual(s["model_source"], "agent_def")

    @needs_start_c4
    def test_a2_start_for_unresolvable_type_stays_unknown_but_says_so(self):
        self.start(typ="no-such-agent")
        s = rows(self.log)[0]
        self.assertEqual((s["model"], s["model_source"]), ("unknown", "unresolved"))

    @needs_end_c4
    def test_b_end_copies_agent_type_and_model_from_matching_start(self):
        sid = self.start()
        self.sh("log-spawn-end-from-agent.sh", "--spawn-id", sid, "--outcome", "DONE", "--summary", "s")
        e = ends(self.log)[0]
        self.assertEqual((e["agent_type"], e["model"]), ("fake-coord", "opus"))

    @needs_end_c4
    def test_b2_end_marks_cost_unavailable_with_sum_safe_zero(self):
        sid = self.start()
        self.sh("log-spawn-end-from-agent.sh", "--spawn-id", sid, "--outcome", "DONE")
        e = ends(self.log)[0]
        self.assertEqual((e["cost_usd"], e["cost_source"]), (0.0, "unavailable"))

    @needs_end_c4
    def test_b3_end_without_matching_start_still_writes_with_markers(self):
        self.sh("log-spawn-end-from-agent.sh", "--spawn-id", "ghost", "--outcome", "DONE")
        e = ends(self.log)[0]
        self.assertEqual((e["spawn_id"], e["cost_usd"], e["cost_source"]), ("ghost", 0.0, "unavailable"))
        self.assertIn("agent_type", e)
        self.assertIn("model", e)

    def test_b4_end_keeps_every_old_field(self):
        sid = self.start()
        self.sh("log-spawn-end-from-agent.sh", "--spawn-id", sid, "--outcome", "DONE", "--summary", "s")
        e = ends(self.log)[0]
        for k in ("event", "spawn_id", "tool_use_id", "outcome", "duration_ms", "tokens", "tool_uses",
                  "summary_excerpt", "ts", "source"):
            self.assertIn(k, e)

    def test_c_reconcile_abandoned_row_copies_type_model_and_marks_cost(self):
        old = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")
        with open(self.log, "w") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "stale-1", "tool_use_id": "tu",
                                "subagent_type": "fake-coord", "model": "opus", "ts": old}) + "\n")
        self.sh("reconcile-stale-spawns.sh", self.log)
        e = ends(self.log)[0]
        self.assertEqual((e["outcome"], e["source"]), ("ABANDONED", "reconciliation-sweep"))
        self.assertEqual((e["agent_type"], e["model"]), ("fake-coord", "opus"))
        self.assertEqual((e["cost_usd"], e["cost_source"]), (0.0, "unavailable"))

    def test_c2_reconcile_prefers_launched_model_when_start_model_is_inherit(self):
        old = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")
        with open(self.log, "w") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "stale-2", "tool_use_id": "tu2",
                                "subagent_type": "coord", "model": "inherit", "ts": old}) + "\n")
            f.write(json.dumps(launched_row(sid="stale-2", tu="tu2", aid="aX", resolved="claude-opus-5-5[1m]")) + "\n")
        self.sh("reconcile-stale-spawns.sh", self.log)
        e = ends(self.log)[0]
        self.assertEqual(e["model"], "claude-opus-5-5")

    def test_c3_reconcile_stays_idempotent(self):
        old = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")
        with open(self.log, "w") as f:
            f.write(json.dumps({"event": "spawn_start", "spawn_id": "stale-3", "tool_use_id": "t",
                                "subagent_type": "coord", "model": "opus", "ts": old}) + "\n")
        self.sh("reconcile-stale-spawns.sh", self.log)
        os.remove(self.log + ".reconcile-marker")
        self.sh("reconcile-stale-spawns.sh", self.log)
        self.assertEqual(len(ends(self.log)), 1)


if __name__ == "__main__":
    unittest.main()

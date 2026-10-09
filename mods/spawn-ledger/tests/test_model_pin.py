#!/usr/bin/env python3
"""Fixture tests for hooks/lib/model-pin.py (model pin + Exec cap).

Every test pipes fixture JSON into the CLI via subprocess with temp dirs and env
overrides; the real logs, state and agents are never touched.
Run from the repo root: python3 -m unittest -v mods/spawn-ledger/tests/test_model_pin.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# tests -> spawn-ledger -> mods -> repo root
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hooks", "lib")
SCRIPT = os.path.join(LIB, "model-pin.py")
REAL_MAP = os.path.join(LIB, "exec-model-map.json")
NOW = 1_791_000_000  # fixed epoch for MODEL_PIN_NOW

DEFAULT_MAP = {
    "default": "sonnet",
    "categories": {},
    "escalation": {"enabled": False, "allowed": ["opus"]},
    "exec_cap": {"enabled": True, "max": 5, "types": ["general-purpose", "task-executor"],
                 "include_root": False, "stale_after_sec": 7200},
}


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).astimezone().isoformat(timespec="seconds")


def agent_file(name, model=None):
    fm = "---\nname: %s\n" % name
    if model is not None:
        fm += "model: %s\n" % model
    fm += "description: test\n---\nbody\n"
    return fm


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="model-pin-test-")
        self.agents = os.path.join(self.tmp, "agents")
        self.state = os.path.join(self.tmp, "state")
        self.home = os.path.join(self.tmp, "home")
        self.log = os.path.join(self.tmp, "logs", "spawns.jsonl")
        self.glog = os.path.join(self.tmp, "global", "spawns.jsonl")
        self.map = os.path.join(self.tmp, "map.json")
        for d in (self.agents, self.state, os.path.join(self.home, ".claude"), os.path.dirname(self.log)):
            os.makedirs(d)
        open(self.log, "w").close()
        self.write_map(DEFAULT_MAP)
        self.add_agent("pinned-sonnet", "sonnet[1m]")
        self.add_agent("pinned-opus", "opus[1m]")
        self.add_agent("no-model")
        self.add_agent("inheriting", "inherit")
        self.n = 0
        # The cap walks ancestry to the root PD. P1 is the PD that most fixtures spawn under.
        # (in the global log so tests asserting "the resolved log stays empty" keep their meaning)
        self.put(self.start("P1", parent="", typ="test-pd", pa="root"), path=self.glog)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- helpers
    def write_map(self, m):
        with open(self.map, "w") as f:
            json.dump(m, f)

    def map_with(self, **over):
        m = json.loads(json.dumps(DEFAULT_MAP))
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(m.get(k), dict):
                m[k].update(v)
            else:
                m[k] = v
        self.write_map(m)

    def add_agent(self, name, model=None, sub=""):
        d = os.path.join(self.agents, sub) if sub else self.agents
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name + ".md"), "w") as f:
            f.write(agent_file(name, model))

    def env(self, **extra):
        e = {k: v for k, v in os.environ.items()
             if not k.startswith(("MODEL_PIN_", "SPAWN_")) and k not in ("AGENCY_HOME", "CLAUDE_CONFIG_DIR")}
        e.update({
            "SPAWN_LOG_FILE": self.log, "MODEL_PIN_MAP": self.map,
            "MODEL_PIN_AGENTS_DIR": self.agents, "MODEL_PIN_STATE_DIR": self.state,
            "MODEL_PIN_NOW": str(NOW), "MODEL_PIN_HOME": self.home,
            "MODEL_PIN_GLOBAL_LOG": self.glog,
        })
        e.update(extra)
        return e

    def payload(self, **kw):
        self.n += 1
        p = {"subagent_type": "general-purpose", "model": None, "fork": False, "is_teammate": False,
             "workflow": False, "parent_spawn_id": "", "parent_agent": "root",
             "tool_use_id": "toolu_%d" % self.n, "description": "d", "prompt": "p"}
        if kw.get("parent_spawn_id") == "P1":  # P1 is the seeded PD: its direct children carry its type
            p["parent_agent"] = "test-pd"
        p.update(kw)
        return p

    def run_raw(self, stdin, env=None):
        r = subprocess.run([sys.executable, SCRIPT], input=stdin, capture_output=True, text=True,
                           env=env or self.env(), timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, "expected ONE output line, got %r" % r.stdout)
        return json.loads(lines[0])

    def run_pin(self, env=None, **kw):
        return self.run_raw(json.dumps(self.payload(**kw)), env)

    def rows(self, path=None):
        out = []
        try:
            with open(path or self.log) as f:
                for l in f:
                    if l.strip():
                        out.append(json.loads(l))
        except FileNotFoundError:
            pass
        return out

    def events(self, name, path=None):
        return [r for r in self.rows(path) if r.get("event") == name]

    def put(self, *rows, path=None):
        p = path or self.log
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def start(self, sid, parent="P1", typ="general-purpose", age=60, tool=None, pa=None):
        if pa is None:  # parent_agent = the parent's subagent_type, as the ledger records it
            pa = "test-pd" if parent == "P1" else ("root" if parent == "" else "coord")
        return {"event": "spawn_start", "spawn_id": sid, "tool_use_id": tool if tool is not None else "tu-" + sid,
                "parent_spawn_id": parent, "parent_agent": pa, "subagent_type": typ, "ts": iso(NOW - age)}

    def end(self, sid="", agent_id="", outcome="DONE", tool=""):
        return {"event": "spawn_end", "spawn_id": sid, "tool_use_id": tool, "agent_id": agent_id,
                "outcome": outcome, "ts": iso(NOW - 5)}

    def launched(self, sid, agent_id):
        return {"event": "spawn_launched", "spawn_id": sid, "tool_use_id": "tu-" + sid, "agent_id": agent_id,
                "ts": iso(NOW - 50)}


class NamedAgentTests(Base):
    def test_named_opus_param_vs_sonnet_frontmatter_strips(self):
        o = self.run_pin(subagent_type="pinned-sonnet", model="opus")
        self.assertEqual(o["action"], "rewrite")
        self.assertIsNone(o["model"])
        self.assertEqual(o["old"], "opus")
        self.assertEqual(o["new"], "sonnet[1m]")
        self.assertEqual(o["reason"], "named_frontmatter_wins")

    def test_named_matching_param_passes(self):
        for param in ("sonnet[1m]", "sonnet", "SONNET"):
            self.assertEqual(self.run_pin(subagent_type="pinned-sonnet", model=param)["action"], "pass", param)

    def test_named_absent_param_passes(self):
        self.assertEqual(self.run_pin(subagent_type="pinned-sonnet", model=None)["action"], "pass")

    def test_named_without_frontmatter_model_passes(self):
        self.assertEqual(self.run_pin(subagent_type="no-model", model="opus")["action"], "pass")

    def test_named_inherit_passes(self):
        self.assertEqual(self.run_pin(subagent_type="inheriting", model="opus")["action"], "pass")

    def test_unknown_and_plugin_types_pass(self):
        for t in ("Explore", "Plan", "some-plugin:agent", "ghost"):
            o = self.run_pin(subagent_type=t, model="opus")
            self.assertEqual(o["action"], "pass", t)

    def test_nested_agent_dir_found(self):
        self.add_agent("deep-one", "haiku", sub="eng/sub")
        o = self.run_pin(subagent_type="deep-one", model="opus")
        self.assertEqual((o["action"], o["new"]), ("rewrite", "haiku"))

    def test_named_opus_frontmatter_strips_sonnet_param(self):
        # frontmatter is the single source of truth, in both directions
        o = self.run_pin(subagent_type="pinned-opus", model="sonnet")
        self.assertEqual((o["action"], o["model"], o["new"]), ("rewrite", None, "opus[1m]"))

    def test_override_row_logged_for_named(self):
        o = self.run_pin(subagent_type="pinned-sonnet", model="opus", tool_use_id="tu-N", parent_spawn_id="PX")
        rows = self.events("model_override")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["tool_use_id"], r["subagent_type"], r["old"], r["new"], r["reason"], r["parent_spawn_id"]),
                         ("tu-N", "pinned-sonnet", "opus", "sonnet[1m]", "named_frontmatter_wins", "PX"))
        self.assertRegex(r["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        self.assertEqual(o["action"], "rewrite")

    def test_pass_logs_nothing(self):
        self.run_pin(subagent_type="pinned-sonnet", model="sonnet")
        self.assertEqual(self.rows(), [])


class GeneralPurposeTests(Base):
    def test_no_param_gets_sonnet(self):
        o = self.run_pin(model=None)
        self.assertEqual((o["action"], o["model"], o["old"], o["new"], o["reason"]),
                         ("rewrite", "sonnet", None, "sonnet", "gp_category_map"))

    def test_opus_param_gets_sonnet(self):
        o = self.run_pin(model="opus")
        self.assertEqual((o["action"], o["model"], o["old"]), ("rewrite", "sonnet", "opus"))

    def test_sonnet_1m_passes(self):
        self.assertEqual(self.run_pin(model="sonnet[1m]")["action"], "pass")
        self.assertEqual(self.run_pin(model="sonnet")["action"], "pass")

    def test_claude_and_empty_type_are_general_purpose(self):
        for t in ("claude", ""):
            o = self.run_pin(subagent_type=t, model="opus")
            self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"), t)

    def test_filled_category_entry(self):
        self.map_with(categories={"lookup": "haiku", "debug": "sonnet[1m]", "review": ""})
        o = self.run_pin(model="opus", prompt="work\nMODEL-CATEGORY: lookup\nmore")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "haiku"))
        o = self.run_pin(model="opus", description="x [category:lookup]")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "haiku"))
        self.assertEqual(self.run_pin(model="haiku", description="[category:lookup]")["action"], "pass")
        # empty entry and unknown category fall back to default
        self.assertEqual(self.run_pin(model="opus", prompt="MODEL-CATEGORY: review")["model"], "sonnet")
        self.assertEqual(self.run_pin(model="opus", prompt="MODEL-CATEGORY: nonsense")["model"], "sonnet")

    def test_category_marker_in_fenced_block_ignored(self):
        self.map_with(categories={"lookup": "haiku"})
        o = self.run_pin(model=None, prompt="```\nMODEL-CATEGORY: lookup\n```\n")
        self.assertEqual(o["model"], "sonnet")

    def test_custom_default(self):
        self.map_with(default="haiku")
        self.assertEqual(self.run_pin(model="opus")["model"], "haiku")

    def test_gp_rewrite_logs_row(self):
        self.run_pin(model="opus", tool_use_id="tu-G", parent_spawn_id="PP")
        r = self.events("model_override")[0]
        self.assertEqual((r["old"], r["new"], r["reason"], r["subagent_type"]),
                         ("opus", "sonnet", "gp_category_map", "general-purpose"))
        self.run_pin(model=None, tool_use_id="tu-H")
        self.assertIsNone(self.events("model_override")[1]["old"])


class EscalationTests(Base):
    PROMPT = "task\nMODEL-ESCALATE: opus - architecture call needs depth\n"

    def test_disabled_marker_ignored(self):
        o = self.run_pin(model="opus", prompt=self.PROMPT)
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))
        self.assertIn("escalation", o["reason"])  # notes the ignored marker
        self.assertTrue(o["reason"].startswith("gp_category_map"))

    def test_enabled_marker_honoured(self):
        self.map_with(escalation={"enabled": True})
        o = self.run_pin(model="sonnet", prompt=self.PROMPT)
        self.assertEqual((o["action"], o["model"], o["new"]), ("rewrite", "opus", "opus"))
        self.assertEqual(o["reason"], "escalation_marker:architecture call needs depth")

    def test_enabled_marker_em_dash_and_already_opus(self):
        self.map_with(escalation={"enabled": True})
        o = self.run_pin(model="opus", prompt="MODEL-ESCALATE: opus \u2014 hard debug\n")
        self.assertEqual(o["action"], "pass")
        o = self.run_pin(model=None, prompt="MODEL-ESCALATE: opus \u2014 hard debug\n")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "opus"))

    def test_enabled_reason_required(self):
        self.map_with(escalation={"enabled": True})
        for bad in ("MODEL-ESCALATE: opus\n", "MODEL-ESCALATE: opus - \n", "MODEL-ESCALATE: opus -   \n"):
            o = self.run_pin(model="opus", prompt=bad)
            self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"), bad)

    def test_enabled_model_not_allowed(self):
        self.map_with(escalation={"enabled": True, "allowed": ["opus"]})
        o = self.run_pin(model="sonnet", prompt="MODEL-ESCALATE: haiku - because\n")
        self.assertEqual(o["action"], "pass")

    def test_marker_must_be_own_line(self):
        self.map_with(escalation={"enabled": True})
        o = self.run_pin(model="sonnet", prompt="docs say `MODEL-ESCALATE: opus - why` is the form")
        self.assertEqual(o["action"], "pass")

    def test_marker_does_not_affect_named_agents(self):
        self.map_with(escalation={"enabled": True})
        o = self.run_pin(subagent_type="pinned-sonnet", model="opus", prompt=self.PROMPT)
        self.assertEqual((o["action"], o["reason"]), ("rewrite", "named_frontmatter_wins"))


class UntouchedTests(Base):
    def test_fork_untouched(self):
        self.assertEqual(self.run_pin(fork=True, model="opus")["action"], "pass")
        self.assertEqual(self.run_pin(fork=True, model="opus", subagent_type="pinned-sonnet")["action"], "pass")

    def test_teammate_untouched(self):
        self.assertEqual(self.run_pin(is_teammate=True, model="opus")["action"], "pass")

    def test_workflow_untouched(self):
        self.assertEqual(self.run_pin(workflow=True, model="opus")["action"], "pass")

    def test_fork_teammate_workflow_skip_cap(self):
        self.put(*[self.start("s%d" % i, parent="P1") for i in range(5)])
        for kw in ({"fork": True}, {"is_teammate": True}, {"workflow": True}):
            self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet", **kw)["action"], "pass", kw)


class FailOpenTests(Base):
    def test_malformed_stdin_passes(self):
        for s in ("", "not json", "[1,2]", "{"):
            o = self.run_raw(s)
            self.assertEqual(o["action"], "pass", s)
        self.assertTrue(o["reason"].startswith("error"))

    def test_corrupt_map_passes_with_error_row(self):
        with open(self.map, "w") as f:
            f.write("{ this is not json")
        o = self.run_pin(model="opus")
        self.assertEqual(o["action"], "pass")
        self.assertTrue(o["reason"].startswith("error"), o)
        errs = self.events("model_pin_error")
        self.assertEqual(len(errs), 1)
        self.assertIn("error", json.dumps(errs[0]).lower())
        self.assertIn("ts", errs[0])

    def test_map_wrong_shape_passes(self):
        self.write_map(["a", "list"])
        self.assertEqual(self.run_pin(model="opus")["action"], "pass")
        self.write_map({"default": "sonnet", "categories": "nope"})
        self.assertEqual(self.run_pin(model="opus")["action"], "pass")

    def test_missing_map_uses_builtin_default(self):
        os.unlink(self.map)
        o = self.run_pin(model="opus")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))

    def test_unwritable_log_still_answers(self):
        o = self.run_pin(env=self.env(SPAWN_LOG_FILE="/proc/definitely/not/writable/x.jsonl"), model="opus")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))

    def test_unusable_state_dir_fails_open_for_cap(self):
        bad = os.path.join(self.tmp, "afile")
        open(bad, "w").close()
        o = self.run_pin(env=self.env(MODEL_PIN_STATE_DIR=os.path.join(bad, "sub")),
                         parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "pass")


class KillSwitchTests(Base):
    def test_env_kill_switch(self):
        o = self.run_pin(env=self.env(MODEL_PIN_OFF="1"), model="opus")
        self.assertEqual(o["action"], "pass")
        self.assertEqual(self.rows(), [])

    def test_flag_file_kill_switch(self):
        open(os.path.join(self.state, "model-pin.off"), "w").close()
        self.assertEqual(self.run_pin(model="opus")["action"], "pass")
        self.assertEqual(self.run_pin(subagent_type="pinned-sonnet", model="opus")["action"], "pass")
        self.assertEqual(self.rows(), [])

    def test_minimal_profile_kill_switch(self):
        with open(os.path.join(self.home, ".claude", ".hook-profile"), "w") as f:
            f.write("minimal\n")
        self.assertEqual(self.run_pin(model="opus")["action"], "pass")
        self.assertEqual(self.rows(), [])

    def test_standard_profile_does_not_disable(self):
        with open(os.path.join(self.home, ".claude", ".hook-profile"), "w") as f:
            f.write("standard\n")
        self.assertEqual(self.run_pin(model="opus")["action"], "rewrite")

    def test_cap_kill_switch_env_and_flag_only_disable_cap(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "deny")
        o = self.run_pin(env=self.env(SPAWN_CAP_OFF="1"), parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "pass")
        open(os.path.join(self.state, "spawn-cap.off"), "w").close()
        o = self.run_pin(parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "pass")
        # the model pin itself still works with the cap off
        o = self.run_pin(parent_spawn_id="P1", model="opus")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))

    def test_cap_disabled_in_map(self):
        self.map_with(exec_cap={"enabled": False})
        self.put(*[self.start("s%d" % i) for i in range(9)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")


class CapTests(Base):
    MSG = ("[spawn-cap] 5 Execs already running under PD test-pd tree (cap 5, Exec cap policy: max 5 Execs per PD "
           "across all its coords). Please wait for a slot - a completion notification arrives on its own - then "
           "spawn again, or merge tasks. Do not retry in a loop.")

    def test_four_running_fifth_allowed(self):
        self.put(*[self.start("s%d" % i) for i in range(4)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")

    def test_five_running_sixth_denied(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        o = self.run_pin(parent_spawn_id="P1", model="sonnet", tool_use_id="tu-six")
        self.assertEqual(o["action"], "deny")
        self.assertEqual(o["deny"], self.MSG)
        rows = self.events("spawn_denied")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["tool_use_id"], r["subagent_type"], r["parent_spawn_id"], r["running"], r["cap"]),
                         ("tu-six", "general-purpose", "P1", 5, 5))
        self.assertEqual(r["root"], "pd:test-pd")
        self.assertIn("ts", r)

    def test_denied_spawn_is_not_reserved(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        self.run_pin(parent_spawn_id="P1", model="sonnet")
        slots = os.path.join(self.state, "spawn-slots.jsonl")
        content = ""
        if os.path.exists(slots):
            with open(slots) as f:
                content = f.read().strip()
        self.assertEqual(content, "")

    def test_task_executor_counts_and_is_capped(self):
        self.put(*[self.start("s%d" % i, typ="task-executor") for i in range(5)])
        self.assertEqual(self.run_pin(subagent_type="task-executor", parent_spawn_id="P1")["action"], "deny")
        # a general-purpose spawn counts the task-executors too
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "deny")

    def test_other_types_not_counted_or_capped(self):
        self.put(*[self.start("s%d" % i, typ="coord") for i in range(8)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")
        self.put(*[self.start("t%d" % i, typ="general-purpose") for i in range(5)])
        self.assertEqual(self.run_pin(subagent_type="pinned-sonnet", parent_spawn_id="P1")["action"], "pass")

    def test_ended_by_spawn_id_not_counted(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        self.put(self.end(sid="s0"))
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")

    def test_ended_by_agent_id_via_launched_not_counted(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        self.put(self.launched("s0", "agent-0"), self.launched("s1", "agent-1"))
        # spawn_end rows without spawn_id: matched only through agent_id
        self.put(self.end(sid="", agent_id="agent-0"))
        o = self.run_pin(parent_spawn_id="P1", model="sonnet")  # 4 running -> allowed, reserves slot 5
        self.assertEqual(o["action"], "pass")
        o = self.run_pin(parent_spawn_id="P1", model="sonnet")  # 4 running + 1 reservation -> denied
        self.assertEqual(o["action"], "deny")

    def test_abandoned_rows_not_counted(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        self.put(self.end(sid="s3", outcome="ABANDONED"), self.end(sid="s4", outcome="ABANDONED"))
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")

    def test_stale_start_not_counted(self):
        self.put(*[self.start("s%d" % i, age=3 * 3600) for i in range(5)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")
        self.put(*[self.start("f%d" % i, age=7000) for i in range(5)])  # inside 7200
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "deny")

    def test_other_parents_children_not_counted(self):
        self.put(self.start("OTHER", parent="", typ="other-pd", pa="root"))
        self.put(*[self.start("s%d" % i, parent="OTHER") for i in range(9)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")

    def test_root_exempt_and_include_root(self):
        self.put(*[self.start("s%d" % i, parent="") for i in range(9)])
        self.assertEqual(self.run_pin(parent_spawn_id="", model="sonnet")["action"], "pass")
        self.map_with(exec_cap={"include_root": True})
        self.assertEqual(self.run_pin(parent_spawn_id="", model="sonnet")["action"], "deny")

    def test_custom_max(self):
        self.map_with(exec_cap={"max": 2})
        self.put(self.start("a"), self.start("b"))
        o = self.run_pin(parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "deny")
        self.assertIn("(cap 2,", o["deny"])
        self.assertIn("2 Execs already running", o["deny"])
        self.assertIn("wait for a slot", o["deny"])

    def test_global_log_scanned_when_it_differs(self):
        self.put(*[self.start("g%d" % i) for i in range(5)], path=self.glog)
        o = self.run_pin(parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "deny")
        # only the resolved log gets the denial row
        self.assertEqual(len(self.events("spawn_denied")), 1)
        self.assertEqual(self.events("spawn_denied", self.glog), [])

    def test_global_log_same_as_resolved_not_double_counted(self):
        self.put(*[self.start("s%d" % i) for i in range(4)])
        o = self.run_pin(env=self.env(MODEL_PIN_GLOBAL_LOG=self.log), parent_spawn_id="P1", model="sonnet")
        self.assertEqual(o["action"], "pass")

    def test_reservation_counts_until_start_row_or_expiry(self):
        self.put(*[self.start("s%d" % i) for i in range(4)])
        first = self.run_pin(parent_spawn_id="P1", model="sonnet", tool_use_id="tu-A")
        self.assertEqual(first["action"], "pass")
        # reservation for tu-A holds the 5th slot
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet", tool_use_id="tu-B")["action"], "deny")
        # tu-A's spawn_start appears (counted as running now, reservation is dropped): still 5 -> denied
        self.put(self.start("sA", tool="tu-A"))
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet", tool_use_id="tu-B")["action"], "deny")
        # tu-A ends -> 4 running -> allowed
        self.put(self.end(sid="sA"))
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet", tool_use_id="tu-B")["action"], "pass")

    def test_reservation_expires_after_60s(self):
        self.put(*[self.start("s%d" % i) for i in range(4)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", tool_use_id="tu-A", model="sonnet")["action"], "pass")
        later = self.env(MODEL_PIN_NOW=str(NOW + 61))
        # starts are 61s older now but still within the stale window
        self.assertEqual(self.run_pin(env=later, parent_spawn_id="P1", tool_use_id="tu-B", model="sonnet")["action"],
                         "pass")

    def test_same_tool_use_id_retry_not_double_reserved(self):
        self.put(*[self.start("s%d" % i) for i in range(3)])
        for _ in range(3):
            self.assertEqual(self.run_pin(parent_spawn_id="P1", tool_use_id="tu-R", model="sonnet")["action"], "pass")
        self.assertEqual(self.run_pin(parent_spawn_id="P1", tool_use_id="tu-S", model="sonnet")["action"], "pass")
        self.assertEqual(self.run_pin(parent_spawn_id="P1", tool_use_id="tu-T", model="sonnet")["action"], "deny")

    def test_cap_and_rewrite_together(self):
        self.put(*[self.start("s%d" % i) for i in range(5)])
        o = self.run_pin(parent_spawn_id="P1", model="opus")
        self.assertEqual(o["action"], "deny")
        self.assertEqual(self.events("model_override"), [])  # a denied spawn logs only the denial

    def test_allowed_rewrite_under_cap_still_rewrites(self):
        self.put(*[self.start("s%d" % i) for i in range(2)])
        o = self.run_pin(parent_spawn_id="P1", model="opus")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))

    def test_garbage_log_lines_tolerated(self):
        with open(self.log, "a") as f:
            f.write("not json\n\n{\"event\": \"spawn_start\"}\n[1]\n")
        self.put(*[self.start("s%d" % i) for i in range(4)])
        self.assertEqual(self.run_pin(parent_spawn_id="P1", model="sonnet")["action"], "pass")

    def test_race_eight_processes_exactly_five_allowed(self):
        payloads = [json.dumps(self.payload(parent_spawn_id="PRACE", parent_agent="race-pd", model="sonnet",
                                            tool_use_id="tu-race-%d" % i))
                    for i in range(8)]
        env = self.env(MODEL_PIN_TEST_RACE_DELAY="0.05")  # widens count->reserve so a missing lock shows

        def go(p):
            r = subprocess.run([sys.executable, SCRIPT], input=p, capture_output=True, text=True, env=env, timeout=60)
            return json.loads(r.stdout.strip())

        with ThreadPoolExecutor(max_workers=8) as ex:
            outs = list(ex.map(go, payloads))
        allowed = [o for o in outs if o["action"] != "deny"]
        denied = [o for o in outs if o["action"] == "deny"]
        self.assertEqual((len(allowed), len(denied)), (5, 3), [o["action"] for o in outs])
        self.assertEqual(len(self.events("spawn_denied")), 3)


class PdTreeCapTests(Base):
    """Max 5 running Execs per ROOT PD across its whole tree (coords, mini-coords, direct Execs)."""

    def setUp(self):
        super().setUp()
        # PD P1 (test-pd) with two coords CA, CB (spawned by the PD)
        self.put(self.start("CA", parent="P1", typ="coord"), self.start("CB", parent="P1", typ="coord"))

    def ex(self, sid, coord):  # an Exec running under a coord (or under the PD when coord == "P1")
        return self.start(sid, parent=coord, pa="coord" if coord != "P1" else "test-pd")

    def spawn(self, coord, **kw):
        pa = "test-pd" if coord == "P1" else "coord"
        return self.run_pin(parent_spawn_id=coord, parent_agent=pa, model="sonnet", **kw)

    def slots_text(self):
        p = os.path.join(self.state, "spawn-slots.jsonl")
        if not os.path.exists(p):
            return ""
        with open(p) as f:
            return f.read().strip()

    def test_a_coords_3_plus_2_sixth_denied_from_either(self):
        self.put(*[self.ex("a%d" % i, "CA") for i in range(3)], *[self.ex("b%d" % i, "CB") for i in range(2)])
        for coord in ("CA", "CB"):
            o = self.spawn(coord, tool_use_id="tu-six-" + coord)
            self.assertEqual(o["action"], "deny", coord)
        rows = self.events("spawn_denied")
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["root"] for r in rows], ["pd:test-pd", "pd:test-pd"])
        self.assertEqual((rows[0]["running"], rows[0]["cap"], rows[0]["parent_spawn_id"]), (5, 5, "CA"))

    def test_b_three_plus_three_through_cli_exactly_sixth_denied(self):
        results = []
        for i, coord in enumerate(["CA"] * 3 + ["CB"] * 3):
            tu = "tu-seq-%d" % i
            o = self.spawn(coord, tool_use_id=tu)
            results.append(o["action"])
            if o["action"] != "deny":  # the spawn "happens": its spawn_start row lands in the ledger
                self.put(self.start("seq%d" % i, parent=coord, pa="coord", tool=tu))
        self.assertEqual(results, ["pass"] * 5 + ["deny"])

    def test_c_pd_direct_and_coord_execs_counted_together(self):
        self.put(*[self.ex("d%d" % i, "P1") for i in range(2)], *[self.ex("a%d" % i, "CA") for i in range(3)])
        self.assertEqual(self.spawn("CB")["action"], "deny")
        self.assertEqual(self.spawn("P1")["action"], "deny")

    def test_d_ended_execs_free_slots_by_spawn_id_and_agent_id(self):
        self.put(*[self.ex("a%d" % i, "CA") for i in range(3)], *[self.ex("b%d" % i, "CB") for i in range(2)])
        self.assertEqual(self.spawn("CA")["action"], "deny")
        self.put(self.end(sid="a0"))
        self.put(self.launched("b0", "agent-b0"), self.end(sid="", agent_id="agent-b0"))
        # 5 - 2 = 3 running: two more fit (reserving), the third is denied
        self.assertEqual(self.spawn("CB", tool_use_id="tu-n1")["action"], "pass")
        self.assertEqual(self.spawn("CA", tool_use_id="tu-n2")["action"], "pass")
        self.assertEqual(self.spawn("CA", tool_use_id="tu-n3")["action"], "deny")

    def test_e_two_different_pds_counted_separately(self):
        self.put(self.start("P2", parent="", typ="other-pd", pa="root"), self.start("CX", parent="P2", typ="coord", pa="other-pd"))
        self.put(*[self.ex("a%d" % i, "CA") for i in range(5)])
        self.assertEqual(self.spawn("CB")["action"], "deny")  # PD1 full
        o = self.run_pin(parent_spawn_id="CX", parent_agent="coord", model="sonnet")  # PD2 empty
        self.assertEqual(o["action"], "pass")

    def test_e2_respawned_pd_same_type_shares_budget(self):
        self.put(self.start("P1b", parent="", typ="test-pd", pa="root"), self.start("CC", parent="P1b", typ="coord", pa="test-pd"))
        self.put(*[self.ex("a%d" % i, "CA") for i in range(5)])
        self.assertEqual(self.spawn("CC")["action"], "deny")

    def test_f_coords_and_mini_coords_do_not_count(self):
        self.put(*[self.start("m%d" % i, parent="CA", typ="mini-coord", pa="coord") for i in range(4)],
                 *[self.start("c%d" % i, parent="P1", typ="coord", pa="test-pd") for i in range(4)])
        self.assertEqual(self.spawn("CA")["action"], "pass")
        self.put(*[self.ex("a%d" % i, "CA") for i in range(4)])  # 4 Execs + the reservation above = 5
        self.assertEqual(self.spawn("CB")["action"], "deny")

    def test_g_mini_coord_grandchild_chain_counts(self):
        self.put(self.start("MC", parent="CA", typ="mini-coord", pa="coord"))
        self.put(*[self.start("g%d" % i, parent="MC", pa="mini-coord") for i in range(5)])
        self.assertEqual(self.spawn("CB")["action"], "deny")
        # and an Exec spawned by that mini-coord is capped too
        o = self.run_pin(parent_spawn_id="MC", parent_agent="mini-coord", model="sonnet")
        self.assertEqual(o["action"], "deny")

    def test_h_no_pd_ancestor_fully_resolved_is_exempt(self):
        self.put(self.start("MC0", parent="", typ="coord", pa="root"))
        self.put(*[self.start("x%d" % i, parent="MC0", pa="coord") for i in range(9)])
        o = self.run_pin(parent_spawn_id="MC0", parent_agent="coord", model="sonnet")
        self.assertEqual(o["action"], "pass")
        self.assertEqual(self.events("model_pin_error"), [])
        self.assertEqual(self.slots_text(), "")  # no reservation for an exempt spawn

    def test_i_broken_chain_fails_open_with_one_error_row_and_still_rewrites(self):
        self.put(*[self.ex("a%d" % i, "CA") for i in range(5)])  # even a full PD tree does not matter
        o = self.run_pin(parent_spawn_id="GHOST", parent_agent="coord", model="opus")
        self.assertEqual((o["action"], o["model"]), ("rewrite", "sonnet"))  # the pin still applies
        errs = self.events("model_pin_error")
        self.assertEqual(len(errs), 1)
        self.assertIn("ancestry unresolved", errs[0]["error"])
        self.assertEqual(self.events("spawn_denied"), [])
        self.assertEqual(self.slots_text(), "")

    def test_i2_broken_chain_midway_fails_open(self):
        self.put(self.start("orph", parent="NOPE", typ="coord", pa="coord"))
        o = self.run_pin(parent_spawn_id="orph", parent_agent="coord", model="sonnet")
        self.assertEqual(o["action"], "pass")
        self.assertEqual(len(self.events("model_pin_error")), 1)

    def test_i3_cycle_fails_open(self):
        self.put(self.start("cy1", parent="cy2", typ="coord", pa="coord"), self.start("cy2", parent="cy1", typ="coord", pa="coord"))
        o = self.run_pin(parent_spawn_id="cy1", parent_agent="coord", model="sonnet")
        self.assertEqual(o["action"], "pass")
        self.assertEqual(len(self.events("model_pin_error")), 1)

    def test_j_reservation_is_per_root_parallel_race_two_coords(self):
        payloads = [json.dumps(self.payload(parent_spawn_id=("CA" if i % 2 == 0 else "CB"), parent_agent="coord",
                                            model="sonnet", tool_use_id="tu-prace-%d" % i)) for i in range(8)]
        env = self.env(MODEL_PIN_TEST_RACE_DELAY="0.05")

        def go(p):
            r = subprocess.run([sys.executable, SCRIPT], input=p, capture_output=True, text=True, env=env, timeout=60)
            return json.loads(r.stdout.strip())

        with ThreadPoolExecutor(max_workers=8) as ex:
            outs = list(ex.map(go, payloads))
        allowed = [o for o in outs if o["action"] != "deny"]
        self.assertEqual((len(allowed), len(outs) - len(allowed)), (5, 3), [o["action"] for o in outs])
        self.assertEqual(len(self.events("spawn_denied")), 3)
        for line in self.slots_text().splitlines():
            self.assertEqual(json.loads(line)["root"], "pd:test-pd")

    def test_j2_old_format_reservation_ignored(self):
        with open(os.path.join(self.state, "spawn-slots.jsonl"), "w") as f:
            for i in range(6):
                f.write(json.dumps({"parent_spawn_id": "CA", "tool_use_id": "old-%d" % i, "ts": NOW - 5}) + "\n")
        self.assertEqual(self.spawn("CA")["action"], "pass")

    def test_k_deny_message_names_pd_and_says_wait_for_a_slot(self):
        self.put(*[self.ex("a%d" % i, "CA") for i in range(5)])
        o = self.spawn("CB")
        self.assertEqual(o["action"], "deny")
        for frag in ("wait for a slot", "PD test-pd", "cap 5", "Exec cap policy"):
            self.assertIn(frag, o["deny"])

    def test_l_kill_switches_still_disable(self):
        self.put(*[self.ex("a%d" % i, "CA") for i in range(5)])
        self.assertEqual(self.spawn("CB")["action"], "deny")
        self.assertEqual(self.run_pin(env=self.env(SPAWN_CAP_OFF="1"), parent_spawn_id="CB", parent_agent="coord",
                                      model="sonnet")["action"], "pass")
        self.assertEqual(self.run_pin(env=self.env(MODEL_PIN_OFF="1"), parent_spawn_id="CB", parent_agent="coord",
                                      model="sonnet")["action"], "pass")
        open(os.path.join(self.state, "spawn-cap.off"), "w").close()
        self.assertEqual(self.spawn("CB")["action"], "pass")
        os.unlink(os.path.join(self.state, "spawn-cap.off"))
        open(os.path.join(self.state, "model-pin.off"), "w").close()
        self.assertEqual(self.spawn("CB")["action"], "pass")
        os.unlink(os.path.join(self.state, "model-pin.off"))
        with open(os.path.join(self.home, ".claude", ".hook-profile"), "w") as f:
            f.write("minimal\n")
        self.assertEqual(self.spawn("CB")["action"], "pass")

    def test_m_direct_pd_parent_agent_needs_no_pd_row(self):
        # payload parent_agent is a PD type -> root immediately, no ledger lookup of the parent needed
        self.put(*[self.start("z%d" % i, parent="PDX", pa="solo-pd") for i in range(5)])
        o = self.run_pin(parent_spawn_id="PDX", parent_agent="solo-pd", model="sonnet")
        self.assertEqual(o["action"], "deny")
        self.assertEqual(self.events("spawn_denied")[0]["root"], "pd:solo-pd")


class RealMapTests(unittest.TestCase):
    def test_shipped_map_is_valid_and_empty(self):
        with open(REAL_MAP) as f:
            m = json.load(f)
        self.assertEqual(m["default"], "sonnet")
        self.assertTrue(set(m["categories"]) >= {"lookup", "implement", "debug", "review", "research"})
        self.assertTrue(all(v == "" for v in m["categories"].values()))
        self.assertFalse(m["escalation"]["enabled"])
        self.assertEqual(m["escalation"]["allowed"], ["opus"])
        cap = m["exec_cap"]
        self.assertEqual((cap["enabled"], cap["max"], cap["include_root"], cap["stale_after_sec"]),
                         (True, 5, False, 7200))
        self.assertEqual(cap["types"], ["general-purpose", "task-executor"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

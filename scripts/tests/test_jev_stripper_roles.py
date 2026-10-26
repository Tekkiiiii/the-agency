"""JCR-2 tests for scripts/skill-route.py: boilerplate stripper, role-aware menu, families / agree_family.
NO network: the local counting stub (jev_stub.JevStub) stands in for Jev.

Run (repo root): python3 -m unittest discover -s scripts/tests -p 'test_jev_stripper_roles*' -v
Prompt fixtures below are synthesised from the SHAPES of real spawn prompts (task-executor, coord,
general-purpose "direct Exec", PD resume); names and task text are invented.
"""
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import jev_stub  # noqa: E402
import test_jev_router as tr  # noqa: E402  (RouterEnv, run_main, sr)

sr = tr.sr
RouterEnv = tr.RouterEnv
run_main = tr.run_main

# The eval seed is not shipped (scripts/skill-route/README.md): point JEV_TEST_SEED at your own seed.jsonl to run the
# "plain task texts are untouched" check; without it that one test is skipped.
SEED = os.environ.get("JEV_TEST_SEED")

# --------------------------------------------------------------------------- real-shaped prompts
EXEC_ACK = (
    "You are Exec-widget-Gadget, executing a sub-task for acme-project. [task:AC-2]\n"
    "You are a team member, not a contractor. Your spawner (Coord-acme-thing-Sprocket) is your technical lead. "
    "You MUST write an APPROACH request to your checkpoint file before any file edits, and a CHECKPOINT at ~50% "
    "effort, via the scratch-board file-poll handshake (not SendMessage). See ~/.claude/agents/specialized/"
    "task-executor.md §2b/3a and ~/.claude/runbooks/checkpoint-handshake-protocol.md. Tier: TIER_B.\n"
    "Checkpoint file: ~/.claude/projects/acme/memory/agents/execs/exec-widget-Gadget-checkpoint.md\n"
    "Scratch file: ~/.claude/projects/acme/memory/agents/executors/exec-AC2-Gadget-scratch.md\n"
    "Executor definition: ~/.claude/agents/specialized/task-executor.md — read it fully.\n"
    "Skills: /backend, /superpowers-test-driven-development.\n"
    "\n"
    "## Context (why)\n"
    "Add rate limiting to the webhook endpoint in api/hooks.ts so a burst of 500 calls cannot exhaust the "
    "database pool. Write the failing vitest first.\n"
    "\n"
    "## Report (final task result to Coord)\n"
    "DONE/BLOCKED line, then: design summary, fail-before and pass-after test output, files touched. "
    "Then archive your scratch file per task-executor.md and stop.\n"
)
EXEC_ACK_KEEP = ["rate limiting", "webhook endpoint", "api/hooks.ts", "failing vitest", "## Context (why)"]
EXEC_ACK_GONE = ["You are Exec-widget", "[task:AC-2]", "team member", "spawner", "APPROACH", "CHECKPOINT",
                 "Checkpoint file", "Scratch file", "Executor definition", "Tier: TIER_B", "Report (final",
                 "DONE/BLOCKED", "archive your scratch"]

EXEC_INLINE = (
    "[task:WK-1] You are Exec-docs-Snooze, executing a sub-task for acme-project (project root ~/.claude/"
    "projects/acme/, system root ~/.claude/).\n"
    "You are a team member, not a contractor. Your spawner (Coord-acme-Zed) is your technical lead.\n"
    "\n"
    "You have READ + WRITE + CREATE permission within your task scope.\n"
    "\n"
    "Your task (doc edits only): remove the ScheduleWakeup paragraph from skills/pd-resume/SKILL.md and "
    "rewrite runbooks/goal-wakeup-contract.md.\n"
    "\n"
    "Your Executor scratch file: ~/.claude/projects/acme/memory/agents/executors/exec-WK1-snooze-scratch.md "
    "— set it up now.\n"
    "Executor definition: ~/.claude/agents/specialized/task-executor.md — read it fully.\n"
    "\n"
    "Execute the task EXACTLY as given. Do NOT decompose further. If blocked, report BLOCKED. If an action "
    "exceeds scope, report ESCALATE.\n"
    "When done, report to Coord as your final task result: DONE \"[1-line summary]\" + exact list of files "
    "changed + the grep output. Then archive your scratch file and stop.\n"
)
EXEC_INLINE_KEEP = ["remove the ScheduleWakeup paragraph", "skills/pd-resume/SKILL.md",
                    "runbooks/goal-wakeup-contract.md"]
EXEC_INLINE_GONE = ["You are Exec-docs", "[task:WK-1]", "READ + WRITE", "team member", "scratch file",
                    "Executor definition", "EXACTLY as given", "decompose further", "When done, report",
                    "archive your scratch"]

COORD_HDR = (
    "Project: acme-project -- ~/.claude/projects/acme-project/\n"
    "System root: ~/.claude/\n"
    "You have full read/write/create access to the system directory and all subdirectories.\n"
    "Use Read, Edit, Write, Bash, Glob, Grep, Agent, SendMessage freely. No permission needed.\n"
    "Coord definition: ~/.claude/agents/project-management/coord.md -- read it fully.\n"
    "Scratch file: ~/.claude/projects/acme-project/memory/agents/coords/coord-acme-sprocket-scratch.md\n"
    "Set it up now. Decompose your L3 task, spawn Task-Executors in parallel, collect reports.\n"
    "\n"
    "Coord name: \"Sprocket\". Skills for Execs: /backend, /superpowers-test-driven-development.\n"
    "\n"
    "L3 TASK — Migrate the invoice export job from cron to a queue worker. Files in scope: jobs/export.ts, "
    "lib/queue.ts. Do not touch the billing schema.\n"
)
COORD_HDR_KEEP = ["Migrate the invoice export job", "jobs/export.ts", "Do not touch the billing schema",
                  "Coord name", "Skills for Execs"]
COORD_HDR_GONE = ["System root", "full read/write/create", "freely", "Coord definition", "Scratch file",
                  "Set it up now", "Project: acme-project"]

DIRECT_EXEC = (
    "You are a direct Exec (name for logs: Chain Gang) spawned by acme-pd. Project: acme-project. "
    "Skills: /superpowers-test-driven-development.\n"
    "\n"
    "TASK: two fixes to the granularity gate in scripts/gate.py: clamp the threshold and log the rejection reason.\n"
)
DIRECT_EXEC_KEEP = ["TASK: two fixes", "scripts/gate.py", "Skills: /superpowers-test-driven-development"]
DIRECT_EXEC_GONE = ["direct Exec", "spawned by", "name for logs", "Project: acme-project"]

NO_COORD = (
    "You are Exec-mirror-Ball, spawned directly by PD-acme (no Coord). Project: acme -- ~/.claude/projects/acme/. "
    "System root ~/.claude/ (git repo; do NOT commit).\n"
    "Sync the mirrored agent definitions under core/agents with the canonical ones.\n"
)
NO_COORD_KEEP = ["Sync the mirrored agent definitions", "core/agents", "git repo; do NOT commit"]
NO_COORD_GONE = ["You are Exec-mirror", "spawned directly", "Project: acme"]

NO_PERIOD = "You are Exec researching VN deck-copy writers\nCollect five public decks and note the title style."
PD_RESUME = (
    "You are PD-acme-api, resuming Acme API.\n"
    "Project: /home/x/projects/acme-api\n"
    "Tasks: /home/x/projects/acme-api/memory/tasks/ongoing/\n"
    "Inter-spawn tasks: /home/x/projects/acme-api/memory/inter-spawn-tasks/\n"
    "\n"
    "--- BRIEFING ---\n"
    "# acme-api\n"
    "Windows connect.ps1 untested (no pwsh on Mac)\n"
    "Pending inbound: none\n"
)
STACK_PROJECT = ("Project: /home/x/projects/acme-api (Next.js 15 + Supabase, vitest). Skills: /backend.\n"
                 "You implement ONE fix in lib/scripts/workerMjs.ts.\n")
EXEC_TIER = (
    "Audit the blast radius of the dept sunset across agents/ and runbooks/, read-only.\n"
    "Task tier: TIER_A (single output file, read-only elsewhere): APPROACH gate skipped \u2014 write a one-line "
    "\"starting\" note in your checkpoint file. CHECKPOINT at ~50% is still MANDATORY \u2014 write "
    "~/.claude/projects/acme/memory/agents/execs/exec-x-checkpoint.md.\n"
    "TIER_B. Poll it bounded (~5 min ceiling, per task-executor.md \u00a72b/3a and ~/.claude/runbooks/"
    "checkpoint-handshake-protocol.md); if no reply, proceed and mark APPROACH_UNREVIEWED.\n"
)
EXEC_TIER_KEEP = ["Audit the blast radius of the dept sunset", "agents/ and runbooks/"]
EXEC_TIER_GONE = ["TIER_A", "TIER_B", "APPROACH", "CHECKPOINT", "Poll it", "handshake"]
SKILLS_RESIDUE = (
    "Coord name: \"Trim Reaper\". Skills: , . Spec: revisions/2026-10-08-model-research.md items C3 and C4, "
    "read them fully before decomposing.\n"
)
PD_STD_PROTOCOL = (
    "Build the retry wrapper for the sync client in lib/sync.ts with exponential backoff.\n"
    "\n"
    "## PD Standard Protocol — NON-NEGOTIABLE\n"
    "Rule 1 — Decompose First: break every task into smallest independent sub-tasks.\n"
    "Rule 2 — Routing: run skill-route on each sub-task before spawning an Exec.\n"
    "\n"
    "## Scope\n"
    "Only lib/sync.ts and tests/sync.test.ts.\n"
)


def squash(s):
    return " ".join((s or "").split())


class StripBoilerplateTests(unittest.TestCase):
    def check(self, text, keep, gone):
        out = sr.strip_boilerplate(text)
        for k in keep:
            self.assertIn(k, out, "lost task content %r in:\n%s" % (k, out))
        for g in gone:
            self.assertNotIn(g, out, "boilerplate %r survived in:\n%s" % (g, out))
        return out

    def test_exec_ack_prompt(self):
        self.check(EXEC_ACK, EXEC_ACK_KEEP, EXEC_ACK_GONE)

    def test_exec_inline_prompt(self):
        self.check(EXEC_INLINE, EXEC_INLINE_KEEP, EXEC_INLINE_GONE)

    def test_coord_header(self):
        self.check(COORD_HDR, COORD_HDR_KEEP, COORD_HDR_GONE)

    def test_direct_exec_sentence_preamble(self):
        self.check(DIRECT_EXEC, DIRECT_EXEC_KEEP, DIRECT_EXEC_GONE)

    def test_spawned_directly_no_coord(self):
        self.check(NO_COORD, NO_COORD_KEEP, NO_COORD_GONE)

    def test_identity_line_without_period_keeps_task_words(self):
        out = self.check(NO_PERIOD, ["researching VN deck-copy writers", "five public decks"], ["You are Exec"])
        self.assertTrue(out.startswith("researching"))

    def test_pd_resume_drops_path_lines_keeps_briefing(self):
        out = self.check(PD_RESUME, ["--- BRIEFING ---", "Windows connect.ps1 untested", "Pending inbound: none"],
                         ["You are PD-acme-api", "Inter-spawn tasks", "/memory/tasks/ongoing/"])
        self.assertNotIn("Project: /Users", out)

    def test_project_path_stripped_but_stack_parenthetical_kept(self):
        out = self.check(STACK_PROJECT, ["Next.js 15 + Supabase, vitest", "lib/scripts/workerMjs.ts"],
                         ["/home/x/projects/acme-api"])
        self.assertIn("Skills: /backend", out)   # Skills lines are the shadow path's business, not the stripper's

    def test_tier_and_gate_lines(self):
        self.check(EXEC_TIER, EXEC_TIER_KEEP, EXEC_TIER_GONE)

    def test_empty_skills_residue_sentence_is_dropped(self):
        out = self.check(SKILLS_RESIDUE, ["Coord name", "Spec: revisions/2026-10-08-model-research.md"],
                         ["Skills:"])

    def test_pd_standard_protocol_section_removed_until_next_heading(self):
        out = self.check(PD_STD_PROTOCOL, ["retry wrapper", "lib/sync.ts", "## Scope", "tests/sync.test.ts"],
                         ["Standard Protocol", "Decompose First", "Routing"])
        self.assertIn("exponential backoff", out)

    def test_idempotent(self):
        for t in (EXEC_ACK, EXEC_INLINE, COORD_HDR, DIRECT_EXEC, NO_COORD, NO_PERIOD, PD_RESUME, STACK_PROJECT,
                  PD_STD_PROTOCOL, EXEC_TIER, SKILLS_RESIDUE):
            once = sr.strip_boilerplate(t)
            self.assertEqual(sr.strip_boilerplate(once), once)

    def test_floor_falls_back_to_original(self):
        only_bp = "You are Exec-a-B, executing a sub-task for p. [task:X]\nScratch file: ~/x/y.md\nSet it up now."
        self.assertEqual(sr.strip_boilerplate(only_bp), only_bp)
        self.assertGreaterEqual(sr.STRIP_FLOOR, 20)

    def test_non_string_and_empty_pass_through(self):
        self.assertEqual(sr.strip_boilerplate(""), "")
        self.assertEqual(sr.strip_boilerplate("   "), "   ")
        self.assertIsNone(sr.strip_boilerplate(None))

    def test_task_sentence_mentioning_scratch_or_approach_in_prose_survives(self):
        t = ("Rewrite the approach section of the README and explain the scratch directory layout "
             "to new contributors.")
        self.assertEqual(sr.strip_boilerplate(t), t)

    @unittest.skipUnless(SEED and os.path.isfile(SEED), "set JEV_TEST_SEED to a seed.jsonl to run")
    def test_seed_texts_are_a_noop(self):
        rows = []
        with open(SEED, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
        self.assertGreaterEqual(len(rows), 100)
        changed = [r["id"] for r in rows if squash(sr.strip_boilerplate(r["task"])) != squash(r["task"])]
        self.assertEqual(changed, [], "stripper altered plain seed tasks: %s" % changed)


class StripWiringTests(unittest.TestCase):
    """Wiring with SKILL_ROUTE_STRIP=1 (STRIP_ROUTED_TEXT True). The default is OFF, see StripDefaultOffTests."""

    def setUp(self):
        p = mock.patch.object(sr, "STRIP_ROUTED_TEXT", True)
        p.start()
        self.addCleanup(p.stop)

    def test_route_sends_stripped_text(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            res = sr.route(EXEC_ACK.replace("Add rate limiting", "Build a landing page"), log=False)
            state = e.stub.requests[0]["json"]["state"]
            self.assertIn("landing page", state)
            self.assertNotIn("team member", state)
            self.assertNotIn("Scratch file", state)
            self.assertEqual(res["router"], "jev")

    def test_plain_text_reaches_jev_unchanged(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            sr.route("Build a responsive landing page", log=False)
            self.assertEqual(e.stub.requests[0]["json"]["state"], "Build a responsive landing page")

    def test_cli_explicit_slash_token_in_boilerplate_free_text_still_passes_through(self):
        with RouterEnv() as e:
            rc, out, err = run_main(["--no-log", "use /frontend for the hero"])
            self.assertEqual(rc, 0)
            r = json.loads(out)
            self.assertEqual((r["router"], r["skills"]), ("passthrough", ["frontend"]))
            self.assertEqual(e.stub.count, 0)

    def test_shadow_strips_before_the_cap(self):
        pad = "".join("Coord definition: ~/.claude/agents/project-management/coord.md -- read it fully.\n"
                      for _ in range(60))   # ~5k chars of boilerplate: used to eat the whole 3000 cap
        self.assertGreater(len(pad), sr.SHADOW_TEXT_CAP)
        payload = json.dumps({"spawn_id": "s1", "subagent_type": "task-executor", "parent_agent": "coord",
                              "description": "Landing page", "prompt": pad + "Build a responsive hero section."})
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            run_main(["--shadow"], payload)
            state = e.stub.requests[0]["json"]["state"]
            self.assertIn("responsive hero section", state)
            self.assertNotIn("Coord definition", state)
            self.assertEqual(len(e.shadows()), 1)

    def test_shadow_skills_clause_removal_keeps_the_rest_of_the_line(self):
        """Real prompts open with `Skills: /x, /y. You are an Exec ... Task: ...` on ONE line; the old
        whole-line removal ate the task. Only the Skills clause (up to its sentence end) may go."""
        payload = json.dumps({"spawn_id": "s3", "subagent_type": "general-purpose", "parent_agent": "some-pd",
                              "description": "Hero section",
                              "prompt": "Skills: /frontend, tailwind. You are an Exec for acme (~/acme). "
                                        "Task: build a responsive hero section with a pricing table.\n"
                                        "Coord name: \"Zed\". Skills: /humanizer. Second sentence stays.\n"
                                        "Skills for Execs: /frontend, /tailwind\nLast line stays."})
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            run_main(["--shadow"], payload)
            state = e.stub.requests[0]["json"]["state"]
            self.assertIn("responsive hero section with a pricing table", state)
            self.assertIn("Second sentence stays", state)
            self.assertIn("Last line stays", state)
            self.assertNotIn("Skills:", state)
            self.assertNotIn("tailwind", state)
            self.assertNotIn("Skills for Execs", state)
            self.assertNotIn("You are an Exec", state)
            r = e.shadows()[0]
            self.assertEqual(r["actual_skills"], ["frontend", "tailwind", "humanizer"])


# --------------------------------------------------------------------------- roles
def add_skill(e, name, domain, desc, hint=None):
    d = os.path.join(e.skills_dir, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w") as fh:
        fh.write("---\nname: %s\ndescription: %s\n---\n# %s\n" % (name, desc, name))
    ov = tr.read_json(e.overlay)
    ov["skills"][name] = {"domain": domain}
    if hint:
        ov["skills"][name]["hint"] = hint
    tr.write_json(e.overlay, ov)


def set_overlay(e, **top):
    ov = tr.read_json(e.overlay)
    ov.update(top)
    tr.write_json(e.overlay, ov)


def role_env(**kw):
    """RouterEnv with `guard` + `freeze` skills added and role_excludes.exec = [guard, freeze]."""
    e = RouterEnv(**kw)
    return e


def setup_roles(e):
    add_skill(e, "guard", "code-quality-testing", "Full safety mode: destructive command warnings and directory-scoped edits.")
    add_skill(e, "freeze", "code-quality-testing", "Restrict file edits to a specific directory for the session.")
    add_skill(e, "backend", "code-quality-testing", "Build server-side APIs, databases and webhooks.")
    set_overlay(e, role_excludes={"exec": {"reason": "orchestration/safety toggles an Exec never needs",
                                           "skills": ["guard", "freeze"]}})


def all_criteria_keys(stub):
    keys = set()
    for r in stub.requests:
        for q in ((r["json"] or {}).get("questions") or {}).values():
            if isinstance(q.get("criteria"), dict):
                keys.update(q["criteria"].keys())
    return keys


class StripDefaultOffTests(unittest.TestCase):
    """JCR-2 replay (n=96 real spawns): stripping lowered Jev's gate=pass rate 35 -> 30 and top-1 by ~5 pts, so the
    routed text is the ORIGINAL unless SKILL_ROUTE_STRIP=1."""

    def test_default_flag_is_off(self):
        self.assertIs(sr.STRIP_ROUTED_TEXT, False)

    def test_route_sends_the_original_text_by_default(self):
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            sr.route(EXEC_ACK.replace("Add rate limiting", "Build a landing page"), log=False)
            state = e.stub.requests[0]["json"]["state"]
            self.assertIn("landing page", state)
            self.assertIn("team member", state)      # boilerplate stays when stripping is off

    def test_shadow_by_default_keeps_boilerplate_but_still_fixes_the_skills_clause(self):
        payload = json.dumps({"spawn_id": "s4", "subagent_type": "general-purpose", "parent_agent": "some-pd",
                              "description": "Hero section",
                              "prompt": "Skills: /frontend, tailwind. You are an Exec for acme (~/acme). "
                                        "Task: build a responsive hero section with a pricing table."})
        with RouterEnv(winners={"domain": "frontend-ui", "skill": "frontend"}) as e:
            run_main(["--shadow"], payload)
            state = e.stub.requests[0]["json"]["state"]
            self.assertIn("You are an Exec", state)
            self.assertIn("responsive hero section with a pricing table", state)
            self.assertNotIn("/frontend", state)

    def test_env_switch_turns_stripping_on(self):
        with mock.patch.dict(os.environ, {"SKILL_ROUTE_STRIP": "1"}):
            spec = importlib.util.spec_from_file_location("skill_route_strip_on", sr.__file__)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        self.assertIs(mod.STRIP_ROUTED_TEXT, True)


class RoleMenuTests(unittest.TestCase):
    def test_exec_role_never_returns_an_excluded_skill_even_when_jev_ranks_it_top(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
            setup_roles(e)
            res = sr.route("Harden the delete path before the migration runs", role="exec", log=False)
            self.assertNotIn("guard", res["skills"])
            self.assertNotIn("freeze", res["skills"])
            keys = all_criteria_keys(e.stub)
            self.assertNotIn("guard", keys)
            self.assertNotIn("freeze", keys)
            self.assertIn("backend", keys)

    def test_lead_and_none_role_can_still_return_the_skill(self):
        for role in (None, "lead"):
            with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
                setup_roles(e)
                res = sr.route("Harden the delete path before the migration runs", role=role, log=False)
                self.assertEqual(res["skills"][0], "guard", role)
                self.assertIn("guard", all_criteria_keys(e.stub))

    def test_flat_mode_and_grep_router_honour_the_role(self):
        with RouterEnv(winners={"skill": "guard"}) as e:
            setup_roles(e)
            res = sr.route("restrict file edits to a directory", mode="flat", role="exec", log=False)
            self.assertNotIn("guard", res["skills"])
            self.assertNotIn("guard", all_criteria_keys(e.stub))
            g_exec = sr.route("destructive command warnings directory-scoped edits safety mode",
                              router="grep", role="exec", log=False)
            g_lead = sr.route("destructive command warnings directory-scoped edits safety mode",
                              router="grep", role="lead", log=False)
            self.assertNotIn("guard", g_exec["skills"])
            self.assertIn("guard", g_lead["skills"])

    def test_default_module_role_is_no_filter(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
            setup_roles(e)
            self.assertEqual(sr.route("anything about safety", log=False)["skills"][0], "guard")

    def test_domain_question_drops_a_domain_emptied_by_the_role(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "frontend"}) as e:
            setup_roles(e)
            ov = tr.read_json(e.overlay)
            # make code-quality-testing contain ONLY the excluded skills
            ov["skills"]["backend"]["domain"] = "frontend-ui"
            ov["synthetic"]["code-review"]["domain"] = "frontend-ui"
            tr.write_json(e.overlay, ov)
            sr.route("Harden the delete path", role="exec", log=False)
            dom_q = tr.req_questions(e.stub, 0)["domain"]["criteria"]
            self.assertNotIn("code-quality-testing", dom_q)

    def test_role_excludes_naming_unknown_skill_raises_menu_error(self):
        with RouterEnv() as e:
            set_overlay(e, role_excludes={"exec": {"reason": "x", "skills": ["no-such-skill"]}})
            with self.assertRaises(sr.MenuError) as cm:      # strict (CI gate, gate check): a rename must update the overlay
                sr.load_menu(rebuild=True)
            self.assertIn("no-such-skill", str(cm.exception))
            # runtime is lenient: the name is dropped (and noted), the router keeps working
            menu = sr.load_menu(rebuild=True, strict=False)
            self.assertEqual(menu["role_excludes"], {"exec": []})
            self.assertEqual(menu["dropped"], ["role_excludes[exec]:no-such-skill"])
            sr.route("anything", role="exec", log=False)
            with self.assertRaises(sr.MenuError):            # a strict caller never gets the lenient cache
                sr.load_menu()

    def test_role_excludes_naming_an_overlay_excluded_skill_raises(self):
        with RouterEnv() as e:
            ov = tr.read_json(e.overlay)
            gone = [n for n, v in ov["skills"].items() if v.get("exclude")]
            self.assertTrue(gone, "fixture has an excluded skill")
            set_overlay(e, role_excludes={"exec": {"reason": "x", "skills": [gone[0]]}})
            with self.assertRaises(sr.MenuError):
                sr.load_menu(rebuild=True)

    def test_role_excludes_malformed_raises_menu_error(self):
        for bad in ([], {"exec": ["frontend"]}, {"exec": {"reason": "x", "skills": "frontend"}}):
            with RouterEnv() as e:
                set_overlay(e, role_excludes=bad)
                with self.assertRaises(sr.MenuError):
                    sr.load_menu(rebuild=True)

    def test_menu_carries_role_excludes_and_defaults_to_empty(self):
        with RouterEnv() as e:
            self.assertEqual(sr.load_menu(rebuild=True).get("role_excludes"), {})
            setup_roles(e)
            m = sr.load_menu(rebuild=True)
            self.assertEqual(sorted(m["role_excludes"]["exec"]), ["freeze", "guard"])
            self.assertIn("guard", m["skills"])   # the full menu is untouched

    def test_cli_default_role_is_exec_and_lead_flag_unfilters(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
            setup_roles(e)
            rc, out, _err = run_main(["--no-log", "Harden the delete path before the migration"])
            self.assertEqual(rc, 0)
            self.assertNotIn("guard", json.loads(out)["skills"])
            rc, out, _err = run_main(["--no-log", "--role", "lead", "Harden the delete path before the migration"])
            self.assertEqual(json.loads(out)["skills"][0], "guard")
            rc, out, _err = run_main(["--no-log", "--role", "exec", "Harden the delete path before the migration"])
            self.assertNotIn("guard", json.loads(out)["skills"])

    def test_cli_rejects_unknown_role(self):
        with RouterEnv() as e:
            rc, _out, _err = run_main(["--no-log", "--role", "boss", "x"])
            self.assertEqual(rc, 2)

    def test_explicit_slash_passthrough_is_not_filtered_by_role(self):
        with RouterEnv() as e:
            setup_roles(e)
            rc, out, _err = run_main(["--no-log", "run /guard while I clean the table"])   # default role exec
            r = json.loads(out)
            self.assertEqual((r["router"], r["skills"]), ("passthrough", ["guard"]))
            self.assertEqual(e.stub.count, 0)
            res = sr.route("run /freeze for this edit", role="exec", log=False)
            self.assertEqual(res["skills"], ["freeze"])

    def test_decision_log_records_role(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "backend"}) as e:
            setup_roles(e)
            run_main(["--role", "exec", "Build the webhook handler"])
            sr.route("Build the webhook handler", log=True)   # module default: role None
            recs = e.decisions()
            self.assertEqual(recs[0]["role"], "exec")
            self.assertIn(recs[1]["role"], (None, "lead"))

    def test_role_for_subagent_type(self):
        for t in ("task-executor", "general-purpose", "", None):
            self.assertEqual(sr.role_for_subagent(t), "exec", t)
        for t in ("coord", "mini-coord", "pd-coordinator", "demo-project-pd", "acme-ops-pd",
                  "dept-head-eng", "critique-design", "codebase-search"):
            self.assertEqual(sr.role_for_subagent(t), "lead", t)


class ShadowRoleTests(unittest.TestCase):
    def payload(self, **kw):
        d = {"spawn_id": "sp-r", "subagent_type": "task-executor", "parent_agent": "coord",
             "description": "Harden the delete path",
             "prompt": "Skills: /guard, /backend\nHarden the delete path before the migration runs."}
        d.update(kw)
        return json.dumps(d)

    def test_exec_shadow_filters_menu_but_actual_skills_use_the_full_menu(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
            setup_roles(e)
            run_main(["--shadow"], self.payload())
            r = e.shadows()[0]
            self.assertEqual(r["role"], "exec")
            self.assertEqual(r["actual_skills"], ["guard", "backend"])      # guard survives in the truth
            self.assertNotIn("guard", r["router_skills"])
            self.assertNotIn("guard", all_criteria_keys(e.stub))

    def test_lead_shadow_is_unfiltered_and_role_recorded(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "guard"}) as e:
            setup_roles(e)
            run_main(["--shadow"], self.payload(subagent_type="coord", spawn_id="sp-l"))
            r = e.shadows()[0]
            self.assertEqual(r["role"], "lead")
            self.assertEqual(r["router_skills"][0], "guard")
            self.assertTrue(r["agree_top1"])

    def test_shadow_record_has_agree_family(self):
        with RouterEnv(winners={"domain": "code-quality-testing", "skill": "freeze"}) as e:
            setup_roles(e)
            set_overlay(e, families={"safety": ["guard", "freeze"]})
            run_main(["--shadow"], self.payload(subagent_type="coord",
                                                prompt="Skills: /guard\nHarden the delete path."))
            r = e.shadows()[0]
            self.assertEqual(r["router_skills"][0], "freeze")
            self.assertFalse(r["agree_any"])
            self.assertTrue(r["agree_family"])

    def test_shadow_agree_family_is_none_without_actual(self):
        with RouterEnv() as e:
            run_main(["--shadow"], self.payload(prompt="no skills named here"))
            self.assertIsNone(e.shadows()[0]["agree_family"])


# --------------------------------------------------------------------------- families
class FamilyAgreeTests(unittest.TestCase):
    FAM = {"ui": ["frontend", "ui-ux-pro-max", "design-taste-frontend"], "sb": ["supabase-sql", "supabase-deploy"]}

    def test_exact_overlap_counts(self):
        self.assertTrue(sr.family_agree(["backend"], ["backend", "security"], self.FAM))

    def test_shared_family_counts(self):
        self.assertTrue(sr.family_agree(["ui-ux-pro-max"], ["design-taste-frontend"], self.FAM))
        self.assertTrue(sr.family_agree(["supabase-deploy"], ["backend", "supabase-sql"], self.FAM))
        self.assertTrue(sr.family_agree(["backend", "ui-ux-pro-max"], ["frontend"], self.FAM))   # any router skill

    def test_different_families_do_not_agree(self):
        self.assertFalse(sr.family_agree(["ui-ux-pro-max"], ["supabase-sql"], self.FAM))
        self.assertFalse(sr.family_agree(["backend"], ["security"], self.FAM))

    def test_empty_and_missing_inputs(self):
        self.assertFalse(sr.family_agree([], ["frontend"], self.FAM))
        self.assertFalse(sr.family_agree(["frontend"], [], self.FAM))
        self.assertFalse(sr.family_agree(None, None, None))
        self.assertTrue(sr.family_agree(["frontend"], ["frontend"], None))   # no families -> plain overlap

    def test_same_domain_is_not_a_family(self):
        self.assertFalse(sr.family_agree(["tailwind"], ["frontend"], self.FAM))


class FamilyMenuTests(unittest.TestCase):
    def test_families_validated_against_menu(self):
        with RouterEnv() as e:
            set_overlay(e, families={"ui": ["frontend", "tailwind"]})
            self.assertEqual(sr.load_menu(rebuild=True)["families"], {"ui": ["frontend", "tailwind"]})
            set_overlay(e, families={"ui": ["frontend", "ghost-skill"]})
            with self.assertRaises(sr.MenuError) as cm:
                sr.load_menu(rebuild=True)
            self.assertIn("ghost-skill", str(cm.exception))
            self.assertEqual(sr.load_menu(rebuild=True, strict=False)["families"], {"ui": ["frontend"]})   # lenient: dropped
            set_overlay(e, families={"ui": "frontend"})
            with self.assertRaises(sr.MenuError):
                sr.load_menu(rebuild=True)
            set_overlay(e, families={})
            self.assertEqual(sr.load_menu(rebuild=True)["families"], {})

    def test_real_overlay_roles_and_families_are_wired(self):
        """The shipped overlay: role_excludes.exec lists only skills the repo ships, families have >= 2 members and
        the strict loader accepts both (the CI menu gate builds the real menu)."""
        path = os.path.join(SCRIPTS, "skill-route", "overlay.json")
        with open(path) as fh:
            ov = json.load(fh)
        ex = ov["role_excludes"]["exec"]
        self.assertTrue(ex["reason"])
        self.assertEqual(sorted(ex["skills"]), sorted([
            "superpowers-subagent-driven-development", "superpowers-dispatching-parallel-agents", "guard",
            "freeze", "careful", "unfreeze"]))
        self.assertNotIn("swarm", ex["skills"])
        self.assertNotIn("skill-tracker", ex["skills"])
        for name, members in ov["families"].items():
            self.assertGreaterEqual(len(members), 2, name)
        self.assertIn("supabase-sql", ov["families"]["supabase"])


class ShadowReportTests(unittest.TestCase):
    def test_report_family_and_low_confidence_lines_computed_on_the_fly_for_old_records(self):
        with RouterEnv() as e:
            set_overlay(e, families={"ui": ["frontend", "tailwind"]})
            old = [   # legacy records: no agree_family / role fields
                {"ts": "2026-10-07T01:00:00Z", "router": "jev", "gate": "pass", "actual_skills": ["frontend"],
                 "router_skills": ["frontend"], "agree_top1": True, "agree_any": True},
                {"ts": "2026-10-07T01:01:00Z", "router": "jev", "gate": "low_confidence",
                 "actual_skills": ["frontend"], "router_skills": ["tailwind"], "agree_top1": False,
                 "agree_any": False},
                {"ts": "2026-10-07T01:02:00Z", "router": "jev", "gate": "low_confidence",
                 "actual_skills": ["humanizer"], "router_skills": ["frontend"], "agree_top1": False,
                 "agree_any": False},
                {"ts": "2026-10-07T01:03:00Z", "router": "jev", "gate": "pass", "actual_skills": [],
                 "router_skills": ["frontend"], "agree_top1": None, "agree_any": None},
            ]
            with open(e.shadow_log, "w") as fh:
                for r in old:
                    fh.write(json.dumps(r) + "\n")
            rc, out, _err = run_main(["--shadow-report"])
            self.assertEqual(rc, 0)
            self.assertIn("top-1 agreement: 33.3% (1/3)", out)       # strict lines unchanged
            self.assertIn("any agreement:   33.3% (1/3)", out)
            self.assertIn("family agreement: 66.7% (2/3)", out)
            self.assertIn("low_confidence rate: 50.0% (2/4)", out)

    def test_report_with_no_records(self):
        with RouterEnv() as e:
            rc, out, _err = run_main(["--shadow-report"])
            self.assertIn("family agreement: n/a", out)
            self.assertIn("low_confidence rate: n/a", out)


if __name__ == "__main__":
    unittest.main()

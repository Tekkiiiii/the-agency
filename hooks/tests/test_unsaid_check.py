#!/usr/bin/env python3
"""Tests for scripts/unsaid_check.py (core) and hooks/unsaid-check.sh (PreToolUse wrapper).

Pure fixtures + temp HOME for the wrapper; the real logs and transcripts are never touched.
Run: python3 -m unittest discover -s hooks/tests -p 'test_unsaid_check.py'
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
spec = importlib.util.spec_from_file_location("unsaid_check", os.path.join(ROOT, "scripts", "unsaid_check.py"))
uc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uc)
HOOK = os.path.join(ROOT, "hooks", "unsaid-check.sh")

USER_TEXT = ("Q1: ok, design our system like a nesting doll, one screen, "
         "new relevant buttons appear as I enter deeper into a menu")

REV3 = """# Revision 3: UI structure directive (2026-10-23)
Source: the user in the main session, verbatim. Applies to the dashboard UI plan and every phase built from it.

User verbatim: "Q1: ok, design our system like a nesting doll, one screen, new relevant buttons appear as I enter deeper into a menu"

Binding (do not reword when passing to Coords/Execs; copy the verbatim line above):
- Everything happens on one screen. No page or tab switching.
- Nesting-doll depth: each level opens inside the current one.
- The buttons/actions shown are the ones relevant to the current depth. New actions appear as the user goes deeper.
- Replaces the 7-tab layout. v3 stays the visual skin only (rev2).

Plan update needed: a depth map (levels and what opens inside what). Add it to plan.html before any Phase 1 UI work.
"""


def flagged_lines(flags):
    return [f["line"] for f in flags]


class CheckTests(unittest.TestCase):
    def test_rev3_flags_replaces_line_rule_a(self):
        flags = uc.check(REV3, USER_TEXT)
        hit = [f for f in flags if "Replaces the 7-tab layout" in f["line"]]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["rule"], "A")
        self.assertIn("replace", hit[0]["reason"].lower())

    def test_rev3_does_not_flag_verbatim_or_heading_or_source(self):
        for f in uc.check(REV3, USER_TEXT):
            self.assertFalse(f["line"].startswith("User verbatim"))
            self.assertFalse(f["line"].startswith("#"))
            self.assertFalse(f["line"].startswith("Source:"))

    def test_sendmessage_fixture_flagged(self):
        flags = uc.check("This replaces the 7 tabs.", USER_TEXT)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["rule"], "A")

    def test_assumption_label_not_flagged(self):
        brief = "- Assumption: replaces the 7-tab layout\n- Question: should we drop the tabs?"
        self.assertEqual(uc.check(brief, USER_TEXT), [])

    def test_struck_and_main_session_addition_exempt(self):
        self.assertEqual(uc.check("- [STRUCK] replaces tabs\n- Main-session addition: never use tabs", USER_TEXT), [])

    def test_corpus_with_replace_not_flagged(self):
        flags = uc.check("- Replaces the 7-tab layout.", USER_TEXT + "\nplease replace the tabs")
        self.assertEqual(flags, [])

    def test_quoted_span_not_rule_a(self):
        self.assertEqual(uc.check('The button says "never again" in red.', USER_TEXT), [])

    def test_rule_c_fabricated_quote(self):
        flags = uc.check('User verbatim: "remove the tabs"', USER_TEXT)
        self.assertEqual([f["rule"] for f in flags], ["C"])

    def test_rule_c_exact_quote_ok_with_normalisation(self):
        brief = 'User verbatim: “Q1: ok,  design our system like a nesting doll, one screen”'
        self.assertEqual(uc.check(brief, USER_TEXT), [])

    def test_rule_c_user_colon_form(self):
        flags = uc.check('User: "delete everything"', USER_TEXT)
        self.assertEqual([f["rule"] for f in flags], ["C"])

    def test_rule_c_user_said_form(self):
        flags = uc.check('The user said "remove the tabs" earlier.', USER_TEXT)
        self.assertEqual([f["rule"] for f in flags], ["C"])
        self.assertEqual(uc.check('The user said "one screen" earlier.', USER_TEXT), [])

    def test_name_free_attribution_not_matched(self):
        self.assertEqual(uc.check('Alex verbatim: "remove the tabs"', USER_TEXT), [])

    def test_rule_b_only_strict(self):
        brief = "Implement quarterly invoice reconciliation pipeline using postgres triggers."
        self.assertEqual(uc.check(brief, USER_TEXT), [])
        self.assertTrue(any(f["rule"] == "B" for f in uc.check(brief, USER_TEXT, strict=True)))


class ExtractTests(unittest.TestCase):
    def test_bash_heredoc_revisions(self):
        cmd = "cat > /p/memory/inter-spawn-tasks/revisions/rev3.md <<'EOF'\nline one\nReplaces tabs\nEOF\nls"
        self.assertEqual(uc.extract_brief("Bash", {"command": cmd}), "line one\nReplaces tabs")

    def test_bash_ls_none(self):
        self.assertIsNone(uc.extract_brief("Bash", {"command": "ls inter-spawn-tasks"}))
        self.assertIsNone(uc.extract_brief("Bash", {"command": "ls"}))

    def test_write_other_path_none(self):
        self.assertIsNone(uc.extract_brief("Write", {"file_path": "/tmp/x.md", "content": "hi"}))

    def test_write_revisions_and_edit_incoming(self):
        self.assertEqual(uc.extract_brief("Write", {"file_path": "/a/inter-spawn-tasks/revisions/r.md", "content": "c"}), "c")
        self.assertEqual(uc.extract_brief("Edit", {"file_path": "/a/inter-spawn-tasks/incoming/r.md", "new_string": "n"}), "n")

    def test_sendmessage_and_agent(self):
        self.assertEqual(uc.extract_brief("SendMessage", {"to": "x", "message": "hello"}), "hello")
        self.assertIsNone(uc.extract_brief("SendMessage", {"to": "x", "message": {"type": "shutdown"}}))
        self.assertEqual(uc.extract_brief("Agent", {"subagent_type": "example-pd", "prompt": "p"}), "p")
        self.assertEqual(uc.extract_brief("Agent", {"subagent_type": "pd-coordinator", "prompt": "p"}), "p")
        self.assertIsNone(uc.extract_brief("Agent", {"subagent_type": "general-purpose", "prompt": "p"}))


def jl(entries):
    return "\n".join(json.dumps(e) for e in entries) + "\n"


def user(content, **kw):
    d = {"type": "user", "message": {"role": "user", "content": content}}
    d.update(kw)
    return d


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="unsaid-test-")
        self.path = os.path.join(self.tmp, "t.jsonl")

    def write(self, entries):
        with open(self.path, "w") as f:
            f.write(jl(entries))

    def test_exclusions_and_inclusions(self):
        self.write([
            user("real text one"),
            user("meta text", isMeta=True),
            user([{"type": "tool_result", "tool_use_id": "x", "content": "toolresult text"}]),
            user([{"type": "text", "text": "list text two"}]),
            user("Base directory for this skill: /x\nskillbody", isMeta=True),
            user("Another Claude session sent a message: <agent-message from=\"a\">hello agentmsg"),
            user("<agent-message from=\"a\">agentmsg2</agent-message>"),
            user("<task-notification>tasknote</task-notification>"),
            user("<local-command-caveat>caveat</local-command-caveat>"),
            user("<command-message>recall</command-message> <command-name>/recall</command-name> <command-args>si args</command-args>"),
            user("keep <system-reminder>REMINDER</system-reminder> this"),
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "assistant text"}]}},
        ])
        c = uc.user_corpus(self.path)
        for want in ("real text one", "list text two", "si args", "keep", "this"):
            self.assertIn(want, c)
        for bad in ("meta text", "toolresult", "skillbody", "agentmsg", "hello", "tasknote", "caveat",
                    "/recall", "REMINDER", "assistant text"):
            self.assertNotIn(bad, c)

    def test_upto_line(self):
        self.write([user("first msg"), user("second msg")])
        self.assertIn("first msg", uc.user_corpus(self.path, upto_line=1))
        self.assertNotIn("second msg", uc.user_corpus(self.path, upto_line=1))


class CliReplayTests(unittest.TestCase):
    def test_replay_line(self):
        tmp = tempfile.mkdtemp(prefix="unsaid-test-")
        p = os.path.join(tmp, "t.jsonl")
        cmd = "cat > /p/inter-spawn-tasks/revisions/r.md <<'EOF'\n- Replaces the 7-tab layout.\nEOF"
        with open(p, "w") as f:
            f.write(jl([user(USER_TEXT),
                        {"type": "assistant", "message": {"content": [
                            {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}]))
        r = subprocess.run(["python3", os.path.join(ROOT, "scripts", "unsaid_check.py"),
                            "--transcript", p, "--replay-line", "1"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn('UNSAID L1 [A:replace] "- Replaces the 7-tab layout."', r.stdout)


class HookTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="unsaid-home-")
        os.makedirs(os.path.join(self.home, ".claude", "logs"))
        self.transcript = os.path.join(self.home, "t.jsonl")
        with open(self.transcript, "w") as f:
            f.write(jl([user(USER_TEXT)]))

    def run_hook(self, payload):
        env = dict(os.environ, HOME=self.home, USERPROFILE=self.home)
        env.pop("AGENCY_HOME", None)
        env.pop("CLAUDE_CONFIG_DIR", None)
        r = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def base(self, tool, ti, **kw):
        d = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti, "transcript_path": self.transcript}
        d.update(kw)
        return d

    def test_subagent_passes(self):
        out = self.run_hook(self.base("SendMessage", {"to": "x", "message": "This replaces the 7 tabs."}, agent_id="abc"))
        self.assertEqual(out, {})

    def test_plain_bash_passes(self):
        self.assertEqual(self.run_hook(self.base("Bash", {"command": "ls -la"})), {})

    def test_flag_emits_additional_context_only(self):
        out = self.run_hook(self.base("SendMessage", {"to": "x", "message": "This replaces the 7 tabs."}))
        h = out["hookSpecificOutput"]
        self.assertEqual(h["hookEventName"], "PreToolUse")
        self.assertIn("UNSAID-CHECK", h["additionalContext"])
        self.assertNotIn("permissionDecision", h)
        self.assertNotIn("permissionDecision", out)
        log = os.path.join(self.home, ".claude", "logs", "unsaid-check.jsonl")
        self.assertTrue(os.path.exists(log))
        self.assertEqual(json.loads(open(log).readline())["tool"], "SendMessage")

    def test_clean_brief_passes(self):
        self.assertEqual(self.run_hook(self.base("SendMessage", {"to": "x", "message": "Please build the nesting doll screen."})), {})

    def test_bad_input_fails_open(self):
        env = dict(os.environ, HOME=self.home)
        env.pop("AGENCY_HOME", None)
        env.pop("CLAUDE_CONFIG_DIR", None)
        r = subprocess.run(["bash", HOOK], input="not json", capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(r.stdout), {})

    def test_minimal_profile_passes(self):
        with open(os.path.join(self.home, ".claude", ".hook-profile"), "w") as f:
            f.write("minimal\n")
        self.assertEqual(self.run_hook(self.base("SendMessage", {"to": "x", "message": "This replaces the 7 tabs."})), {})


if __name__ == "__main__":
    unittest.main()

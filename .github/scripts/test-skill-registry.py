#!/usr/bin/env python3
"""Tests for scripts/skill-registry.py (generated skills/INDEX.md + ratcheting skill lint).

Stdlib only (unittest), no network, no repo state: every test builds a scratch agency root in a temp dir and
drives the real CLI through a subprocess, so what passes here is what CI and a contributor's shell will see.
Runs on Linux, macOS and Windows runners.

  python3 .github/scripts/test-skill-registry.py          (add -v for one line per test)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(REPO, "scripts", "skill-registry.py")

OVERLAY = {
    "domains": {"alpha": "Alpha things: first domain.", "beta": "Beta things: second domain."},
    "skills": {
        "one": {"domain": "alpha"},
        "two": {"domain": "beta"},
        "three": {"domain": "alpha"},
        "secret": {"exclude": "internal", "why": "loaded by hand only"},
    },
}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def skill(root, name, description="Use when testing " + "x", body="# Body\n\nSome text.\n", extra_fm="", raw=None):
    text = raw if raw is not None else "---\nname: %s\ndescription: \"%s\"\n%s---\n%s" % (name, description, extra_fm, body)
    write(os.path.join(root, "skills", name, "SKILL.md"), text)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="skillreg-")
        write(os.path.join(self.root, "scripts", "skill-route", "overlay.json"), json.dumps(OVERLAY))
        write(os.path.join(self.root, "scripts", "skill-registry", "header.md"), "# Skills Index\n\nHand-kept header.\n")
        write(os.path.join(self.root, "scripts", "skill-registry", "footer.md"), "## Footer\n\nHand-kept footer.\n")
        self.baseline = os.path.join(self.root, "scripts", "skill-registry", "lint-baseline.json")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_tool(self, *args):
        p = subprocess.run([sys.executable, TOOL, "--root", self.root] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return p.returncode, p.stdout, p.stderr

    def index(self):
        with open(os.path.join(self.root, "skills", "INDEX.md"), encoding="utf-8") as fh:
            return fh.read()


class RegistryTests(Base):
    def test_writes_domain_tables_header_and_footer(self):
        skill(self.root, "one", "Use when alpha one")
        skill(self.root, "two", "Use when beta two")
        skill(self.root, "three", "Use when alpha three")
        skill(self.root, "secret", "Use when internal")
        rc, _, err = self.run_tool()
        self.assertEqual(rc, 0, err)
        md = self.index()
        self.assertTrue(md.startswith("# Skills Index\n\nHand-kept header."))
        self.assertTrue(md.rstrip().endswith("Hand-kept footer."))
        self.assertLess(md.index("## alpha"), md.index("## beta"))
        alpha = md[md.index("## alpha"):md.index("## beta")]
        self.assertIn("| `one` | Use when alpha one |", alpha)
        self.assertIn("| `three` | Use when alpha three |", alpha)
        self.assertLess(alpha.index("`one`"), alpha.index("`three`"))  # sorted by name
        self.assertIn("Alpha things: first domain.", alpha)
        self.assertIn("| `two` | Use when beta two |", md)
        # an excluded skill is still listed (INDEX.md is the menu when the router is off), with its reason
        self.assertIn("| `secret` | internal: loaded by hand only |", md)

    def test_regenerating_twice_is_identical(self):
        skill(self.root, "one")
        skill(self.root, "two")
        self.assertEqual(self.run_tool()[0], 0)
        first = self.index()
        path = os.path.join(self.root, "skills", "INDEX.md")
        m1 = os.stat(path).st_mtime_ns
        self.assertEqual(self.run_tool()[0], 0)
        self.assertEqual(self.index(), first)
        self.assertEqual(os.stat(path).st_mtime_ns, m1, "an unchanged registry must not be rewritten")
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_output_does_not_depend_on_directory_listing_order_or_clock(self):
        for n in ("two", "one", "three"):
            skill(self.root, n)
        self.run_tool()
        a = self.index()
        shutil.rmtree(os.path.join(self.root, "skills", "one"))
        skill(self.root, "one")  # recreated last: different mtime and creation order
        self.run_tool()
        self.assertEqual(self.index(), a)

    def test_skill_without_frontmatter_is_still_listed(self):
        skill(self.root, "one", raw="# One\n\nDoes the first thing for you.\n\nSecond paragraph.\n")
        self.assertEqual(self.run_tool()[0], 0)
        md = self.index()
        self.assertIn("| `one` | Does the first thing for you. |", md)

    def test_skill_with_empty_body_and_no_frontmatter_is_listed(self):
        skill(self.root, "one", raw="")
        self.assertEqual(self.run_tool()[0], 0)
        self.assertIn("| `one` |", self.index())

    def test_unclosed_frontmatter_is_listed_not_fatal(self):
        skill(self.root, "one", raw="---\nname: one\ndescription: oops\n# never closed\n")
        rc, _, err = self.run_tool()
        self.assertEqual(rc, 0, err)
        self.assertIn("`one`", self.index())

    def test_unrouted_skill_gets_its_own_table(self):
        skill(self.root, "one")
        skill(self.root, "stray", "Use when stray")
        self.assertEqual(self.run_tool()[0], 0)
        md = self.index()
        self.assertIn("## Unrouted", md)
        self.assertIn("| `stray` | Use when stray |", md[md.index("## Unrouted"):])

    def test_dirs_without_skill_md_or_underscore_prefixed_are_skipped(self):
        skill(self.root, "one")
        os.makedirs(os.path.join(self.root, "skills", "empty-dir"))
        skill(self.root, "_hidden", "Use when hidden")
        write(os.path.join(self.root, "skills", "README.md"), "not a skill\n")
        self.assertEqual(self.run_tool()[0], 0)
        md = self.index()
        self.assertNotIn("empty-dir", md)
        self.assertNotIn("_hidden", md)

    def test_folded_and_quoted_multiline_descriptions(self):
        skill(self.root, "one", raw="---\nname: one\ndescription: >\n  Use when the\n  folded one\n---\nbody\n")
        skill(self.root, "two", raw="---\nname: two\ndescription: \"Use when the quoted\n  one wraps\"\n---\nbody\n")
        self.assertEqual(self.run_tool()[0], 0)
        md = self.index()
        self.assertIn("| `one` | Use when the folded one |", md)
        self.assertIn("| `two` | Use when the quoted one wraps |", md)

    def test_pipes_are_escaped_and_long_descriptions_are_cut_on_a_word(self):
        skill(self.root, "one", "Use when a|b " + "word " * 80)
        self.assertEqual(self.run_tool()[0], 0)
        row = [l for l in self.index().splitlines() if l.startswith("| `one`")][0]
        self.assertIn("a\\|b", row)
        self.assertTrue(row.endswith("... |"), row)
        self.assertLess(len(row), 200)

    def test_crlf_skill_file_parses(self):
        write(os.path.join(self.root, "skills", "one", "SKILL.md"), "x")
        with open(os.path.join(self.root, "skills", "one", "SKILL.md"), "wb") as fh:
            fh.write(b"---\r\nname: one\r\ndescription: Use when crlf\r\n---\r\nbody\r\n")
        self.assertEqual(self.run_tool()[0], 0)
        self.assertIn("| `one` | Use when crlf |", self.index())

    def test_check_fails_on_stale_index_and_passes_after_write(self):
        skill(self.root, "one")
        self.assertEqual(self.run_tool("--check")[0], 1, "no INDEX.md yet is stale")
        self.assertFalse(os.path.exists(os.path.join(self.root, "skills", "INDEX.md")), "--check must not write")
        self.run_tool()
        self.assertEqual(self.run_tool("--check")[0], 0)
        skill(self.root, "two")
        rc, out, err = self.run_tool("--check")
        self.assertEqual(rc, 1)
        self.assertIn("skill-registry.py", out + err)  # tells the contributor how to fix it
        self.run_tool()
        self.assertEqual(self.run_tool("--check")[0], 0)

    def test_check_ignores_crlf_checkout_of_index(self):
        skill(self.root, "one")
        self.run_tool()
        p = os.path.join(self.root, "skills", "INDEX.md")
        with open(p, "rb") as fh:
            data = fh.read()
        with open(p, "wb") as fh:
            fh.write(data.replace(b"\n", b"\r\n"))
        self.assertEqual(self.run_tool("--check")[0], 0, "autocrlf checkouts must not read as stale")

    def test_overlay_names_not_on_disk_warn_but_do_not_fail(self):
        skill(self.root, "one")
        rc, _, err = self.run_tool()
        self.assertEqual(rc, 0)
        self.assertIn("WARN", err)

    def test_missing_overlay_lists_everything_unrouted(self):
        os.remove(os.path.join(self.root, "scripts", "skill-route", "overlay.json"))
        skill(self.root, "one")
        rc, _, err = self.run_tool()
        self.assertEqual(rc, 0, err)
        self.assertIn("## Unrouted", self.index())

    def test_output_has_no_count_or_machine_paths(self):
        for n in ("one", "two", "three"):
            skill(self.root, n)
        self.run_tool()
        md = self.index()
        self.assertNotIn(self.root, md)
        self.assertNotRegex(md, r"\b\d+\s+(reusable\s+)?skills\b")


class LintTests(Base):
    def lint(self, *args):
        return self.run_tool("--lint", "--baseline", self.baseline, *args)

    def test_clean_tree_passes(self):
        skill(self.root, "one")
        rc, out, err = self.lint()
        self.assertEqual(rc, 0, out + err)
        self.assertIn("OK", out)

    def test_new_violation_fails_with_lint_fail_line(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        rc, out, _ = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("LINT FAIL one description>400", out)

    def test_baselined_violation_passes_and_a_second_new_one_fails(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        self.assertEqual(self.lint("--update-baseline")[0], 0)
        with open(self.baseline, encoding="utf-8") as fh:
            self.assertIn("one:description>400", json.load(fh)["violations"])
        rc, out, _ = self.lint()
        self.assertEqual(rc, 0, "an existing violation passes")
        skill(self.root, "two", "Use when " + "y" * 450)
        rc, out, _ = self.lint()
        self.assertEqual(rc, 1, "a new violation in another skill fails")
        self.assertIn("LINT FAIL two description>400", out)
        self.assertNotIn("LINT FAIL one", out)

    def test_existing_violation_getting_worse_in_a_new_rule_fails(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        self.lint("--update-baseline")
        skill(self.root, "one", "Use when " + "x" * 450, body="line\n" * 600)
        rc, out, _ = self.lint()
        self.assertEqual(rc, 1)
        self.assertIn("LINT FAIL one body-lines>500", out)

    def test_fixed_baseline_entries_are_reported_and_removable(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        self.lint("--update-baseline")
        skill(self.root, "one", "Use when short")
        rc, out, _ = self.lint()
        self.assertEqual(rc, 0)
        self.assertIn("LINT FIXED", out)
        self.assertIn("one:description>400", out)
        self.lint("--update-baseline")
        with open(self.baseline, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["violations"], {})

    def test_changed_only_limits_scope_and_baseline_updates(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        skill(self.root, "two", "Use when " + "y" * 450)
        rc, out, _ = self.lint("--changed-only", os.path.join(self.root, "skills", "one", "SKILL.md"))
        self.assertEqual(rc, 1)
        self.assertIn("LINT FAIL one", out)
        self.assertNotIn("two", out)
        self.lint("--update-baseline", "--changed-only", os.path.join(self.root, "skills", "one", "SKILL.md"))
        with open(self.baseline, encoding="utf-8") as fh:
            v = json.load(fh)["violations"]
        self.assertEqual(sorted(v), ["one:description>400"], "only the changed skill's entries move")

    def test_each_rule_fires(self):
        skill(self.root, "one", body="word " * 25000)  # > 5000 tokens by len//4
        skill(self.root, "two", body="see ~/.claude/skills/two/helper.md and $HOME/.claude/skills/two/x\n")
        skill(self.root, "three", extra_fm="homepage: https://example.com\n")
        write(os.path.join(self.root, "skills", "four", "references", "a.md"), "see [b](b.md)\n")
        write(os.path.join(self.root, "skills", "four", "references", "b.md"), "leaf\n")
        skill(self.root, "four")
        rc, out, _ = self.lint()
        self.assertEqual(rc, 1)
        for want in ("one body-tokens>5000", "two hardcoded-self-path", "three non-spec-key:homepage", "four refs-two-deep"):
            self.assertIn("LINT FAIL " + want, out)

    def test_machine_neutral_self_path_is_not_a_violation(self):
        skill(self.root, "one", body="read {agency-root}/skills/one/helper.md and ${CLAUDE_SKILL_DIR}/x.md\n")
        rc, out, _ = self.lint()
        self.assertEqual(rc, 0, out)

    def test_spec_keys_and_metadata_block_are_clean(self):
        skill(self.root, "one", extra_fm="license: MIT\nallowed-tools: Read\nmetadata:\n  scope: \"global\"\n")
        rc, out, _ = self.lint()
        self.assertEqual(rc, 0, out)

    def test_skill_without_frontmatter_lints_without_crashing(self):
        skill(self.root, "one", raw="# No frontmatter\n\ntext\n")
        rc, out, err = self.lint()
        self.assertEqual(rc, 0, out + err)

    def test_missing_baseline_file_means_empty_baseline(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        self.assertFalse(os.path.exists(self.baseline))
        self.assertEqual(self.lint()[0], 1)

    def test_baseline_output_is_deterministic(self):
        skill(self.root, "one", "Use when " + "x" * 450)
        skill(self.root, "two", "Use when " + "y" * 450)
        self.lint("--update-baseline")
        a = read_bytes(self.baseline)
        self.lint("--update-baseline")
        self.assertEqual(read_bytes(self.baseline), a)


if __name__ == "__main__":
    unittest.main()

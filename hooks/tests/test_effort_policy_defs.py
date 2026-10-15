#!/usr/bin/env python3
"""Drift test for the enforced effort policy (ruling 2026-10-15).

Source of truth: the `effort` section of hooks/lib/exec-model-map.json. The hook (model-pin.py + the spawn-ledger
turn.step relay) sets effort on every spawn and wins over agent frontmatter, so the agent files must not disagree:
  - every PD def (agents/**/*-pd.md and agents/project-management/pd-coordinator.md) carries `effort:` == categories.pd;
  - NO other agent def carries an `effort:` line (the hook decides from effort.agents; nothing to drift);
  - the config itself is internally consistent (allowed values, known categories and families).

Read-only: it opens files under hooks/ and agents/ (located from this file, never from $HOME) and writes nothing outside
its own temp dirs, so the hermetic-HOME bootstrap in test_00_isolation.py has nothing to protect here, and no live log is touched.
Skips when agents/ is absent (the Windows CI sparse checkout has no agents/). The real-map tests skip until the
`effort` section exists in the map; the checker logic is also proved on temp fixtures, so the test is never vacuous.
Run: python3 -m unittest -v hooks/tests/test_effort_policy_defs.py
"""
import json
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.normpath(os.path.join(HERE, "..", ".."))
AGENTS = os.path.join(CLAUDE, "agents")
REAL_MAP = os.path.join(CLAUDE, "hooks", "lib", "exec-model-map.json")

ALLOWED = {"low", "medium", "high", "xhigh", "max"}
FAMILIES = {"visual", "content", "coding", "other"}
EFFORT_RE = re.compile(r"^effort:[ \t]*(\S*)[ \t]*$")

# Shape of the shipped policy (design contract); used ONLY when the real map has no `effort` section yet.
FIXTURE_EFFORT = {
    "enabled": True,
    "categories": {"pd": "medium", "coding_complex": "high", "coding_routine": "medium", "visual": "high",
                   "content_en": "high", "content_vi": "xhigh", "other": "medium", "lookup": "low"},
    "fallback_category": "other",
    "domains": {"frontend-ui": "visual", "writing-en": "content", "writing-vi": "content",
                "backend-infra-deploy": "coding", "research": "other"},
    "complexity": {"domains": ["code-quality-testing"], "skills": ["investigate"], "markers": ["refactor"]},
    "marker_categories": {"lookup": "lookup", "debug": "coding_complex"},
    "agents": {"critique-design": "visual", "critique-content": "content_en", "critique-code": "coding_complex",
               "coord": "other", "mini-coord": "other", "codebase-search": "lookup"},
}


def load_effort(path=REAL_MAP):
    """Return the map's `effort` section, or None when absent."""
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("effort")


def frontmatter_lines(path):
    """Lines of the YAML frontmatter block, or None when the file has none. Strict: opening and closing '---'."""
    with open(path, encoding="utf-8", newline=None) as f:
        lines = f.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return None


def effort_value(path):
    """Value of the frontmatter `effort:` line, "" for a bare key, None when there is no such line."""
    fm = frontmatter_lines(path)
    for line in fm or []:
        m = EFFORT_RE.match(line)
        if m:
            return m.group(1)
    return None


def is_pd_def(path):
    base = os.path.basename(path)
    return base.endswith("-pd.md") or base == "pd-coordinator.md"


def agent_defs(root):
    """Every .md under root with a frontmatter block (agent definitions); INDEX/README style docs have none."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "graphify-out"]
        for fn in sorted(filenames):
            if fn.endswith(".md"):
                p = os.path.join(dirpath, fn)
                if frontmatter_lines(p) is not None:
                    out.append(p)
    return sorted(out)


def check_defs(root, pd_value):
    """Problems (list of strings) in the agent defs under root against the policy's PD value."""
    problems = []
    for p in agent_defs(root):
        rel = os.path.relpath(p, root)
        val = effort_value(p)
        if is_pd_def(p):
            if val != pd_value:
                problems.append("%s: PD def effort is %r, policy says %r" % (rel, val, pd_value))
        elif val is not None:
            problems.append("%s: non-PD def has an effort line (%r); the hook decides, remove it" % (rel, val))
    return problems


def check_config(eff):
    """Problems (list of strings) in the effort section's own consistency."""
    problems = []
    cats = eff.get("categories") or {}
    for k, v in cats.items():
        if v not in ALLOWED:
            problems.append("categories.%s=%r not in %s" % (k, v, sorted(ALLOWED)))
    for need in ("pd", eff.get("fallback_category")):
        if need not in cats:
            problems.append("category %r missing from categories" % (need,))
    for d, fam in (eff.get("domains") or {}).items():
        if fam not in FAMILIES:
            problems.append("domains.%s=%r not in %s" % (d, fam, sorted(FAMILIES)))
    for a, c in (eff.get("agents") or {}).items():
        if c not in cats:
            problems.append("agents.%s=%r is not a category" % (a, c))
    for m, c in (eff.get("marker_categories") or {}).items():
        if c not in cats:
            problems.append("marker_categories.%s=%r is not a category" % (m, c))
    return problems


def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return p


class CheckerLogic(unittest.TestCase):
    """The checkers catch drift (proved on temp trees; independent of the live agents/ and of the map)."""

    def test_flags_pd_with_wrong_or_missing_effort_and_non_pd_with_effort(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "a/x-pd.md", "---\nname: x-pd\neffort: high\n---\nbody\n")
            _write(root, "a/y-pd.md", "---\nname: y-pd\n---\nbody\n")
            _write(root, "a/pd-coordinator.md", "---\nname: pd-coordinator\neffort: medium\n---\nbody\n")
            _write(root, "a/critic.md", "---\nname: critic\neffort: high\n---\nbody\n")
            _write(root, "a/clean.md", "---\nname: clean\nmodel: sonnet\n---\nbody\n")
            _write(root, "a/INDEX.md", "# no frontmatter\neffort: high\n")
            _write(root, "a/body-only.md", "---\nname: b\n---\neffort: high\n")  # outside the frontmatter: ignored
            problems = check_defs(root, "medium")
            self.assertEqual(sorted(p.split(":")[0] for p in problems),
                             [os.path.join("a", "critic.md"), os.path.join("a", "x-pd.md"), os.path.join("a", "y-pd.md")])

    def test_clean_tree_has_no_problems(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "z-pd.md", "---\nname: z-pd\neffort: medium\n---\n")
            _write(root, "w.md", "---\nname: w\n---\n")
            self.assertEqual(check_defs(root, "medium"), [])

    def test_unclosed_frontmatter_is_not_an_agent_def(self):
        with tempfile.TemporaryDirectory() as root:
            p = _write(root, "o.md", "---\nname: o\neffort: high\n")
            self.assertIsNone(frontmatter_lines(p))

    def test_config_checker_flags_bad_values_and_dangling_references(self):
        bad = json.loads(json.dumps(FIXTURE_EFFORT))
        bad["categories"]["visual"] = "ultra"
        bad["domains"]["x"] = "painting"
        bad["agents"]["y"] = "nonesuch"
        bad["marker_categories"]["z"] = "nonesuch"
        bad["fallback_category"] = "nonesuch"
        self.assertEqual(len(check_config(bad)), 5)
        self.assertEqual(check_config(FIXTURE_EFFORT), [])


@unittest.skipUnless(os.path.isdir(AGENTS), "agents/ absent (sparse checkout, e.g. Windows CI)")
class LiveDefsMatchPolicy(unittest.TestCase):
    """The shipped agent defs against the shipped (or, until it lands, the fixture) policy."""

    @classmethod
    def setUpClass(cls):
        real = load_effort() if os.path.isfile(REAL_MAP) else None
        cls.using_fixture = real is None
        cls.eff = real if real is not None else FIXTURE_EFFORT

    def test_pd_defs_mirror_policy_and_non_pd_defs_have_no_effort_line(self):
        problems = check_defs(AGENTS, self.eff["categories"]["pd"])
        self.assertEqual(problems, [], "agent defs drift from the effort policy (%s):\n  %s" % (
            "FIXTURE policy: real map has no effort section yet" if self.using_fixture else "exec-model-map.json",
            "\n  ".join(problems)))

    def test_every_pd_def_is_found(self):
        pds = [p for p in agent_defs(AGENTS) if is_pd_def(p)]
        self.assertTrue(any(p.endswith("pd-coordinator.md") for p in pds))
        # The repo ships one PD def (pd-coordinator); per-project {slug}-pd defs are generated by /new-project.
        self.assertGreaterEqual(len(pds), 1, "no PD defs found: %s" % pds)


class RealMapPolicy(unittest.TestCase):
    """The real map's effort section (written by the hook Exec). Skips until it exists."""

    def setUp(self):
        if not os.path.isfile(REAL_MAP):
            self.skipTest("hooks/lib/exec-model-map.json absent")
        self.eff = load_effort()
        if self.eff is None:
            self.skipTest("exec-model-map.json has no `effort` section yet")

    def test_effort_section_is_internally_consistent(self):
        self.assertEqual(check_config(self.eff), [])

    def test_policy_values_match_the_ruling(self):
        c = self.eff["categories"]
        self.assertEqual((c["pd"], c["coding_routine"], c["coding_complex"], c["visual"], c["content_en"],
                          c["content_vi"], c["lookup"], c["other"]),
                         ("medium", "medium", "high", "high", "high", "xhigh", "low", "medium"))


if __name__ == "__main__":
    unittest.main()

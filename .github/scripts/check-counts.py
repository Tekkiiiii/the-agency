#!/usr/bin/env python3
"""Fail on any stale "N skills / N+ agents / N departments" claim in user-facing docs.

The counts are DERIVED from the tree, never typed in here:
  skills       skills/*/SKILL.md
  agents       .md files under agents/ whose YAML frontmatter has `name:` and
               `description:` (skips memory/, integrations/, scripts/, which are not
               agent definitions). Same definition the CHANGELOG uses, and the same
               file set agents/scripts/lint-agents.sh lints.
  departments  agents/<dir>/ that contains an INDEX.md

Scanned (current, user-facing copy only; CHANGELOG and dated notes are out of scope):
  README.md, skills/INDEX.md, skills/onboard/SKILL.md, agents/INDEX.md,
  agents/README.md, docs/**/*.md, cli/** (.js/.json/.md), install.sh, install.ps1

Claim rules:
  "N skills"  -> N must equal the derived count
  "N+ skills" -> N <= count <= N * 1.1 (a floor claim that has drifted far below the
                 real number is stale too; refresh it or drop the count)
  Numbers < 20 for skills/agents are ignored (spawn limits such as "more than 6
  agents", not catalog sizes); department counts are always checked.
  Ranges ("1-3 skills") are ignored. A line carrying `check-counts:ignore` is skipped
  (use sparingly: only for a count that describes some OTHER system). Whole docs
  about another system go in EXTERNAL_DOCS below instead.

Usage: python3 .github/scripts/check-counts.py [repo-root]
"""
import glob
import os
import re
import sys

NOUNS = {"skill": "skills", "agent": "agents", "department": "departments"}
# Docs that describe some OTHER system, whose counts are not ours to check.
EXTERNAL_DOCS = {"docs/ecc-patterns.md"}  # everything-claude-code: "60 agents, 230 skills"
MIN_CATALOG = 20  # skills/agents below this are not catalog-size claims

# "240+ skills", "45 agent definitions", "240+ reusable workflow skills", "8 departments"
CLAIM = re.compile(
    r"(?<![\w.,\-–/])(\d[\d,]*)(\+|%2B)?\s+(?:[A-Za-z-]+\s+){0,2}?"
    r"(skills?|agents?|departments?)\b",
    re.IGNORECASE,
)
# shields.io style badges: Skills-240%2B, Agents-45%2B
BADGE = re.compile(r"\b(Skills|Agents)-(\d+)(\+|%2B)?", re.IGNORECASE)


def frontmatter(path):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return ""
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    return m.group(1) if m else ""


def derive(root):
    skills = len(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
    agents = 0
    for r, dirs, files in os.walk(os.path.join(root, "agents")):
        dirs[:] = [d for d in dirs if d not in ("memory", "integrations", "scripts")]
        for f in files:
            if f.endswith(".md"):
                fm = frontmatter(os.path.join(r, f))
                if re.search(r"^name:", fm, re.M) and re.search(r"^description:", fm, re.M):
                    agents += 1
    depts = 0
    for d in sorted(os.listdir(os.path.join(root, "agents"))):
        if os.path.isfile(os.path.join(root, "agents", d, "INDEX.md")):
            depts += 1
    return {"skills": skills, "agents": agents, "departments": depts}


def targets(root):
    out = []
    for rel in ("README.md", "skills/INDEX.md", "skills/onboard/SKILL.md",
                "agents/INDEX.md", "agents/README.md", "install.sh", "install.ps1"):
        if os.path.isfile(os.path.join(root, rel)):
            out.append(rel)
    for pattern in ("docs/**/*.md", "agents/**/*.md", "cli/**/*.js", "cli/**/*.json", "cli/**/*.md"):
        for p in glob.glob(os.path.join(root, pattern), recursive=True):
            rel = os.path.relpath(p, root)
            parts = rel.split(os.sep)
            if "node_modules" in parts or (parts[0] == "agents" and ("memory" in parts or "integrations" in parts)):
                continue
            if os.path.basename(rel) == "package-lock.json":
                continue
            out.append(rel)
    return sorted(set(out))


def claims(line):
    """Yield (matched_text, noun, number, is_floor) for each count claim on a line."""
    for m in CLAIM.finditer(line):
        noun = NOUNS[m.group(3).lower().rstrip("s")]
        yield m.group(0), noun, int(m.group(1).replace(",", "")), bool(m.group(2))
    for m in BADGE.finditer(line):
        noun = NOUNS[m.group(1).lower().rstrip("s")]
        yield m.group(0), noun, int(m.group(2)), bool(m.group(3))


def verdict(noun, n, floor, actual):
    """Return None if the claim holds, else a reason."""
    if noun != "departments" and n < MIN_CATALOG:
        return None
    if floor:
        if n <= actual <= n * 1.1:
            return None
        return "a floor claim must satisfy N <= count <= 1.1*N"
    return None if n == actual else "an exact claim must equal the count"


def selftest():
    cases = [
        ("240+ skills and 45+ agents.", [("skills", 240, True), ("agents", 45, True)]),
        ("Agent catalog (130+ agents)", [("agents", 130, True)]),
        ("organized across 8 departments", [("departments", 8, False)]),
        ("240+ reusable workflow skills", [("skills", 240, True)]),
        ("![Skills: 240+](x/Skills-240%2B-orange)", [("skills", 240, True)]),
        ("pick 1-3 skills", []),
        ("Skills Library", []),
    ]
    for text, want in cases:
        got = [(n, v, f) for _, n, v, f in claims(text)]
        # the badge alt text "Skills: 240+" is not matched; only the URL is, once
        if sorted(got) != sorted(want):
            sys.exit("check-counts: self-test failed on %r: got %r want %r" % (text, got, want))


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    if not os.path.isdir(os.path.join(root, "agents")) or not os.path.isdir(os.path.join(root, "skills")):
        sys.exit("check-counts: %s has no agents/ and skills/ (run from the repo root)" % root)
    selftest()
    actual = derive(root)
    print("derived from tree: skills=%(skills)d agents=%(agents)d departments=%(departments)d" % actual)
    checked = stale = 0
    for rel in targets(root):
        if rel in EXTERNAL_DOCS:
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines, 1):
            if "check-counts:ignore" in line:
                continue
            for text, noun, n, floor in claims(line):
                checked += 1
                why = verdict(noun, n, floor, actual[noun])
                if why:
                    stale += 1
                    print("STALE %s:%d: claims %r but the tree has %d %s (%s)"
                          % (rel, i, text, actual[noun], noun, why))
    print("check-counts: %d claim(s) checked, %d stale" % (checked, stale))
    if actual["skills"] == 0 or actual["agents"] == 0 or actual["departments"] == 0:
        sys.exit("check-counts: a derived count is 0, so the tree walk is broken")
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()

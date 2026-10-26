#!/usr/bin/env python3
"""CI guard for the generated skill registry and the skill lint (replaces a pre-commit hook in the live system).

Fails when:
  1. skills/INDEX.md is stale: it is GENERATED from skills/*/SKILL.md by scripts/skill-registry.py, so a skill
     added, renamed, removed or re-described without regenerating it drifts the index from the tree.
     Fix: python3 scripts/skill-registry.py   (then commit skills/INDEX.md)
  2. the skill lint finds a violation that is not in scripts/skill-registry/lint-baseline.json (a ratchet: existing
     violations pass, new ones fail). Fix the skill. Accept an intended vendor update with
     python3 scripts/skill-registry.py --lint --update-baseline --changed-only skills/<name>/SKILL.md

Usage: python3 .github/scripts/check-skill-registry.py [repo-root]
"""
import os
import subprocess
import sys


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tool = os.path.join(root, "scripts", "skill-registry.py")
    if not os.path.isfile(tool):
        sys.exit("check-skill-registry: %s not found (run from the repo root)" % tool)
    failed = 0
    for label, args in (("INDEX.md is current", ["--check"]), ("no new lint violations", ["--lint"])):
        p = subprocess.run([sys.executable, tool, "--root", root] + args, universal_newlines=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print("%s %s" % ("PASS" if p.returncode == 0 else "FAIL", label))
        if p.returncode != 0:
            failed += 1
            print(p.stdout.rstrip())
        else:
            print("  " + p.stdout.strip().splitlines()[-1])
    print("check-skill-registry: %s" % ("FAIL (%d)" % failed if failed else "OK"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

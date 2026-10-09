#!/usr/bin/env python3
"""core-mirror-check: verify that core/ mirrors its canonical sources.

Why it exists: core/ holds copies of canonical docs (agent defs, ORG.md, runbooks). Nothing
re-synced them, so they drift silently and stale wording ships from the copy.

Usage:
  python3 scripts/core-mirror-check.py                 # check; exit 0 ok, 1 drift, 2 config error
  python3 scripts/core-mirror-check.py --root .        # explicit agency root (CI passes this)
  python3 scripts/core-mirror-check.py --quiet         # print only problems
  python3 scripts/core-mirror-check.py --fix           # copy source over drifted dest, re-check

Root: --root, else $AGENCY_HOME, else $CLAUDE_CONFIG_DIR, else <home>/.claude.
A root is a checkout of this repo or an installed agency tree: both have core/, agents/, runbooks/.

Mirror map (dest <- source, both under the root):
  core/agents/{coord,mini-coord,pd-coordinator,curator,delegator}.md <- agents/ tree
  core/ORG.md <- agents/ORG.md
  core/runbooks/<every file> <- runbooks/<same name>
Everything else under core/ is standalone (no source) and is not checked. No git operations.

Known delta (the only exemption): a dest file may wrap core-only text in marker lines
  <!-- core-mirror:exempt begin <id> (<reason>) -->
  ...
  <!-- core-mirror:exempt end <id> -->
Those lines, everything between them, and the one blank line right after the end marker are
removed from the DEST before comparing. Every exemption is printed on every run. Markers in a
SOURCE file, unbalanced markers, or mismatched ids are config errors (exit 2). --fix refuses to
overwrite a dest that carries an exemption (it would delete the core-only text); merge by hand.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

AGENT_SRC = {
    "coord.md": "agents/project-management/coord.md",
    "mini-coord.md": "agents/project-management/mini-coord.md",
    "pd-coordinator.md": "agents/project-management/pd-coordinator.md",
    "curator.md": "agents/specialized/curator.md",
    "delegator.md": "agents/specialized/delegator.md",
}

BEGIN = re.compile(r"^<!-- core-mirror:exempt begin (\S+)")
END = re.compile(r"^<!-- core-mirror:exempt end (\S+) -->\s*$")


def default_root():
    return (os.environ.get("AGENCY_HOME")
            or os.environ.get("CLAUDE_CONFIG_DIR")
            or str(Path.home() / ".claude"))


def build_pairs(root):
    """Return list of (dest, source) Paths. Raises ValueError on config error."""
    core = root / "core"
    if not core.is_dir():
        raise ValueError(f"missing {core}")
    pairs = [(core / "agents" / n, root / s) for n, s in AGENT_SRC.items()]
    pairs.append((core / "ORG.md", root / "agents" / "ORG.md"))
    rb = core / "runbooks"
    if not rb.is_dir():
        raise ValueError(f"missing {rb}")
    for f in sorted(p for p in rb.iterdir() if p.is_file()):
        src = root / "runbooks" / f.name
        if not src.is_file():
            raise ValueError(f"core/runbooks/{f.name} has no source runbooks/{f.name}")
        pairs.append((f, src))
    return pairs


def strip_exempt(data, label):
    """Remove marked exempt blocks from dest bytes. Returns (bytes, [(id, nlines)]).
    Raises ValueError on unbalanced / mismatched markers."""
    lines = data.decode("utf-8", "surrogateescape").split("\n")
    out, blocks, i = [], [], 0
    while i < len(lines):
        m = BEGIN.match(lines[i])
        if not m:
            if END.match(lines[i]):
                raise ValueError(f"{label}:{i + 1}: exempt end without begin")
            out.append(lines[i])
            i += 1
            continue
        bid, start = m.group(1), i
        i += 1
        while i < len(lines) and not END.match(lines[i]):
            if BEGIN.match(lines[i]):
                raise ValueError(f"{label}:{i + 1}: nested exempt begin")
            i += 1
        if i >= len(lines):
            raise ValueError(f"{label}:{start + 1}: exempt begin '{bid}' never closed")
        if END.match(lines[i]).group(1) != bid:
            raise ValueError(f"{label}:{i + 1}: exempt end id does not match begin '{bid}'")
        i += 1
        if i < len(lines) and lines[i] == "":
            i += 1
        blocks.append((bid, i - start))
    return "\n".join(out).encode("utf-8", "surrogateescape"), blocks


def state(dest, src, root):
    """Return (state, exemptions). Raises ValueError on config error."""
    if not src.is_file():
        return "MISSING-SOURCE", []
    if not dest.is_file():
        return "MISSING-DEST", []
    sdata = src.read_bytes()
    if b"core-mirror:exempt" in sdata:
        raise ValueError(f"exempt marker in source {src.relative_to(root)}; markers belong in the dest only")
    ddata, blocks = strip_exempt(dest.read_bytes(), str(dest.relative_to(root)))
    return ("OK" if ddata == sdata else "DRIFT"), blocks


def check(pairs, root, quiet):
    bad = 0
    for dest, src in pairs:
        st, blocks = state(dest, src, root)
        bad += st != "OK"
        rel = dest.relative_to(root)
        if st != "OK" or not quiet:
            print(f"{st:15} {rel} <- {src.relative_to(root)}")
        for bid, n in blocks:
            print(f"{'EXEMPT':15} {rel}: block '{bid}' ({n} lines) excluded from comparison")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="verify core/ mirrors its canonical sources")
    ap.add_argument("--fix", action="store_true", help="copy source over drifted dest, then re-check")
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    ap.add_argument("--root", default=None, help="agency root (default: resolved from the environment, see the module docstring)")
    a = ap.parse_args()
    root = Path(a.root or default_root()).expanduser().resolve()
    try:
        pairs = build_pairs(root)
        if not a.quiet:
            mapped = {d for d, _ in pairs}
            alone = sorted(str(p.relative_to(root)) for p in (root / "core").rglob("*")
                           if p.is_file() and p not in mapped and not p.name.startswith("."))
            print("standalone (unchecked):", ", ".join(alone) or "none")
        rc = check(pairs, root, a.quiet)
        if a.fix and rc:
            for dest, src in pairs:
                st, blocks = state(dest, src, root)
                if st not in ("DRIFT", "MISSING-DEST"):
                    continue
                if blocks:
                    print(f"SKIPPED {dest.relative_to(root)}: carries an exemption; merge by hand")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
                print(f"COPIED {src.relative_to(root)} -> {dest.relative_to(root)}")
            print("-- re-check --")
            rc = check(pairs, root, a.quiet)
    except ValueError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())

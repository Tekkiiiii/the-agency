#!/usr/bin/env python3
"""memory-frontmatter-add.py — Memory v2 P1 schema unification.

Adds typed frontmatter (name/type/description/created/review-by/links) to memory
files that don't already have it. Pure delta edit: prepends a frontmatter block,
never touches existing body content. Idempotent — skips any file that already
starts with a `---` frontmatter fence.

This is reusable P3 gardener infrastructure (the "schema" part of Lint + the
additive part of Curate), not a one-off script — designed to be re-run safely
against any memory directory as new files are added.

Usage:
    python3 memory-frontmatter-add.py --dir /path/to/memory --dry-run
    python3 memory-frontmatter-add.py --dir /path/to/memory --apply

Scope contract (P1 blast-radius findings, 2026-07-10):
  - Only *.md files directly inside the target dir and its `lessons/` subdir
    (no recursion into sessions/, tasks/, inter-spawn-tasks/, qa/, agents/,
    outputs/ — those are managed/log/control dirs, not knowledge memory).
  - Hard-excluded filenames (mechanically owned by save-state.py / recall /
    pd-resume — schema must never touch these): next-session.md, decisions.md,
    decisions-archive.md, heartbeat.md, STATE.md, PROJECT.md, MEMORY.md,
    wiki-log.md, wiki-schema.md, pd-scratch.md, index.md, README.md, CLAUDE.md.
  - Any file already starting with `---` is left untouched (idempotent).
"""

import argparse
import datetime
import pathlib
import re
import subprocess
import sys

EXCLUDE_NAMES = {
    "next-session.md", "decisions.md", "decisions-archive.md", "heartbeat.md",
    "STATE.md", "PROJECT.md", "MEMORY.md", "wiki-log.md", "wiki-schema.md",
    "pd-scratch.md", "index.md", "README.md", "CLAUDE.md",
    # L0 integrity fixture — fixed content, SHA-256 byte-compared daily (R1).
    # Frontmatter would change its bytes and break the canary check.
    ".canary.md",
}
EXCLUDE_DIRS = {
    "sessions", "tasks", "inter-spawn-tasks", "qa", "agents", "outputs",
    "graphify-out", "obsidian", ".git", "node_modules", "revisions",
    "ongoing", "completed",
}
PROJECT_TYPE_NAMES = {"pd-structure.md", "dev-plan.md", "brand-guidelines.md"}


def infer_type(path: pathlib.Path) -> str:
    name = path.name
    parent = path.parent.name
    if parent == "lessons":
        return "lesson"
    if name.startswith("feedback_"):
        return "feedback"
    if name.startswith("reference_"):
        return "reference"
    if name in PROJECT_TYPE_NAMES:
        return "project"
    if "registry" in name or name == "medium-term.md" or name == "delegator-cache.md":
        return "registry"
    return "note"


def infer_name(path: pathlib.Path, body: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if m:
        return m.group(1).strip()[:80]
    stem = path.stem.replace("_", " ").replace("-", " ")
    return stem[:1].upper() + stem[1:]


def infer_description(body: str, name: str) -> str:
    """Best-effort: first non-heading, non-empty line after the title. v1
    heuristic only — P3 gardener Distill phase should refine low-quality
    descriptions (S7 check: non-empty, unique, != name restated)."""
    lines = [l.strip() for l in body.splitlines()]
    seen_h1 = False
    for l in lines:
        if not l:
            continue
        if l.startswith("#"):
            seen_h1 = True
            continue
        if l.startswith(("- ", "|", "```", ">")):
            continue
        candidate = re.sub(r"[*_`]", "", l).strip()
        if candidate and candidate.lower() != name.lower():
            return candidate[:140]
    return "(auto-generated — needs review, no distinct summary line found)"


def infer_created(path: pathlib.Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path.parent), "log", "--follow", "--format=%ad",
             "--date=short", "--", path.name],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        if lines:
            return lines[-1].strip()
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        ts = path.stat().st_mtime
        return datetime.datetime.fromtimestamp(ts).date().isoformat()
    except OSError:
        return datetime.date.today().isoformat()


def build_frontmatter(path: pathlib.Path, body: str) -> str:
    ftype = infer_type(path)
    name = infer_name(path, body)
    desc = infer_description(body, name)
    created = infer_created(path)
    lines = ["---", f"name: {name}", f"type: {ftype}",
              f"description: {desc}", f"created: {created}"]
    if ftype == "project":
        review_by = (datetime.date.today() + datetime.timedelta(days=90)).isoformat()
        lines.append(f"review-by: {review_by}")
    lines.append("links: []")
    lines.append("---\n")
    return "\n".join(lines)


def candidate_files(target: pathlib.Path):
    if not target.is_dir():
        return
    for f in sorted(target.glob("*.md")):
        if f.name in EXCLUDE_NAMES:
            continue
        yield f
    lessons = target / "lessons"
    if lessons.is_dir():
        for f in sorted(lessons.glob("*.md")):
            if f.name in EXCLUDE_NAMES:
                continue
            yield f


def process(target: pathlib.Path, apply: bool):
    added, skipped_has_fm, skipped_excluded = [], [], []
    for f in candidate_files(target):
        try:
            body = f.read_text(errors="ignore")
        except OSError as e:
            print(f"  ERROR reading {f}: {e}")
            continue
        if body.lstrip().startswith("---"):
            skipped_has_fm.append(f)
            continue
        fm = build_frontmatter(f, body)
        added.append(f)
        if apply:
            f.write_text(fm + body)
    return added, skipped_has_fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="target memory directory")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()

    target = pathlib.Path(args.dir).expanduser().resolve()
    added, skipped = process(target, apply=args.apply)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] {target}")
    print(f"  frontmatter added: {len(added)}")
    for f in added:
        print(f"    + {f.relative_to(target.parent) if target.parent in f.parents else f.name}")
    print(f"  already had frontmatter (skipped): {len(skipped)}")
    if not args.apply and added:
        print("\n  Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()

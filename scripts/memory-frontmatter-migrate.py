#!/usr/bin/env python3
"""memory-frontmatter-migrate.py — Memory v2 P1 schema unification, pass 2.

Companion to memory-frontmatter-add.py. That script only handles files with
NO frontmatter at all. This script handles files that already have SOME
frontmatter (typically Claude Code's own auto-memory extraction schema:
name/description/type-or-metadata.node_type+metadata.type/originSessionId)
but are missing the target unified schema's required fields: top-level
`type`, `created`, `links`.

Pure delta edit: adds only the missing required keys, inserted just before
the closing `---` fence. Never touches existing fields (originSessionId,
metadata block, etc. are left as-is — additive only, no deletion, no
restructuring). Idempotent — a file with all three fields already present
is left untouched.

Usage:
    python3 memory-frontmatter-migrate.py --dir /path/to/memory --dry-run
    python3 memory-frontmatter-migrate.py --dir /path/to/memory --apply
"""

import argparse
import datetime
import pathlib
import re
import subprocess

EXCLUDE_NAMES = {
    "next-session.md", "decisions.md", "decisions-archive.md", "heartbeat.md",
    "STATE.md", "PROJECT.md", "MEMORY.md", "wiki-log.md", "wiki-schema.md",
    "pd-scratch.md", "index.md", "README.md", "CLAUDE.md", ".canary.md",
}


def infer_type_from_name(path: pathlib.Path) -> str:
    name = path.name
    if name.startswith("feedback_"):
        return "feedback"
    if name.startswith("reference_"):
        return "reference"
    return "note"


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


def find_fence_end(lines):
    """lines[0] must be '---'. Return index of the closing '---' line, or None."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i
    return None


def extract_nested_type(block_lines):
    """Look for a `metadata:` block with an indented `type: X` line."""
    in_metadata = False
    for l in block_lines:
        if re.match(r"^metadata:\s*$", l):
            in_metadata = True
            continue
        if in_metadata:
            if re.match(r"^\S", l):  # dedent — left the metadata block
                break
            m = re.match(r"^\s+type:\s*(.+)$", l)
            if m:
                return m.group(1).strip()
    return None


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
    migrated, skipped_ok, skipped_no_fm = [], [], []
    for f in candidate_files(target):
        try:
            text = f.read_text(errors="ignore")
        except OSError as e:
            print(f"  ERROR reading {f}: {e}")
            continue
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            skipped_no_fm.append(f)
            continue
        close_idx = find_fence_end(lines)
        if close_idx is None:
            skipped_no_fm.append(f)
            continue
        block = lines[1:close_idx]
        has_type = any(re.match(r"^type:\s*\S", l) for l in block)
        has_created = any(re.match(r"^created:\s*\S", l) for l in block)
        has_links = any(re.match(r"^links:\s*", l) for l in block)

        if has_type and has_created and has_links:
            skipped_ok.append(f)
            continue

        additions = []
        if not has_type:
            t = extract_nested_type(block) or infer_type_from_name(f)
            additions.append(f"type: {t}")
        if not has_created:
            additions.append(f"created: {infer_created(f)}")
        if not has_links:
            additions.append("links: []")

        new_lines = lines[:close_idx] + additions + lines[close_idx:]
        migrated.append((f, additions))
        if apply:
            f.write_text("\n".join(new_lines) + ("\n" if text.endswith("\n") else ""))
    return migrated, skipped_ok, skipped_no_fm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    target = pathlib.Path(args.dir).expanduser().resolve()
    migrated, skipped_ok, skipped_no_fm = process(target, apply=args.apply)

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] {target}")
    print(f"  migrated (missing fields added): {len(migrated)}")
    for f, additions in migrated:
        print(f"    + {f.name}: {', '.join(additions)}")
    print(f"  already schema-valid (skipped): {len(skipped_ok)}")
    print(f"  no frontmatter fence found (skipped, needs pass-1 script): {len(skipped_no_fm)}")
    if not args.apply and migrated:
        print("\n  Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()

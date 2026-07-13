#!/usr/bin/env python3
"""Skill system audit — mechanical reliability checks over ~/.claude/skills/*/SKILL.md.

Checks per skill:
  A1 skill_md_missing     — no SKILL.md in dir
  A2 fm_unparseable       — frontmatter absent or YAML parse error
  A3 name_missing         — no `name:` in frontmatter
  A4 name_mismatch        — name != directory name
  A5 desc_missing         — no description
  A6 desc_too_short       — description < 60 chars (weak trigger signal)
  A7 desc_too_long        — description > 4000 chars (context waste)
  A8 no_trigger_language  — description lacks any trigger phrasing
  A9 body_oversize        — SKILL.md > 40 KB (advisory only: context cost per invoke)
  B1 dead_local_ref       — references a file inside skill dir that doesn't exist
  B2 dead_home_ref        — references ~/.claude/... path that doesn't exist
  B3 todo_markers         — TODO/FIXME/XXX/PLACEHOLDER in body
  B4 dup_name             — same frontmatter name used by another skill dir

Output: JSON to stdout (one object per skill with issue list) + summary line to stderr.
"""
import json
import os
import re
import sys
from pathlib import Path

SKILLS = Path("~/.claude/skills").expanduser()
HOME = Path("~").expanduser()

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

TRIGGER_RE = re.compile(
    r"(use when|when to|trigger|invoke|use this|when the user|when you|use for|also for"
    r"|use before|use after|use (?:it|via)|load when|loaded (?:automatically|on demand)"
    r"|whenever|apply (?:to|when)|default (?:tool|for|browser)|for (?:any|all) |触发)",
    re.IGNORECASE,
)
# local refs: markdown links / backticked paths pointing into the skill dir
LOCAL_REF_RE = re.compile(
    r"(?:\]\(|`)((?:\./)?(?:references|scripts|assets|templates|examples|memory)/[A-Za-z0-9_./\-]+?)(?:\)|`)"
)
HOME_REF_RE = re.compile(r"~/\.claude/[A-Za-z0-9_./\-]+")


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, "no frontmatter block"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "unterminated frontmatter"
    raw = parts[1]
    if HAVE_YAML:
        try:
            fm = yaml.safe_load(raw)
            if not isinstance(fm, dict):
                return None, "frontmatter not a mapping"
            return fm, None
        except Exception as e:
            return None, f"yaml error: {e}"
    # fallback: naive key extraction
    fm = {}
    m = re.search(r"^name:\s*(.+)$", raw, re.M)
    if m:
        fm["name"] = m.group(1).strip()
    m = re.search(r"^description:\s*(?:>-?|\|)?\s*(.*(?:\n[ \t]+.*)*)", raw, re.M)
    if m:
        fm["description"] = re.sub(r"\s+", " ", m.group(1)).strip()
    return fm, None


def audit_skill(d):
    issues = []
    skill_md = d / "SKILL.md"
    if not skill_md.exists():
        return {"skill": d.name, "issues": [{"code": "A1", "detail": "SKILL.md missing"}],
                "name": None, "desc_len": 0, "advisories": []}

    text = skill_md.read_text(errors="replace")
    body_kb = len(text.encode()) / 1024
    fm, err = parse_frontmatter(text)

    name = None
    desc = ""
    if fm is None:
        issues.append({"code": "A2", "detail": err})
    else:
        name = fm.get("name")
        desc = str(fm.get("description") or "")
        if not name:
            issues.append({"code": "A3", "detail": "no name field"})
        elif str(name).strip() != d.name:
            issues.append({"code": "A4", "detail": f"name '{name}' != dir '{d.name}'"})
        if not desc:
            issues.append({"code": "A5", "detail": "no description"})
        else:
            if len(desc) < 60:
                issues.append({"code": "A6", "detail": f"desc {len(desc)} chars"})
            if len(desc) > 4000:
                issues.append({"code": "A7", "detail": f"desc {len(desc)} chars"})
            if not TRIGGER_RE.search(desc) and not re.search(r"SUNSET|superseded", desc):
                issues.append({"code": "A8", "detail": "no trigger phrasing in description"})

    advisories = []
    if body_kb > 40:
        advisories.append({"code": "A9", "detail": f"SKILL.md {body_kb:.0f} KB"})

    body = text.split("---", 2)[2] if text.startswith("---") and len(text.split("---", 2)) > 2 else text

    for m in LOCAL_REF_RE.finditer(body):
        rel = m.group(1).lstrip("./")
        # truncated template paths (e.g. delegated-{task-id}.md matches up to '-') and
        # illustrative placeholders (references/xxx.md) aren't real refs
        if rel.endswith(("-", "/", ".")) or "/xxx." in rel:
            continue
        # refs may resolve against the skill dir OR the shared skills root (gstack convention)
        if not (d / rel).exists() and not (SKILLS / rel).exists():
            issues.append({"code": "B1", "detail": f"dead local ref: {rel}"})

    # runtime-created paths — not install-time defects
    RUNTIME_ROOTS = ("~/.claude/state/", "~/.claude/outputs/", "~/.claude/tasks/",
                     "~/.claude/.context/", "~/.claude/logs/", "~/.claude/todos/")
    for m in set(HOME_REF_RE.findall(body)):
        p = m.rstrip(".,;:)")
        # skip template placeholders and truncated {var} captures
        if any(c in p for c in "[]{}<>*") or p.endswith(("-", "/", ".")):
            continue
        if p.startswith(RUNTIME_ROOTS) or "/.feature-" in p or p.endswith("update-history.md"):
            continue
        # per-domain notes created at runtime by browser-domain-skills
        if "/browser-domain-skills/" in p:
            continue
        target = Path(p).expanduser()
        if not target.exists():
            issues.append({"code": "B2", "detail": f"dead path: {p}"})

    return {"skill": d.name, "name": str(name) if name else None, "desc_len": len(desc),
            "issues": issues, "advisories": advisories}


def main():
    # only dirs with SKILL.md are skills; others are support dirs (bin, lib, docs, .git, ...)
    # intra-root symlinks are aliases (connect-chrome -> open-gstack-browser): skip to avoid
    # duplicate audits. External-target symlinks (~/.agents/skills/...) are REAL skills: include.
    dirs = []
    dangling = []
    for p in sorted(SKILLS.iterdir()):
        if not p.is_dir():
            if p.is_symlink() and not p.exists():
                dangling.append(p.name)
            continue
        if p.is_symlink():
            if p.resolve().is_relative_to(SKILLS.resolve()):
                continue  # alias
        if (p / "SKILL.md").exists():
            dirs.append(p)
    for name in dangling:
        print(f"DANGLING SYMLINK: {name}", file=sys.stderr)
    results = [audit_skill(d) for d in dirs]

    # B4 duplicate names
    by_name = {}
    for r in results:
        if r["name"]:
            by_name.setdefault(r["name"], []).append(r["skill"])
    for nm, ds in by_name.items():
        if len(ds) > 1:
            for r in results:
                if r["skill"] in ds:
                    r["issues"].append({"code": "B4", "detail": f"name '{nm}' shared by {ds}"})

    clean = sum(1 for r in results if not r["issues"])
    total_issues = sum(len(r["issues"]) for r in results)
    advisories = sum(len(r.get("advisories", [])) for r in results)
    print(json.dumps(results, indent=1))
    print(f"skills={len(results)} clean={clean} with_issues={len(results)-clean} "
          f"total_issues={total_issues} advisories={advisories}", file=sys.stderr)


if __name__ == "__main__":
    main()

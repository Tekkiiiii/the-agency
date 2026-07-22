#!/usr/bin/env python3
"""Agent-tools audit — mechanical checks over ~/.claude/agents/**/*.md.

Sibling to skill-audit.py; same style (argparse-free, JSON to stdout, summary
to stderr, Path-based). Report-only — this script NEVER edits agent files
(Wave 2 "NO blind mass-edit" directive, see memory/tasks/ongoing/
next-action-tools-restriction-propagation-waves.md).

Checks per agent file:
  1. has_tools_key      — frontmatter has a `tools:` key.
  2. has_modeltier_key  — frontmatter has a `modelTier:` key. Noted
                           inert/redundant in the 2026-07-07 audit
                           (~150 files expected). Report-only, no action.
  3. background_spawned — HEURISTIC. Greps ~/.claude/skills/, ~/.claude/
                           agents/, ~/.claude/runbooks/ for the agent's
                           `name:` frontmatter value or filename stem
                           appearing near a spawn marker (`Agent(`,
                           `subagent_type:`, `run_in_background: true`,
                           within a +/-3 line window). This is NOT ground
                           truth: indirect spawn sites (spawned via a
                           variable, a routing table, or a dynamically
                           built subagent_type string) will show up as
                           "unknown" or a false-negative "false". Treat
                           "true" as reliable; treat "false"/"unknown" as
                           "needs a human look before assuming dead code",
                           per Coord ACK_APPROACH note on F31.
  4. role_hint           — inferred from frontmatter `role:` (preferred
                           signal) with a filename/path fallback:
                           pd | coord | dept-coord | executor | specialist
                           | unknown.

Excludes: ~/.claude/agents-archive/ (sibling dir of ~/.claude/agents/,
naturally out of scope for the **/*.md walk, guarded anyway in case of
symlinks) and any path with a `state` directory component — state/*.md
files (active-coords.md, member-roster.md, dept-state.md, state/incoming/*)
are runtime logs, not agent definitions.

Output: JSON array to stdout (one object per agent file) + a summary line
to stderr.
"""
import json
import re
import sys
from pathlib import Path

AGENTS = Path("~/.claude/agents").expanduser()
CORPUS_DIRS = [
    Path("~/.claude/skills").expanduser(),
    Path("~/.claude/agents").expanduser(),
    Path("~/.claude/runbooks").expanduser(),
]

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

SPAWN_RE = re.compile(r"Agent\(|subagent_type\s*:|run_in_background\s*:\s*true", re.IGNORECASE)

# frontmatter `role:` value -> role_hint bucket
ROLE_MAP = {
    "project-director": "pd", "project_director": "pd",
    "dept-coord": "dept-coord",
    "coord": "coord", "mini-coord": "coord", "leader": "coord",
    "task-executor": "executor", "executor": "executor",
    "specialist": "specialist", "member": "specialist", "contract": "specialist",
    "integration-tester": "specialist", "delegator": "specialist", "protocol": "specialist",
}


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
    # naive fallback (no PyYAML): only pull the keys this script needs
    fm = {}
    m = re.search(r"^name:\s*(.+)$", raw, re.M)
    if m:
        fm["name"] = m.group(1).strip().strip('"').strip("'")
    m = re.search(r"^role:\s*(.+)$", raw, re.M)
    if m:
        fm["role"] = m.group(1).strip().strip('"').strip("'")
    if re.search(r"^tools:", raw, re.M):
        fm["tools"] = True
    if re.search(r"^modelTier:", raw, re.M):
        fm["modelTier"] = True
    return fm, None


def role_hint(fm, path):
    role = str((fm or {}).get("role") or "").strip().lower()
    if role in ROLE_MAP:
        return ROLE_MAP[role]
    stem = path.stem.lower()
    if stem.endswith("-pd") or "project-director" in stem:
        return "pd"
    if "dept-coord" in stem:
        return "dept-coord"
    if "coord" in stem:
        return "coord"
    if stem.startswith("exec-") or "executor" in stem:
        return "executor"
    if fm:
        return "specialist"
    return "unknown"


def is_excluded(path):
    parts = path.parts
    return "agents-archive" in parts or "state" in parts


def load_corpus(dirs):
    """One-time read of every .md file under the given dirs.

    Returns a list of (path, lines, lowercased-full-text) tuples. The
    lowercased full text lets us do a cheap substring pre-check before
    paying for a line-by-line window scan.
    """
    corpus = []
    seen = set()
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*.md"):
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            try:
                text = p.read_text(errors="replace")
            except Exception:
                continue
            corpus.append((p, text.splitlines(), text.lower()))
    return corpus


def check_background_spawned(name, stem, corpus, window=3):
    needles = [n for n in {name, stem} if n]
    if not needles:
        return "unknown"
    needles_lower = [n.lower() for n in needles]
    name_res = [re.compile(re.escape(n), re.IGNORECASE) for n in needles]
    seen_any_mention = False
    for _path, lines, lower_text in corpus:
        if not any(nl in lower_text for nl in needles_lower):
            continue  # cheap substring pre-check — skip line scan entirely
        for i, line in enumerate(lines):
            if any(r.search(line) for r in name_res):
                seen_any_mention = True
                lo, hi = max(0, i - window), min(len(lines), i + window + 1)
                if SPAWN_RE.search("\n".join(lines[lo:hi])):
                    return "true"
    return "false" if seen_any_mention else "unknown"


def main():
    files = sorted(p for p in AGENTS.rglob("*.md") if not is_excluded(p))
    corpus = load_corpus(CORPUS_DIRS)

    results = []
    no_tools_count = 0
    modeltier_count = 0
    bg_counts = {"true": 0, "false": 0, "unknown": 0}

    for p in files:
        text = p.read_text(errors="replace")
        fm, _err = parse_frontmatter(text)
        fm = fm or {}
        name = str(fm.get("name") or "").strip()
        has_tools = "tools" in fm
        has_modeltier = "modelTier" in fm

        if has_modeltier:
            modeltier_count += 1

        bg = "unknown"
        if not has_tools:
            no_tools_count += 1
            bg = check_background_spawned(name, p.stem, corpus)
            bg_counts[bg] += 1

        results.append({
            "path": str(p),
            "name": name or None,
            "has_tools_key": has_tools,
            "has_modeltier_key": has_modeltier,
            "background_spawned": bg,
            "role_hint": role_hint(fm, p),
        })

    print(json.dumps(results, indent=1))
    print(
        f"agent_files={len(results)} lacking_tools_key={no_tools_count} "
        f"(background_spawned true={bg_counts['true']} false={bg_counts['false']} "
        f"unknown={bg_counts['unknown']}) with_modeltier_key={modeltier_count}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

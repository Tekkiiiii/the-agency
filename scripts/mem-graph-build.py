#!/usr/bin/env python3
"""
mem-graph-build.py — build memory-graph.json + memory-graph.html from the
~/.claude memory estate, reusing graphify's own node-link schema and HTML
exporter (no custom visualizer — per memory-v2-target-architecture.html §6).

Scope (matches P1 schema-unification scope — two bundles, no per-project
memory/ dirs yet):
  - ~/.claude/memory/**/*.md                                 (global memory)
  - ~/.claude/projects/{cwd-slug}/memory/**/*.md              (auto-memory —
    Claude Code's per-cwd memory folder; slug = cwd path with "/" and "."
    replaced by "-", e.g. running from ~/.claude gives -Users-you--claude)

Frontmatter schema (P1, unified 2026-07-10): name/type/description/created/links

Edge sources — verified against the OKF v0.1 primary spec (2026-07-10,
GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md). OKF itself links via plain
markdown `[text](path.md)` in the body, not a frontmatter `links:` field and
not [[wikilinks]]. Our corpus uses neither OKF form: the `links:` frontmatter
field exists on 127 files but is `[]` (empty) on every one of them; the real,
populated cross-reference signal is [[wikilink]] tokens in "See also:" body
lines (~15+ files). Both are parsed below (links: for forward-compat + the R3
dead-link check the design doc calls for; wikilinks because that's what the
corpus actually uses). OKF-style body markdown links are NOT parsed — zero
real usage found in the corpus, not worth the code (YAGNI).

Broken link targets from either source are reported, never silently dropped
(OKF §9: "Consumers MUST tolerate broken links") -> memory/qa/dead-links.txt
"""
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

GRAPHIFY_SITE = str(Path.home() / ".local/share/uv/tools/graphifyy/lib/python3.12/site-packages")
sys.path.insert(0, GRAPHIFY_SITE)
import networkx as nx  # noqa: E402
from graphify.build import build_from_json  # noqa: E402
from graphify.export import to_html, to_json  # noqa: E402

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
# Claude Code auto-memory slug: cwd path with "/" and "." replaced by "-".
AUTO_MEMORY_SLUG = str(CLAUDE_DIR).replace("/", "-").replace(".", "-")
BUNDLES = [
    (CLAUDE_DIR / "memory", "global_memory"),
    (HOME / "projects" / AUTO_MEMORY_SLUG / "memory", "auto_memory"),
]
CONTROL_FILES = {"MEMORY.md", "index.md"}  # OKF-equivalent index files — not concept nodes
OUT_DIR = CLAUDE_DIR / "memory/graphify-out"
DEAD_LINKS_REPORT = CLAUDE_DIR / "memory/qa/dead-links.txt"

WIKILINK_RE = re.compile(r"\[\[([a-zA-Z0-9_\-]+)\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# graphify's node file_type is a closed enum: code/concept/document/image/paper/rationale.
# Our memory schema's `type` field (7 values, P1 2026-07-10: feedback/lesson/reference/
# note/project/user/registry) is a different, orthogonal taxonomy — map onto graphify's
# enum for the viewer; the original value is preserved in the node label/source_file.
FILE_TYPE_MAP = {
    "feedback": "rationale",
    "lesson": "rationale",
    "decision": "rationale",
    "reference": "document",
    "note": "document",
    "project": "document",
    "registry": "document",
    "user": "concept",
}


def graphify_file_type(our_type: str, bundle_type: str) -> str:
    return FILE_TYPE_MAP.get(our_type, "concept" if our_type == "user" else "document")


def slugify(stem: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", stem.lower())


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    lines = m.group(1).split("\n")
    fm, i = {}, 0
    while i < len(lines):
        kv = re.match(r"^([a-zA-Z_]+):\s*(.*)$", lines[i])
        if not kv:
            i += 1
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val == "[]":
            fm[key] = []
        elif val == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("- "):
            items = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(lines[i].lstrip()[2:].strip())
                i += 1
            fm[key] = items
            continue
        elif val.startswith("[") and val.endswith("]"):
            fm[key] = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
        else:
            fm[key] = val
        i += 1
    return fm


def collect():
    files = []
    for root, bundle_type in BUNDLES:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if p.name in CONTROL_FILES or "graphify-out" in p.parts:
                continue
            files.append((p, bundle_type))

    nodes, id_by_stem, seen = [], {}, set()
    raw = []  # (node, body_text, links_field)
    for p, bundle_type in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        stem = p.stem
        node_id = slugify(stem)
        if node_id in seen:
            node_id = slugify(f"{p.parent.name}_{stem}")
        seen.add(node_id)
        id_by_stem[stem] = node_id
        rel = str(p.relative_to(CLAUDE_DIR))
        our_type = fm.get("type", "")
        node = {
            "id": node_id,
            "label": fm.get("name", stem.replace("_", " ")),
            "file_type": graphify_file_type(our_type, bundle_type),
            "memory_type": our_type or bundle_type,
            "source_file": rel,
            "source_location": None,
            "source_url": None,
            "captured_at": fm.get("created"),
            "author": None,
            "contributor": None,
        }
        nodes.append(node)
        raw.append((node, text, fm.get("links", [])))

    edges, dead = [], []
    for node, text, links_field in raw:
        src = node["id"]
        for target in links_field:
            tslug = str(target).strip().strip("[]").strip()
            if not tslug:
                continue
            tid = id_by_stem.get(tslug) or id_by_stem.get(slugify(tslug))
            if tid:
                edges.append({
                    "source": src, "target": tid, "relation": "links_to",
                    "confidence": "EXTRACTED", "confidence_score": 0.9,
                    "source_file": node["source_file"], "weight": 1.0,
                })
            else:
                dead.append(f"{node['source_file']}: links: -> {tslug} (unresolved)")
        for wm in WIKILINK_RE.finditer(text):
            tslug = wm.group(1)
            tid = id_by_stem.get(tslug) or id_by_stem.get(slugify(tslug))
            if tid and tid != src:
                edges.append({
                    "source": src, "target": tid, "relation": "see_also",
                    "confidence": "EXTRACTED", "confidence_score": 0.9,
                    "source_file": node["source_file"], "weight": 0.8,
                })
            elif not tid:
                dead.append(f"{node['source_file']}: [[{tslug}]] (unresolved)")

    return nodes, edges, dead


def main():
    nodes, edges, dead = collect()
    extraction = {"nodes": nodes, "links": edges}
    G = build_from_json(extraction, directed=True)

    try:
        communities_raw = list(nx.community.greedy_modularity_communities(G.to_undirected()))
    except Exception:
        communities_raw = [set(G.nodes())]
    communities = {i: list(c) for i, c in enumerate(communities_raw)}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "memory-graph.json"
    html_path = OUT_DIR / "memory-graph.html"
    to_json(G, communities, str(json_path), force=True)
    to_html(G, communities, str(html_path))

    # Always write the report, even with 0 dead links — a stale report from a
    # prior run (with dead links) left on disk after they're fixed would make
    # downstream consumers (e.g. mem-scorecard.py's R3 check) see stale FAILs.
    DEAD_LINKS_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEAD_LINKS_REPORT.write_text(
        f"# Dead link report — {datetime.now(timezone.utc).isoformat()}\n"
        f"# {len(dead)} unresolved link(s) out of {len(nodes)} nodes\n\n"
        + "\n".join(sorted(dead)) + ("\n" if dead else "")
    )

    print(f"nodes={len(nodes)} edges={len(edges)} communities={len(communities)} dead_links={len(dead)}")
    print(f"json: {json_path}")
    print(f"html: {html_path}")
    print(f"dead-links report: {DEAD_LINKS_REPORT}")


if __name__ == "__main__":
    main()

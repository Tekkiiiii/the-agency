"""memory_scope.py — single source of truth for the P1 knowledge-memory
schema/scan boundary. Every script that mutates memory frontmatter OR counts/
scores memory files for the scorecard MUST import EXCLUDE_NAMES and
EXCLUDE_DIRS from here — never redefine them locally. That duplication is
exactly what caused the 2026-07-27 R4 scan-scope bug: mem-scorecard.py and
mem-graph-build.py rglob'd every subdirectory under memory/, including
sessions/, qa/, tasks/, inter-spawn-tasks/, agents/, and outputs/ — dirs that
memory-frontmatter-add.py's docstring already documented as "managed/log/
control, not knowledge memory" — so R4 could never reach 100% no matter how
much frontmatter migration ran, and nobody could tell from reading the code
that the two scripts disagreed about what "memory" even means.

Consumers: memory-frontmatter-add.py, memory-frontmatter-migrate.py,
mem-scorecard.py, mem-graph-build.py.
"""

# Hard-excluded filenames — mechanically owned by save-state.py / recall /
# pd-resume / mem-gardener.sh. Schema must never touch these (frontmatter
# would corrupt their control format), and they are never counted as
# in-scope "knowledge memory" for R2/R4 grading either — a control file
# failing R4 forever is not a real schema gap, it's a scope bug.
EXCLUDE_NAMES = {
    "next-session.md", "decisions.md", "decisions-archive.md", "heartbeat.md",
    "STATE.md", "PROJECT.md", "MEMORY.md", "wiki-log.md", "wiki-schema.md",
    "pd-scratch.md", "index.md", "README.md", "CLAUDE.md",
    # L0 integrity fixture — fixed content, SHA-256 byte-compared daily (R1).
    # Frontmatter would change its bytes and break the canary check.
    ".canary.md",
}

# Directory names that, anywhere in a file's path relative to a memory
# bundle root, mark it as managed/log/control content rather than knowledge
# memory: session transcripts, task-tracking files, inter-PD handoff queues,
# QA reports, agent executor scratch/archive, and misc output dumps.
EXCLUDE_DIRS = {
    "sessions", "tasks", "inter-spawn-tasks", "qa", "agents", "outputs",
}


# D6 review-by cadence (2026-07-27 decision, rationale in decisions.md) — per-type
# staleness horizon in days, applied as review-by = created + horizon. A locked
# brand fact and a tooling note do not age the same way, so this is deliberately
# NOT one global number:
#   project  (90d)  — point-in-time snapshot of active work, goes stale fastest
#   feedback (180d) — tactical/behavioral correction, often tied to a specific
#                      tool/API version that changes under it
#   note     (270d) — miscellaneous durable content, same order as lesson
#   lesson   (270d) — deeper structural pattern, more durable than feedback but
#                      still tied to specific stack/tool versions
#   reference(365d) — stable technical fact, changes only on structural shifts
#   user     (730d) — facts about Tekki himself (name, goals), rarely change
#   registry — EXEMPT, not point-in-time: registries are continuously
#              maintained live SSOT (R5 already bans embedded status text in
#              them), so "staleness" isn't the right frame for this type.
REVIEW_BY_HORIZON_DAYS = {
    "project": 90,
    "feedback": 180,
    "note": 270,
    "lesson": 270,
    "reference": 365,
    "user": 730,
    # "registry" deliberately absent -> exempt
}


def is_excluded(path, bundle_root) -> bool:
    """True if `path` (a pathlib.Path) is out of the knowledge-memory scan
    scope relative to `bundle_root` — by filename (EXCLUDE_NAMES) or by any
    path component between bundle_root and the file (EXCLUDE_DIRS)."""
    if path.name in EXCLUDE_NAMES:
        return True
    try:
        rel_parts = path.relative_to(bundle_root).parts[:-1]  # dirs only, not filename
    except ValueError:
        rel_parts = path.parts[:-1]
    return any(part in EXCLUDE_DIRS for part in rel_parts)

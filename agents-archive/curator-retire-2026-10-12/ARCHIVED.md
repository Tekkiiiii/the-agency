# curator agent - ARCHIVED 2026-10-12

Retired 2026-10-12 as part of the memory consolidation. Live source commits: ec49785 (agent archive,
every curator section removed from the PD defs) and ec1b3ac (structural spawn list in CLAUDE.md).

Files (byte-identical to their content before retirement):
- curator.specialized.md  (was agents/specialized/curator.md)
- curator.core.md         (was core/agents/curator.md, mirror of the above)

Replacement doctrine (runbooks/service-lookups.md, section "Project knowledge"):
- Project knowledge = direct lookups in order: wiki (MEMORY.md, memory files, project memory)
  -> a shared-memory MCP server, if you run one -> NotebookLM (research topics only).
- Multi-source synthesis = one read-only general-purpose (sonnet) spawn with that lookup order
  in its prompt. With the skill router on (AGENCY_SKILL_ROUTER=1) it is routed like any spawn.
- No curator agent anywhere. The metric events curator_skip / curator_spawn are retired
  (kept documented in runbooks/metrics-emit-contracts.md, no new emits).

Restore: `git mv agents-archive/curator-retire-2026-10-12/curator.specialized.md agents/specialized/curator.md`
and `git mv agents-archive/curator-retire-2026-10-12/curator.core.md core/agents/curator.md`, then re-add
the curator pair in scripts/core-mirror-check.py and the rows in the docs. Registration takes effect next session.

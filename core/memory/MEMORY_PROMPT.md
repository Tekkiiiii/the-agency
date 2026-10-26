# Memory System — Quick Reference

The Agency memory system uses typed files with YAML frontmatter and a central index.

| Type | Location | Trigger |
|------|----------|---------|
| `user` | `memory/` root | When operator preferences are learned |
| `feedback` | `memory/lessons/{stack}.md` | After any operator correction |
| `project` | `{project-root}/memory/` | On project state change or decision |
| `reference` | `memory/` root | When external resource locations are learned |

**Rules:**
- Append-only for lessons — never edit history
- Index every new file in `MEMORY.md` (one-line pointer, not content)
- Cross-link related files with `See also:` at the bottom
- Verify stale memories before acting on them

See `core/memory/MEMORY.md` for the full spec.

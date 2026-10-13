# Archived 2026-10-12

Retired in memory consolidation REV001: the Obsidian vault is no longer a memory or lookup step.
Lookup order is now: wiki (memory files) -> a shared-memory MCP server, if you run one -> NotebookLM (research topics only).

Source: skills repo commit f9adbc82 (live), mirrored here on 2026-10-13.
Moved, not deleted (vendor/agency files are additive-only). Wave: rev001-curator-2026-10-12.

Restore: `git mv agents-archive/rev001-curator-2026-10-12/skills/obsidian-vault skills/obsidian-vault`, then re-add its
`scripts/skill-route/overlay.json` entry and its row in `scripts/skill-registry/` metadata (or just regenerate `skills/INDEX.md`).

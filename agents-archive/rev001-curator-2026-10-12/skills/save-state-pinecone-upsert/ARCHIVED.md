# Archived 2026-10-12

`pinecone_upsert.py` was the optional Pinecone step of `/save-state`. Pinecone is retired as a memory/lookup step
(memory consolidation REV001). `skills/save-state/SKILL.md` no longer mentions it.

Source: skills repo commit f9adbc82 (live), mirrored here on 2026-10-13.
Moved, not deleted (additive-only). Wave: rev001-curator-2026-10-12.

Restore: `git mv agents-archive/rev001-curator-2026-10-12/skills/save-state-pinecone-upsert/pinecone_upsert.py skills/save-state/pinecone_upsert.py`.
Note: `scripts/save-state.py` (not owned by the skills tree) may still reference this file; see the cross-owner request in the batch report.

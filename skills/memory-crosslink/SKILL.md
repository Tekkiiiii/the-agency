---
name: memory-crosslink
description: "Use when writing or editing a memory file that relates to 2+ other memories: add See also: [[stem]] wikilinks so the wikilink edges resolve (the memory graph build was retired 2026-10-08; links remain the navigation structure). On-demand; moved out of CLAUDE.md."
---
# Memory cross-linking

When a memory relates to 2+ others, add `See also: [[target_file_stem]], [[other_target_stem]]` at the bottom: the target file's stem (no `.md`, no path) inside double brackets. Wikilinks are the cross-reference format checked by `/lint-memory`. Legacy `[Title](file.md)` links still resolve, but use `[[wikilinks]]` for new links.

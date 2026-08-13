# Skills Archive Manifest

Deprecated/retired skill definitions live here, **outside** `skills/` (top-level
sibling directory). `install.sh`, `install.ps1`, and `cli/commands/sync-assets.js`
copy every directory under `skills/` wholesale into the user's install — keeping
archived skills there would ship them as live, invokable skills again and defeats
the purpose of archiving them. `scripts/check-flat-skills.js` also guards the
`skills/` tree's directory-only layout, so archived skills must not live inside it.

## Restore-Beats-Create Rule

Before creating a new skill for a task, check this manifest first. If a matching
archived skill exists, restore it (move back to `skills/{name}/`, re-add its row
to `skills/INDEX.md`, and repoint any references back to it) rather than authoring
a new one from scratch.

## Archived Skills

| Skill | Date Archived | Reason | Restore Instructions |
|-------|---------------|--------|----------------------|
| `superpowers-verification-before-completion` | 2026-08-13 | Capability absorbed into the CLAUDE.md "Verification Before Done (evidence gate)" section — the skill's fresh-verification-before-DONE workflow is now enforced directly by the evidence gate, making the standalone skill redundant. | `git mv skills-archive/superpowers-verification-before-completion skills/superpowers-verification-before-completion`, re-add its row to `skills/INDEX.md` (Superpowers section, alphabetical order), then repoint the 12 live references (see CHANGELOG for the 2026-08-13 retirement entry) back to invoking `/superpowers-verification-before-completion` instead of the CLAUDE.md evidence gate. |

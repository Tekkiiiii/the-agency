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
| `compile` | 2026-08-13 | The skill was a preamble guard that loaded the `marketing-assessment-pipeline` skill's lessons, 24 learned pitfalls, and a quality checklist before running a client-deck pipeline. Archived because both of its two loaded dependencies — `marketing-assessment-pipeline/SKILL.md` and `memory/lessons/marketing-pipeline.md` — are absent from this repo's published tree, so 2 of its 3 load steps point at nothing and the skill cannot function on any fresh install. | `git mv skills-archive/compile skills/compile`, re-add its row to `skills/INDEX.md` (Engineering — Backend section, same position it came from). A real restore additionally requires either shipping the `marketing-assessment-pipeline` skill plus `memory/lessons/marketing-pipeline.md` in this repo, or rewriting `compile` to not depend on them. |

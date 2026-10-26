# Skills Index

Reusable workflow skills for Claude Code. Invoke with `/skill-name`.

> **What discovery actually depends on — read before "fixing" missing frontmatter.**
> A skill is discovered by its **location on disk**, not by its metadata: every code
> path in this repo (`cli/commands/sync-assets.js` `syncSkills()`, `skill.js`,
> `init.js`, `upgrade.js`, `scripts/check-flat-skills.js`) resolves a skill as
> `skills/<name>/SKILL.md` existing, and none of them parses frontmatter. This file
> is documentation only — it is copied verbatim to installs and never read
> programmatically. Per the Claude Code skills contract, all frontmatter fields are
> optional: the invocation command comes from the **directory name** (`name` is only
> a display label for personal/project skills), and an omitted `description` falls
> back to the first paragraph of the markdown body. A `SKILL.md` with no frontmatter
> is therefore still discoverable and still invokable — it is a quality wart (a
> weaker auto-invocation trigger), not a broken skill.
>
> The checks in `scripts/skill-audit.py` (A2 frontmatter present, A3 `name` present,
> A4 `name` matches directory) encode this repo's **house style**, which is stricter
> than the harness requires. Treat A2/A3/A4 hits as consistency debt to schedule, not
> as evidence that a skill is inert. The genuinely risky variant is a **malformed**
> block — an opening `---` with no closing `---`, or a `description:` containing an
> unquoted `:` — because that is a parse failure rather than a clean absence. Those
> are worth fixing ahead of the merely-absent ones.
>
> Related known gap: some skills carry valid frontmatter in a live install while the
> copy published here does not. Because `skills/` is deliberately absent from
> `core/.preserve`, a sync overwrites the install from this repo — so repairs must
> land **here**, or an upgrade will undo them.

With the skill router off (the default), this file is the menu: pick 1-3 skills from it.

**Generated, never hand-edited.** The tables below are written by
`python3 scripts/skill-registry.py` from the `skills/*/SKILL.md` files on disk, so this
list cannot drift from the tree and carries no count of its own. Grouping comes from the
router domains in `scripts/skill-route/overlay.json`. To change a row, change that skill's
`description` (or its overlay entry), then regenerate. The hand-kept parts are
`scripts/skill-registry/header.md` and `footer.md`.

# Agent Gaps Log

When a caller needs to spawn for a task and NO named agent covers it
(after checking delegator-cache → agency-dispatch → `_archived/MANIFEST.md`),
the caller MUST:

1. Append a row here (date, task pattern, agent created).
2. Create a minimal named agent def at `agents/specialized/{slug}.md`
   (frontmatter: name, description, restricted `tools:` list, model; body:
   short role prompt). Registration takes effect next session.
3. Spawn: if the new type resolves, use it. If it does not resolve yet
   (same-session registration lag), spawn the fallback ONCE with the new
   agent's role prompt inlined, and note "bridged" below.

Generalist spawns without a row here are a `generalist_ban_violation`.

| Date | Task pattern | Agent created | Bridged? |
|---|---|---|---|
| 2026-07-02 | (log initialized — no gaps yet) | — | — |

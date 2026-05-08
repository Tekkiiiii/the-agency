# The Agency Memory System

The Agency uses a **typed, indexed memory system** with YAML frontmatter and cross-linked files. Every agent reads from and writes to this system.

## Memory Types

| Type | Purpose | When to Save |
|------|---------|-------------|
| `user` | Operator preferences, role, constraints | When you learn details about the operator |
| `feedback` | Corrections, validated approaches, anti-patterns | On any correction OR confirmed non-obvious approach |
| `project` | Project state, decisions, status, deadlines | On project state changes or decisions |
| `reference` | Pointers to external resources | When you learn about external systems |

## Memory Index — MEMORY.md

Each project and the root agency directory has a `MEMORY.md` file that serves as an **index** — one-line pointers to individual memory files. Never write memory content directly into MEMORY.md.

Format:
```markdown
- [Title](filename.md) — one-line description (under 150 chars)
```

Lines after 200 in MEMORY.md may be truncated, so keep the index concise. Organize semantically by topic, not chronologically.

## File Format (YAML Frontmatter)

Each memory file must start with:

```yaml
---
name: short-name
description: one-line description — used to decide relevance, so be specific
type: user | feedback | project | reference
---

Memory content here.
```

For `feedback` and `project` types, structure the body as:

```markdown
The rule or fact.

**Why:** the reason or context behind it.
**How to apply:** when and where this guidance kicks in.
```

## Save Rules

- **Append immediately** after any correction from the operator — one-off mistake, clear root cause
- **Update or remove** memories that turn out to be wrong or outdated
- **Do not duplicate** — check if an existing memory can be updated before creating a new one
- **Convert relative dates** to absolute dates when saving (e.g., "Thursday" → "2026-03-05")
- **Update the MEMORY.md index** whenever a new file is created

## Access Rules

- Do NOT pre-load all memory files on every spawn
- Use trigger-based loading — read memory only when it seems relevant
- When acting on a memory, verify it's still correct by checking current file/resource state
- If a recalled memory conflicts with current information, trust what you observe now — update or remove the stale memory

## Cross-Linking

When a memory file relates to 2+ other memory files, add at the bottom:
```
See also: [Title A](file-a.md), [Title B](file-b.md)
```

## What NOT to Save

- Code patterns, conventions, architecture, file paths — derive from the codebase
- Git history or who-changed-what — use `git log` / `git blame`
- Debugging solutions — the fix is in the code, the context is in the commit message
- Anything already documented in CLAUDE.md files
- Ephemeral task details only useful within the current session

## Initialization

On first run, `agency init` creates:
```
{agency-root}/memory/
├── MEMORY.md          ← index (one-line pointers)
├── lessons/           ← per-stack lesson files (append-only)
└── agency-dispatch.md ← agent routing dispatch table
```

Do NOT create content in these directories — only the directory structure.

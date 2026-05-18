# Google Workspace — Slides

Google Slides read/write and batch updates via `gws`.

## When to Apply

- Creating Google Slides presentations programmatically
- Reading content from existing presentations
- Batch-updating slides (add shapes, text, images, reorder)
- Page/content operations on presentations

## Prerequisites

Read `../gws-shared/SKILL.md` for auth, global flags, and security rules.
If missing: `gws generate-skills`

## Usage

```bash
gws slides <resource> <method> [flags]
```

## Resources & Methods

**presentations:**
- `create` — Create a blank presentation with a title
- `get` — Get the latest version of a presentation
- `batchUpdate` — Apply multiple updates atomically (all-or-nothing validation)

**pages:** operations on individual slides/pages within presentations

## Discovery

```bash
gws slides --help
gws schema slides.<resource>.<method>
```

---

**Source:** https://officialskills.sh/googleworkspace/skills/gws-slides
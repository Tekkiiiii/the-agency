# Google Workspace — Forms

Google Forms creation, updates, and response collection via `gws`.

## When to Apply

- Creating or updating Google Forms programmatically
- Collecting and processing form responses
- Setting publish/visibility settings on forms

## Prerequisites

Read `../gws-shared/SKILL.md` for auth, global flags, and security rules.
If missing: `gws generate-skills`

## Usage

```bash
gws forms <resource> <method> [flags]
```

## Resources & Methods

**forms:**
- `create` — Create a new form (title only; add items via `batchUpdate`)
- `get` — Get a form
- `batchUpdate` — Add items, update form properties
- `setPublishSettings` — Update publish/visibility settings
- `responses` — Operations on form responses
- `watches` — Operations on form watches

## Discovery

```bash
# Browse resources and methods
gws forms --help

# Inspect a method's required params, types, defaults
gws schema forms.<resource>.<method>

# Use schema output to build --params and --json flags
```

---

**Source:** https://officialskills.sh/googleworkspace/skills/gws-forms
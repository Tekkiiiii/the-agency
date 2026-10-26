---
name: sync-md-json
description: "Use on \"sync index\", \"sync md-json\", \"sync to md\", \"sync to json\", or when index.json and index.md must match. Syncs a .json source of truth to its .md view (or back) with safe overwrite, keeping non-data markdown sections and ISO dates; JSON always wins, never merged."
---

# Sync MD-JSON

Syncs data between `.json` (source of truth) and `.md` (human-readable) files.
JSON is primary. On command, the target format overwrites with data from source.

## When Invoked

- User says "sync index" / "sync md-json" / "sync to md" / "sync to json"
- On-demand project status requested (sync status to JSON for compact storage)
- Any time you need to ensure both formats are in sync

## Sync Direction

**JSON → MD (default, most common):**
1. Read the `.json` file
2. Generate a readable Markdown table from it
3. Overwrite the `.md` file with the new content
4. Preserve any non-data sections (e.g., section headers, footnotes)

**MD → JSON (use when JSON is stale):**
1. Parse the Markdown table into structured data
2. Overwrite the `.json` file with the new data
3. Preserve schema fields not present in the Markdown

## Index File Conventions

Source of truth: `{project-root}/projects/index.json`
Derived: `{project-root}/projects/index.md`

Schema:
```json
{
  "version": 1,
  "updated": "YYYY-MM-DD",
  "pdInboxRoot": "path/to/inboxes/{team}/{pd-name}.json",
  "projects": [
    {
      "name": "string",
      "pd": "string|null",
      "path": "string|null",
      "stack": ["string"],
      "purpose": "string",
      "aliases": ["string"]
    }
  ]
}
```

## Markdown Output Format

Always use a table with these columns:
```
| Project | PD | Path | Stack | Purpose |
```

Archived entries go under `### Archived` section, not in the table.

## Key Rules

- JSON is the **authoritative source** — always prefer JSON for reads
- Only overwrite the target file, never merge and keep both
- Preserve `version` and `updated` fields on every JSON write
- Use ISO date format (YYYY-MM-DD) for all dates

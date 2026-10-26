# Active Projects Registry

The agency's project index: one row per project, the source of truth for project
paths. The installer seeds this file at `{agency-root}/memory/medium-term.md` (only if
it is absent) from the copy shipped at `core/memory/medium-term.md`; the seeded file
is the one that counts. `/recall`, `/pd-resume`, `/pd-spawn` and the spawn-log hooks
resolve a slug from it.

## Usage

- **`agency new <slug>`** and **project-scaffolder** (`/new-project`) append a row
  here, in `{agency-root}/memory/medium-term.md`.
- **recall / pd-resume / codebase-search** read this table to resolve a project slug
  to its path; **wrap** reads it (read-only) to check whether an inbox task belongs to
  an existing project.

Keep rows current: a stale or missing entry breaks slug-to-path resolution for every
skill above. Row format: ``| slug | `<project path>/memory/` | <slug>-pd | active |``.

## Active Projects

| Project | Memory Path | PD | Status |
|---------|-------------|----|--------|

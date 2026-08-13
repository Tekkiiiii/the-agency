# Active Projects Registry

The agency's project index — one row per active project, the source of truth
for project paths used by `codebase-search`, `wrap`, and `project-scaffolder`.

## Usage

- **project-scaffolder** appends a row here whenever `/new-project` creates a project.
- **codebase-search** reads this table to resolve a project slug to its path.
- **wrap** reads this table (read-only) to check whether an inbox task actually
  belongs to an existing project before treating it as ownerless.

Keep rows current — a stale or missing entry breaks slug-to-path resolution for
every skill above.

## Active Projects

| Project | Memory Path | PD | Status |
|---------|-------------|----|--------|

_Empty — rows accumulate as `/new-project` scaffolds new projects. See
`agents/specialized/project-scaffolder.md` §4c for the exact append format._

<purpose>
Show the project ideation pipeline — what's in projects/, what's ready to graduate, and what's already been graduated.
</purpose>

<user-story>
As a builder with multiple ideas in progress, I want to see which projects are in ideation, which are ready to graduate, and which have already moved to apps/, so that I can decide what to work on next.
</user-story>

<when-to-use>
- Want to see all projects in the pipeline
- Deciding which ideation to continue or graduate
- Checking if a project has already been graduated
</when-to-use>

<steps>

<step name="scan_projects" priority="first">
## Scan Pipeline

Scan `projects/` for directories containing `PLANNING.md`. For each project found, extract:

1. **Name** — directory name
2. **Type** — read Type metadata from PLANNING.md header
3. **Created** — file creation date of PLANNING.md
4. **Graduated** — check if PLANNING.md contains a `**Graduated:**` line at the bottom

Also check `apps/` for directories that match project names — these are graduated projects.

If `projects/` doesn't exist or is empty: "No projects in the pipeline. Run `/seed` to start one."
</step>

<step name="display_pipeline">
## Display Pipeline

Present results as a formatted table:

```
Project Pipeline
═══════════════════════════════════════════════════
Name              Type            Status
───────────────────────────────────────────────────
{name}            {type}          Ready for /seed graduate
{name}            {type}          Graduated → apps/{name}/
{name}            {type}          In progress (no Type yet)
═══════════════════════════════════════════════════
{N} projects | {M} ready to graduate | {K} graduated
```

**Status logic:**
- Has Type + content depth → "Ready for /seed graduate"
- Has graduation note → "Graduated → apps/{name}/"
- Missing Type or very thin → "In progress"

If any projects are ready to graduate, suggest: "Run `/seed graduate {name}` to move to apps/."
</step>

</steps>

<output>
- Formatted pipeline table displayed to user
- No files created or modified (read-only)
</output>

<acceptance-criteria>
- [ ] Scans projects/ for directories with PLANNING.md
- [ ] Extracts name, type, and graduation status per project
- [ ] Displays formatted pipeline table
- [ ] Identifies graduated projects (checks for graduation note)
- [ ] Read-only — does not modify any files
- [ ] Handles empty pipeline gracefully
</acceptance-criteria>

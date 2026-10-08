# Project Team Templates

Pre-defined team compositions for common project types. Use `TeamCreate` with these as reference.

> **Note 2026-10-08 (doctrine sync):** Only these department leads resolve as agents today:
> `engineering-lead`, `design-lead`, `content-creation-lead`, `critiques-lead`,
> `project-management-lead`, `specialized-lead`, `testing-lead`, `video-studio-lead`.
> `marketing-lead`, `sales-lead`, `paid-media-lead`, `product-lead`, `operations-lead` and
> `pm-lead` are archived (see `{agency-root}/agents-archive/MANIFEST.md`); `dept-*` member names
> (dept-frontend, dept-backend, ...) are not agents. Since the generalist switch (2026-10-06),
> staff those roles as `general-purpose` + 1-3 skills picked from
> `skills/INDEX.md`; old role names map to skills in
> `{agency-root}/agents-archive/ROLE-MAP.md`. Templates below keep the original rosters as role
> labels; read archived leads as roles to spawn that way.

---

## Template: Full Agency (All Departments)

**When**: Complex multi-domain projects, strategic initiatives, company-wide changes

```
Team: [project-name]-full
Members:
  - engineering-lead
  - design-lead
  - content-creation-lead
  - critiques-lead
  - project-management-lead
  - testing-lead
  - video-studio-lead
  - specialized-lead
  - council-chair (me)
```

---

## Template: Engineering-Heavy

**When**: Feature development, product builds, infrastructure projects

```
Team: [project-name]-engineering
Members:
  - engineering-lead
  - design-lead (if UX/UI involved)
  - project-management-lead
  - testing-lead
  - council-chair (me)
```

**Typical members added** (general-purpose + skills, not named agents):
- Frontend (Engineering): `/frontend`, `/tailwind`
- Backend (Engineering): `/backend`
- Security (Engineering): `/security`, `/cso`
- Project Management: `/persona-project-manager`, `/project-status`
- QA (Testing): `/qa-only`, `/benchmark`

---

## Template: Content Launch

**When**: Content campaigns, product launch assets, publishing programs

```
Team: [project-name]-content
Members:
  - content-creation-lead
  - design-lead (if creative assets needed)
  - specialized-lead (if reporting/analytics needed)
  - council-chair (me)
```

**Typical members added** (general-purpose + skills, not named agents):
- Growth / content: `/content-strategy`, `/copywriting`
- Analytics: `/chart-viz`, `/xlsx-toolkit`

Strategy, growth and sales work has no dedicated department; run it as `general-purpose` + skills (for example /content-strategy, /copywriting).

---

## Template: Custom

**When**: Focused projects with clear boundaries

Build from the department roster:

| Dept | Leader | Common Members (general-purpose + skills) |
|------|--------|--------------|
| Engineering | `engineering-lead` | frontend `/frontend`, backend `/backend`, AI `/claude-api`, security `/security`, devops `/github-deploy` |
| Design | `design-lead` | `/design-router`, `/ui-ux-pro-max`, `/brandkit`, `/impeccable` |
| Content Creation | `content-creation-lead` | `/content-creator`, `/copywriting`, `/seo-aeo-best-practices`, `/content-polish` |
| Critiques | `critiques-lead` | named `critique-*` agents |
| Project Management | `project-management-lead` | `/persona-project-manager`, `/project-status` |
| Testing | `testing-lead` | `/qa-only`, `/benchmark`, `/webapp-testing` |
| Video Studio | `video-studio-lead` | `/video-use`, `/ffmpeg`, `/hyperframes` |
| Specialized | `specialized-lead` | `/xlsx-toolkit`, `/legal-contract-review`, `/security` |
| Marketing, Sales, Paid Media, Product, Operations | archived | see `{agency-root}/agents-archive/MANIFEST.md` and ROLE-MAP.md |
| Spatial Computing, Game Development | archived 2026-06-25 | see `{agency-root}/agents-archive/MANIFEST.md` |

---

## Spawning Checklist

When creating a project team:

1. [ ] Select template or build custom roster
2. [ ] Identify project lead (usually me / council chair)
3. [ ] Send `council-assembly` to relevant leaders
4. [ ] Run kickoff brainstorming session
5. [ ] Create team with `TeamCreate`
6. [ ] Assign initial work packages
7. [ ] Set checkpoint cadence
8. [ ] Document in project kickoff summary
9. [ ] Announce team to human for awareness
10. [ ] Begin execution

---

## Disbanding a Project Team

When a project completes:

1. [ ] Verify all deliverables complete
2. [ ] Collect final status from all leaders
3. [ ] Send project completion report to human
4. [ ] Members: send `shutdown_request` to all members
5. [ ] Await `shutdown_response` from all
6. [ ] Delete team with `TeamDelete`
7. [ ] Archive project documentation

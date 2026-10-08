# Project Team Templates

Pre-defined team compositions for common project types. Use `TeamCreate` with these as reference.

---

## Template: Full Agency (All Departments)

**When**: Complex multi-domain projects, strategic initiatives, company-wide changes

```
Team: [project-name]-full
Members:
  - engineering-lead
  - design-lead
  - content-creation-lead
  - video-studio-lead
  - pm-lead
  - testing-lead
  - critiques-lead
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
  - pm-lead
  - testing-lead
  - specialized-lead (if infra or audit involved)
  - council-chair (me)
```

**Typical members added**:
- `dept-frontend` (Engineering)
- `dept-backend` (Engineering)
- `dept-security` (Engineering)
- `dept-pm` (Project Management)
- `dept-qa` (Testing)

---

## Template: Content Launch

**When**: Content campaigns, product launch assets, publishing programs

```
Team: [project-name]-content
Members:
  - content-creation-lead
  - design-lead (if creative assets needed)
  - video-studio-lead (if video needed)
  - critiques-lead
  - pm-lead
  - council-chair (me)
```

**Typical members added**:
- `dept-content` (Content Creation)
- `dept-social` (Content Creation)
- `dept-seo` (Content Creation)

Strategy, growth and sales work has no dedicated department; run it as `general-purpose` + skills (for example /content-strategy, /copywriting).

---

## Template: Custom

**When**: Focused projects with clear boundaries

Build from the department roster:

| Dept | Leader | Common Members |
|------|--------|--------------|
| Engineering | `engineering-lead` | `dept-frontend`, `dept-backend`, `dept-ai`, `dept-security`, `dept-mobile`, `dept-devops`, `dept-data` |
| Design | `design-lead` | `dept-ui`, `dept-ux`, `dept-brand`, `dept-visual` |
| Content Creation | `content-creation-lead` | `dept-content`, `dept-seo`, `dept-social` |
| Video Studio | `video-studio-lead` | See `agents/video-studio/INDEX.md` |
| Project Management | `pm-lead` | `dept-shepherd`, `dept-studio-ops`, `dept-experiments` |
| Testing | `testing-lead` | `dept-evidence`, `dept-benchmark`, `dept-accessibility`, `dept-api` |
| Critiques | `critiques-lead` | `critique-*` agents (see `agents/critiques/INDEX.md`) |
| Specialized | `specialized-lead` | `dept-orchestrator`, `dept-audit`, `dept-infra` |

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

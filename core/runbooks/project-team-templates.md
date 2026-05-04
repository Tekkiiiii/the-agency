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
  - marketing-lead
  - sales-lead
  - paid-media-lead
  - product-lead
  - pm-lead
  - testing-lead
  - operations-lead
  - specialized-lead
  - spatial-computing-lead
  - game-development-lead
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
  - product-lead
  - pm-lead
  - testing-lead
  - operations-lead (if infra involved)
  - council-chair (me)
```

**Typical members added**:
- `dept-frontend` (Engineering)
- `dept-backend` (Engineering)
- `dept-security` (Engineering)
- `dept-pm` (Project Management)
- `dept-qa` (Testing)

---

## Template: Go-to-Market

**When**: Product launches, campaigns, customer acquisition initiatives

```
Team: [project-name]-gtm
Members:
  - marketing-lead
  - sales-lead
  - paid-media-lead
  - product-lead
  - design-lead (if creative assets needed)
  - operations-lead (if reporting/analytics needed)
  - council-chair (me)
```

**Typical members added**:
- `dept-growth` (Marketing)
- `dept-content` (Marketing)
- `dept-ppc` (Paid Media)
- `dept-sales` (Sales)
- `dept-analytics` (Operations)

---

## Template: Game Development

**When**: Game projects, interactive experiences, spatial computing

```
Team: [project-name]-games
Members:
  - game-development-lead
  - design-lead
  - engineering-lead
  - testing-lead
  - spatial-computing-lead (if AR/VR involved)
  - product-lead
  - pm-lead
  - council-chair (me)
```

---

## Template: Custom

**When**: Focused projects with clear boundaries

Build from the department roster:

| Dept | Leader | Common Members |
|------|--------|--------------|
| Engineering | `engineering-lead` | `dept-frontend`, `dept-backend`, `dept-ai`, `dept-security`, `dept-mobile`, `dept-devops`, `dept-data` |
| Design | `design-lead` | `dept-ui`, `dept-ux`, `dept-brand`, `dept-visual` |
| Marketing | `marketing-lead` | `dept-content`, `dept-growth`, `dept-seo`, `dept-social` |
| Sales | `sales-lead` | `dept-deals`, `dept-pipeline`, `dept-outbound`, `dept-discovery` |
| Paid Media | `paid-media-lead` | `dept-ppc`, `dept-tracking`, `dept-creative`, `dept-programmatic` |
| Product | `product-lead` | `dept-trends`, `dept-feedback`, `dept-behavior` |
| Project Management | `pm-lead` | `dept-shepherd`, `dept-studio-ops`, `dept-experiments` |
| Testing | `testing-lead` | `dept-evidence`, `dept-benchmark`, `dept-accessibility`, `dept-api` |
| Operations | `operations-lead` | `dept-finance`, `dept-compliance`, `dept-analytics` |
| Specialized | `specialized-lead` | `dept-orchestrator`, `dept-audit`, `dept-infra` |
| Spatial Computing | `spatial-lead` | `dept-xr`, `dept-visionos`, `dept-apple-platform` |
| Game Development | `game-lead` | Engine-specific leads and members |

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

# Project Team Templates

Pre-defined team compositions for common project types. Use `TeamCreate` with these as reference.

> **Note 2026-10-08 (dept sunset):** There is no department layer. A project team is a PD, one or more Coords, and `general-purpose` Execs staffed with 1-3 skills picked with
> `python3 {agency-root}/scripts/skill-route.py "<task>"`; old role names map to skills in
> `{agency-root}/agents-archive/ROLE-MAP.md`. Only the `critique-*` agents (spawned by PD/Coord or via `/cc-loop`) and the structural agents (`coord`, `mini-coord`, `pd-coordinator`, `{slug}-pd`) resolve as named agents. Rosters below are role labels with skills, not agent names.

---

## Template: Full Agency (All Domains)

**When**: Complex multi-domain projects, strategic initiatives, company-wide changes

```
Team: [project-name]-full
Members (role label -> general-purpose + skills):
  - engineering      /frontend, /backend, /security
  - design           /design-router, /ui-ux-pro-max
  - content          /content-creator, /copywriting
  - critique         critique-* agents via /cc-loop
  - project-mgmt     /persona-project-manager, /project-status
  - testing          /qa-only, /benchmark
  - video            /video-use, /ffmpeg
  - specialized      /xlsx-toolkit, /legal-contract-review
  - council-chair (me)
```

---

## Template: Engineering-Heavy

**When**: Feature development, product builds, infrastructure projects

```
Team: [project-name]-engineering
Members:
  - engineering      Execs (see below)
  - design           (if UX/UI involved)
  - project-mgmt
  - testing
  - council-chair (me)
```

**Typical members** (general-purpose + skills, not named agents):
- Frontend: `/frontend`, `/tailwind`
- Backend: `/backend`
- Security: `/security`, `/cso`
- Project Management: `/persona-project-manager`, `/project-status`
- QA (Testing): `/qa-only`, `/benchmark`

---

## Template: Content Launch

**When**: Content campaigns, product launch assets, publishing programs

```
Team: [project-name]-content
Members:
  - content          Execs (pipeline: content-request-protocol.md)
  - design           (if creative assets needed)
  - video            (if video needed; content-to-video-protocol.md)
  - critique         critique-* agents via /cc-loop
  - project-mgmt
  - council-chair (me)
```

**Typical members** (general-purpose + skills, not named agents):
- Content / SEO / social: `/content-creator`, `/copywriting`, `/seo-aeo-best-practices`
- Analytics: `/chart-viz`, `/xlsx-toolkit`

Strategy, growth and sales work has no dedicated team (marketing, sales, paid-media,
product and operations are archived); run it as `general-purpose` + skills (for
example `/content-strategy`, `/inbound-sales`).

---

## Template: Custom

**When**: Focused projects with clear boundaries

Build from the role roster (each row = `general-purpose` + skills):

| Domain | Common skills |
|------|--------------|
| Engineering | frontend `/frontend`, backend `/backend`, AI `/claude-api`, security `/security`, devops `/github-deploy` |
| Design | `/design-router`, `/ui-ux-pro-max`, `/brandkit`, `/impeccable` |
| Content | `/content-creator`, `/copywriting`, `/seo-aeo-best-practices`, `/content-polish` |
| Critiques | named `critique-*` agents (via `/cc-loop` or spawned directly) |
| Project Management | `/persona-project-manager`, `/project-status` |
| Testing | `/qa-only`, `/benchmark`, `/webapp-testing` |
| Video | `/video-use`, `/ffmpeg`, `/hyperframes` |
| Specialized | `/xlsx-toolkit`, `/legal-contract-review`, `/security` |
| Marketing, Sales, Paid Media, Product, Operations | archived - see `{agency-root}/agents-archive/MANIFEST.md` and ROLE-MAP.md |
| Spatial Computing, Game Development | archived 2026-06-25 - see `{agency-root}/agents-archive/MANIFEST.md` |

---

## Spawning Checklist

When creating a project team:

1. [ ] Select template or build custom roster
2. [ ] Identify project lead (usually me / council chair)
3. [ ] Send `council-assembly` to the participating PD / Coords
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
2. [ ] Collect final status from all Coords / Execs
3. [ ] Send project completion report to human
4. [ ] Members: send `shutdown_request` to all members
5. [ ] Await `shutdown_response` from all
6. [ ] Delete team with `TeamDelete`
7. [ ] Archive project documentation

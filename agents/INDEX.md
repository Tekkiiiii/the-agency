# The Agency — Agent Directory

Navigate to the department that fits your task. Each department has its own `INDEX.md` listing all members.

## Departments

| Department | Directory | Use when you need... |
|---|---|---|
| [Engineering](engineering/INDEX.md) | `engineering/` | Code, APIs, infrastructure, security, DevOps, mobile, AI/ML |
| [Design](design/INDEX.md) | `design/` | UI, UX, branding, visual storytelling, creative direction |
| [Game Development](game-development/INDEX.md) | `game-development/` | Games, interactive experiences, game audio, level/narrative design |
| [Marketing](marketing/INDEX.md) | `marketing/` | Growth strategy, social media engagement, SEO, China market |
| [Content Creation](content-creation/INDEX.md) | `content-creation/` | Written content of any type — blogs, social copy, ads, email, scripts, docs, decks |
| [Sales](sales/INDEX.md) | `sales/` | Pre-sale discovery, deal strategy, outbound, proposals |
| [Paid Media](paid-media/INDEX.md) | `paid-media/` | Google/Meta ads, PPC, programmatic, display, paid social |
| [Product](product/INDEX.md) | `product/` | Roadmap, prioritization, user research, feedback analysis |
| [Project Management](project-management/INDEX.md) | `project-management/` | Sprint planning, project coordination, studio ops |
| [Testing](testing/INDEX.md) | `testing/` | QA, performance, accessibility, API testing, audits |
| [Operations](operations/INDEX.md) | `operations/` | Analytics, finance, infrastructure, legal/compliance, support |
| [Specialized](specialized/INDEX.md) | `specialized/` | Agents infra, audits, data extraction, web extraction/crawling, ZK knowledge, Vietnamese text processing, misc |
| [Spatial Computing](spatial-computing/INDEX.md) | `spatial-computing/` | AR/VR/XR, visionOS, Metal, Apple platform spatial |
| [Critiques](critiques/INDEX.md) | `critiques/` | Scored critique of any deliverable — design, content, marketing, pedagogy, SEO, product, security, brand |
| [Video Studio](video-studio/INDEX.md) | `video-studio/` | All video production — scripted or AI-generated. Pre-production, production, post-production, distribution, QA |

## Department Coordination (Dept-Coord System)

Each department has a Dept-Coord agent for department-operational work (pipeline management, protocol improvement, member development). See [ORG.md § Department Operations](ORG.md) for the full architecture.

| Dept-Coord Agent | Department | File |
|-----------------|-----------|------|
| career-coord | Career | `career/career-coord.md` |
| content-creation-coord | Content Creation | `content-creation/content-creation-coord.md` |
| design-coord | Design | `design/design-coord.md` |
| engineering-coord | Engineering | `engineering/engineering-coord.md` |
| game-development-coord | Game Development | `game-development/game-development-coord.md` |
| marketing-coord | Marketing | `marketing/marketing-coord.md` |
| operations-coord | Operations | `operations/operations-coord.md` |
| paid-media-coord | Paid Media | `paid-media/paid-media-coord.md` |
| product-coord | Product | `product/product-coord.md` |
| project-management-coord | Project Management | `project-management/project-management-coord.md` |
| sales-coord | Sales | `sales/sales-coord.md` |
| spatial-computing-coord | Spatial Computing | `spatial-computing/spatial-computing-coord.md` |
| specialized-coord | Specialized | `specialized/specialized-coord.md` |
| testing-coord | Testing | `testing/testing-coord.md` |
| video-studio-coord | Video Studio | `video-studio/video-studio-coord.md` |

## Runbooks

- [Department Lead Protocol](runbooks/department-lead-protocol.md) — how dept leaders communicate
- [Dept-Coord Protocol](runbooks/dept-coord-protocol.md) — full dept-coord operational manual
- [Dept Boot Sequence](runbooks/dept-boot-sequence.md) — two-mode dept head startup
- [Protocol Registry](runbooks/protocol-registry.md) — cross-department protocol index
- [Escalation Protocol](runbooks/escalation-protocol.md) — Tier 1/2/3 decision routing
- [Content Request Protocol](runbooks/content-request-protocol.md) — how content gets requested, produced, and distributed
- [Project Kickoff Protocol](runbooks/project-kickoff-protocol.md) — how to spin up a project team
- [Project Team Templates](runbooks/project-team-templates.md) — pre-built team compositions
- [Content → Video Protocol](runbooks/content-to-video-protocol.md) — script handoff from Content Creation to Video Studio, end-to-end video pipeline
- [Quality Loop Protocol](runbooks/quality-loop-protocol.md) — agency-wide quality gate protocol; quality-loop-router is the terminal step for all creative pipelines

## Reference

- [ORG.md](ORG.md) — full org chart, leadership table, council protocol, dept-coord system
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add new agents

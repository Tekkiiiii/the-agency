# The Agency — Agent Directory

Each folder below holds structural agents (PD homes, Coord defs, critics, council seats, service agents) with its own `INDEX.md`.

## Folders

| Folder | Directory | Use when you need... |
|---|---|---|
| [Design](design/INDEX.md) | `design/` | Design quality principles and design PD homes |
| [Project Management](project-management/INDEX.md) | `project-management/` | Coord, mini-coord and pd-coordinator definitions |
| [Specialized](specialized/INDEX.md) | `specialized/` | Service agents (delegator, codebase-search, save-state-runner, project-scaffolder) |
| [Critiques](critiques/INDEX.md) | `critiques/` | Scored critique of any deliverable — design, content, marketing, pedagogy, SEO, product, security, brand |
| [Council](council/INDEX.md) | `council/` | Independent read-only opinions on a decision brief (tier seats, optional Codex seat) |

## Routing

Work routes PD -> Coord -> general-purpose Exec (spawner picks model + 1-3 skills); critics (`critique-*`) are spawned directly by the PD or Coord. The folders above are PD homes (PD definitions + the few kept files), not teams. See [core/ORG.md](../core/ORG.md).

## Runbooks

- [Escalation Protocol](../runbooks/escalation-protocol.md) — Tier 1/2/3 decision routing
- [Content Request Protocol](../runbooks/content-request-protocol.md) — how content gets requested, produced, and distributed
- [Project Kickoff Protocol](../runbooks/project-kickoff-protocol.md) — how to spin up a project team
- [Project Team Templates](../runbooks/project-team-templates.md) — pre-built team compositions
- [Quality Loop Protocol](../runbooks/quality-loop-protocol.md) — agency-wide quality gate protocol; quality-loop-router is the terminal step for all creative pipelines

## Reference

- [council/](council/) — council seats (council-fable, council-opus, council-sonnet, council-haiku): read-only opinion agents for BOD/council; protocol in `{agency-root}/core/memory/agency-council.md`
- [core/ORG.md](../core/ORG.md) — org chart (PD -> Coord -> Exec), council seats

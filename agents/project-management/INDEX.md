# Project Management — PD home

This folder is a home for Project Director (PD) agent definitions and the Coord agent definitions (`coord.md`, `mini-coord.md`, `pd-coordinator.md`). Work routes PD -> Coord -> general-purpose Exec (spawner picks model + skills); critics (`critique-*`) are spawned directly by the PD or Coord.

**Call these roles when you need to orchestrate work across teams** — sprint planning, project coordination, timeline management, Jira/Git workflow enforcement, studio operations, experiment tracking (A/B tests), and multi-project portfolio management.

## Members

Spawn each of these roles as `general-purpose` + the listed skills.

| Role | Spawn as | What it does |
|---|---|---|
| studio producer | general-purpose + /project-status | Multi-project portfolio orchestration, creative-technical alignment |
| project shepherd | general-purpose + /project-status | Cross-functional coordination, timeline management, stakeholder alignment |
| jira workflow steward | general-purpose + /superpowers-finishing-a-development-branch, /ship | Jira-linked Git workflows, traceable commits, PR structure |
| senior project manager | general-purpose + /superpowers-writing-plans | Spec-to-task conversion, scope management, project memory |
| studio operations | general-purpose + /project-status | Day-to-day efficiency, process optimization, resource coordination |
| experiment tracker | general-purpose + /content-experimentation-best-practices, /project-status | A/B test design, hypothesis validation, experiment execution |

### Registered orchestrators

| Agent | What it does |
|---|---|
| PD Coordinator | Tiered orchestrator for all PDs — L1→L2→L3 decomposition, spawns Coords, aggregates results |
| Coord | Autonomous mid-tier agent — L3→smallest decomposition, spawns Execs (general-purpose + Skills), manages to completion |

## Parent Directory

[← Agency Directory](../INDEX.md)

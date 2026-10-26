# Specialized — PD home and service agents

This folder is a home for Project Director (PD) agent definitions plus the agency's service agents. Work routes PD -> Coord -> general-purpose Exec (spawner picks model + skills); critics (`critique-*`) are spawned directly by the PD or Coord.

## Members

Any other role is a `general-purpose` Exec with 1-3 skills from `skills/INDEX.md`. Rows below are the agents that ship.

| Agent | What it does |
|---|---|
| Example Project PD | Project Director for a specific product/app — one PD is spawned per active project via `/new-project` (see Project Scaffolder) |
| Delegator | Routing agent: knows the agents, skills, protocols and pipelines; guides a caller to the right agent and skills. Read-only |
| Save-State Runner | One-project save-state reconstructor for subagent mode (`/save-state all`, crash recovery) |
| Project Scaffolder | Autonomous project + PD scaffolding agent — creates all files and registries for /new-project |
| Codebase Search | Fast read-only file/symbol search across {agency-root}/, projects, and skill library — replaces Explore for system searches |


## Parent Directory

[← Agency Directory](../INDEX.md)

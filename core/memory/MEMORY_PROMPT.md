# Memory System

The Agency maintains persistent memory across sessions:

| Layer | Location | Created By | Read By |
|---|---|---|---|
| Sessions | `~/.agency/sessions/{project}/` | `/save-state` | Next session agent |
| State | `~/.agency/projects/{project}/STATE.md` | PD | PD, team-lead |
| Lessons | `~/.agency/lessons/{stack}.md` | Agents after corrections | Any agent |
| Decisions | `~/.agency/decisions/` | Team-lead | Team-lead, agents |

On spawn: check `~/.agency/projects/{project}/STATE.md` for current context.
On correction: append lesson to `~/.agency/lessons/{stack}.md`.
On session end: run `/save-state` to persist session log.

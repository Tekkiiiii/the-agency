# Memory System

The Agency maintains persistent memory across sessions:

| Layer | Location | Created By | Read By |
|---|---|---|---|
| Sessions | `~/.claude/sessions/{project}/` | `/save-state` | Next session agent |
| State | `~/.claude/projects/{project}/STATE.md` | PD | PD, team-lead |
| Lessons | `~/.claude/lessons/{stack}.md` | Agents after corrections | Any agent |
| Decisions | `~/.claude/decisions/` | Team-lead | Team-lead, agents |

On spawn: check `~/.claude/projects/{project}/STATE.md` for current context.
On correction: append lesson to `~/.claude/lessons/{stack}.md`.
On session end: run `/save-state` to persist session log.

# Persona leftovers - ARCHIVED 2026-10-15

Owner ruling: "archive them or turn them into skill if possible". The live model is the generalist
agent plus the skills the spawner picks, with a flat roster of structural agents only. The files here
were the last pieces of the named-persona era. Moved with `git mv`, old relative path kept, nothing
deleted. No file carried reusable method that a skill does not already cover, so none was converted.

| Archived path (under this folder) | What it was | Replaced by |
|---|---|---|
| `agents/README.md` | upstream persona catalog README (install and per-tool setup) | top-level `README.md` |
| `agents/CONTRIBUTING.md` | how to author a new named persona | `skill-creator` and `docs/DEVELOPER.md` |
| `agents/integrations/**` | per-tool (Cursor, Aider, Windsurf, Gemini CLI, ...) outputs of the converter, plus empty pipeline and protocol registries | none (tool-conversion of a persona catalog) |
| `agents/scripts/convert.sh`, `agents/scripts/install.sh` | converted persona agent files to other tools and installed them | none |
| `core/agents/TEAM_LEAD.md`, `core/agents/SPECIALIST.md` | persona-era pattern templates | Exec spawn message in `agents/project-management/coord.md` |
| `agents/{content-creation,engineering,testing,video-studio}/INDEX.md` | PD-home indexes of dirs that hold no agent | `agents/INDEX.md` |

Kept in place (still referenced): `agents/scripts/lint-agents.sh` (CI), `agents/scripts/room-utils.sh` and
`agents/scripts/flock.py` (rooms protocol), `agents/ORG.md`, `agents/agent-gaps.md`.

## Credit and licence

The persona catalog these files came from is derived from `msitarzewski/agency-agents`
(https://github.com/msitarzewski/agency-agents), MIT licence, copyright its authors. The credit
is also kept in the top-level `README.md` (Credits).

## Restore

For each row: `git mv agents-archive/persona-retire-2026-10-15/<path> <path>` (same relative path).
For the dir rows move the whole folder. Then re-add the dept rows to `agents/INDEX.md`. A restored
INDEX.md makes `lint-agents.sh` and `check-counts.py` count that dir as a department again.
Installs pick the .md files up on the next `agency upgrade`; non-.md files (convert.sh, install.sh,
setup.sh) are never installed or pruned.

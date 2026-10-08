---
name: PD Boot Sequence
description: Standard startup sequence for all Project Directors. Two-mode: thin discover on spawn, lazy routing on demand.
type: template
owner: agency-council
lastUpdated: 2026-10-08
---

# PD Boot Sequence

## Philosophy

- **On spawn**: read as little as possible — one project briefing doc, not 10 INDEX files
- **On demand**: load routing tables only when you need them, not before
- **Skills first**: pick 1-3 skills from `skills/INDEX.md`, spawn general-purpose; structural agents by name only

---

## Mode 1: Spawn (do this every time)

**Target context cost: ~600 tokens max**

**Step 1:** Read briefing from spawn prompt. pd-resume passes next-session.md content
inline -- no file reads needed. If spawned manually without a briefing, read:
```
{project}/memory/next-session.md
```

**Step 2:** Read active tasks:
```
{project}/memory/tasks/ongoing/
```

**Step 2b:** Read structural contract (if it exists):
```
{project}/memory/pd-structure.md
```
If this file does not exist and the project has active L3 Coord work, create it now
using the schema in pd-coordinator.md § Structural Oversight. Takes 2 minutes, saves
hours of cross-L3 conflict resolution later.

**Step 3:** Proceed with your role.

---

## Mode 2: Route (do this when you need to delegate)

**Target context cost: load only what you need**

**Step 1:** Check the PD-BRIEFING doc for a pre-written routing entry for this task type.

**Step 2:** If not in briefing, pick 1-3 skills yourself from `skills/INDEX.md` (no per-dept catalog loads).

**Step 3:** Delegate per Agent Dispatch Priority below. Spawn `general-purpose` (model sonnet) with 1-3 named skills in the prompt (`Skills: /x, /y`). Only structural agents spawn by name (see Agent Dispatch Priority step 2 below).

---

## Agent Dispatch Priority (reference — don't load on spawn)

```
1. Does the PD-BRIEFING list a specific agent or skill set for this task?
   YES → use it
   NO  → step 2

2. Is it a structural role ({slug}-pd, pd-coordinator, coord, mini-coord, task-executor,
   dept head / dept-coord, critique-* critic, Delegator, curator, codebase-search,
   save-state-runner, project-scaffolder)?
   YES → spawn that agent by name
   NO  → step 3

3. Is this a workflow task (planning, verification, QA, retro)?
   YES → use a skill from ~/.claude/skills/INDEX.md
   NO  → step 4

4. Is it knowledge work (analysis, research, planning, memory/state writes)?
   YES → do it directly
   NO  → implementation: delegate to an Exec (atomic, independent) or a Coord, as
         general-purpose + 1-3 skills from skills/INDEX.md;
         PD QAs direct-Exec results itself (pd-coordinator.md §Role). PD never implements.
```

Old specialist role names (backend-architect, frontend-developer, etc.) no longer resolve as
`subagent_type` (generalist switch 2026-10-06). Map any old role name to skills via
`{agency-root}/agents-archive/ROLE-MAP.md`. Never spawn an archived role name.

---

## Department Routing (reference — don't load on spawn)

Live departments: content-creation, critiques, design, engineering, integrations,
project-management, specialized, testing, video-studio. Departments are routing
labels, not spawn catalogs: pick skills from `skills/INDEX.md`, then spawn general-purpose.

| Task | Department | Skill pick |
|---|---|---|
| Frontend / backend / DB / CI-CD | engineering | skills (e.g. /frontend, /backend) |
| QA / accessibility / performance | testing | skills (e.g. /qa-only, /benchmark) |
| UI design / brand / visual | design | skills (e.g. /design-router) |
| Content writing / copy / editorial | content-creation | skills (e.g. /content-creator) |
| Content strategy / social / growth | content-creation | skills (e.g. /content-strategy, /copywriting) |
| Project scheduling | project-management | skills or `pd-coordinator` / `coord` |
| Data extraction / compliance / research | specialized | skills from `skills/INDEX.md` |

Marketing, marketing/china and sales are not live departments (archived); see ROLE-MAP.md.

---

## PD-BRIEFING Template

Create at `{project}/.claude/PD-BRIEFING.md`:

```markdown
# PD Briefing — [project-name]
Last updated: [date]
PD: [pd-name]

## This Project's Agents

| Task | Skills (general-purpose) or structural agent | Department |
|---|---|---|
| [task type] | [/skill-a, /skill-b or agent name] | [dept] |

## Department Contacts

| Department | Who to Tag |
|---|---|
| Engineering | `@engineering-lead` |
| Design | `@design-lead` |
| Testing | `@testing-lead` |
| Content Creation | `@content-creation-lead` |
| Critiques | `@critiques-lead` |
| Project Management | `@project-management-lead` |
| Video Studio | `@video-studio-lead` |
| Specialized | `@specialized-lead` |

## Active Priorities
- [top 2-3 priorities from current session]

## Known Blockers
- [any blockers with owner]
```

**The PD-BRIEFING is the only file read on every spawn.** Build it once per project, update it when priorities shift. This is the key to staying under 500 tokens on spawn.

---

## How to Apply to a New PD

1. Create the PD-BRIEFING doc at `{project}/.claude/PD-BRIEFING.md`
2. Paste Mode 1 (Spawn) + Mode 2 (Route) into the PD agent file, before `## Identity`
3. Paste Agent Dispatch Priority as a reference block (no file reads on spawn)
4. Paste Department Routing table as a reference block (lazy load only)

Total text added to PD agent file: ~60 lines. No file reads on spawn. Routing tables are reference, not runtime-loaded.

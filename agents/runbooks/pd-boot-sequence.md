---
name: PD Boot Sequence
description: Standard startup sequence for all Project Directors. Two-mode: thin discover on spawn, lazy routing on demand.
type: template
owner: agency-council
lastUpdated: 2026-04-01
---

# PD Boot Sequence

## Philosophy

- **On spawn**: read as little as possible — one project briefing doc, not 10 INDEX files
- **On demand**: load routing tables only when you need them, not before
- **Agents first**: check for a department agent before anything else

---

## Mode 1: Spawn (do this every time)

**Target context cost: ~500 tokens max**

**Step 1:** Read briefing from spawn prompt. pd-resume passes next-session.md content
inline -- no file reads needed. If spawned manually without a briefing, read:
```
{project}/memory/next-session.md
```

**Step 2:** Read active tasks:
```
{project}/memory/tasks/ongoing/
```

**Step 3:** Proceed with your role.

---

## Mode 2: Route (do this when you need to delegate)

**Target context cost: load only what you need**

**Step 1:** Check the PD-BRIEFING doc for a pre-written routing entry for this task type.

**Step 2:** If not in briefing, load the relevant department INDEX:
```
{agency-root}/agents/{department}/INDEX.md
```
Only load the one department you need. Not all 8.

**Step 3:** Spawn the agent directly. Use SendMessage to the department lead if you need them to dispatch.

---

## Agent Dispatch Priority (reference — don't load on spawn)

```
1. Does the PD-BRIEFING list a specific agent for this task?
   YES → spawn it directly
   NO  → step 2

2. Does a department INDEX list an agent for this task?
   YES → spawn from that department
   NO  → step 3

3. Is this a workflow task (planning, verification, QA, retro)?
   YES → use a skill from {agency-root}/skills/INDEX.md
   NO  → step 4

4. Can you do it directly (Tier 1: <10 line edits, docs, analysis)?
   YES → do it
   NO  → escalate
```

---

## Department Agent Routing (reference — don't load on spawn)

Load the relevant INDEX.md only when routing, not on every spawn.

| Task | Department | File to Load |
|---|---|---|
| Frontend / React / Next.js | engineering | `engineering/INDEX.md` |
| Backend / Rust / Tauri | engineering | `engineering/INDEX.md` |
| Database / SQL | engineering | `engineering/INDEX.md` |
| CI/CD / DevOps | engineering | `engineering/INDEX.md` |
| QA / testing | testing | `testing/INDEX.md` |
| Accessibility | testing | `testing/INDEX.md` |
| Performance | testing | `testing/INDEX.md` |
| UI design | design | `design/INDEX.md` |
| Brand / visual | design | `design/INDEX.md` |
| Content writing / copy / editorial | content-creation | `content-creation/INDEX.md` |
| Content strategy / social / growth | marketing | `marketing/INDEX.md` |
| China market | marketing/china | `marketing/china/INDEX.md` |
| Sales strategy | sales | `sales/INDEX.md` |
| Project scheduling | project-management | `project-management/INDEX.md` |
| Data extraction | specialized | `specialized/INDEX.md` |
| Cultural intelligence | specialized | `specialized/INDEX.md` |
| Compliance / legal | specialized | `specialized/INDEX.md` |

---

## PD-BRIEFING Template

Create at `{project}/.claude/PD-BRIEFING.md`:

```markdown
# PD Briefing — [project-name]
Last updated: [date]
PD: [pd-name]

## This Project's Agents

| Task | Agent | Department |
|---|---|---|
| [task type] | [agent name] | [dept] |

## Department Contacts

| Department | Who to Tag |
|---|---|
| Engineering | `@engineering-lead` |
| Design | `@design-lead` |
| Testing | `@testing-lead` |
| Marketing | `@marketing-lead` |
| Sales | `@sales-lead` |
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
4. Paste Department Agent Routing table as a reference block (lazy load only)

Total text added to PD agent file: ~60 lines. No file reads on spawn. Routing tables are reference, not runtime-loaded.

# Project Kickoff Protocol

How to spin up a project team, assemble the agency council for brainstorming, and transition into execution.

---

## When to Use This Protocol

Use this when:
- A new project is being started
- A significant new phase of an existing project begins
- A complex cross-domain problem needs structured analysis
- The human or parent AI calls a council assembly

---

## Step 1: Determine Project Scope

Before assembling the council, establish:

1. **What is the project?** One-paragraph description
2. **What domains are involved?** Not every project needs every domain
3. **What is the timeline?** Urgency affects council size and depth
4. **Who is the project lead?** May be the parent AI or a designated council member

### Domain Involvement Guide

Each domain is staffed as `general-purpose` Execs + skills under a Coord (see `project-team-templates.md`); there is no department layer.

| Project Type | Required Domains |
|-------------|---------------|
| Feature development | Engineering, Testing |
| Full product build | Engineering, Design, Testing, PM |
| Content launch | Content Creation, Design, Video Studio, Critiques |
| Customer-facing feature | Engineering, Design, Support, Testing |
| Infrastructure | Engineering, PM, Testing |
| Content/campaign | Content Creation, Design, Video Studio |
| Analysis/report | Specialized, PM |

---

## Step 2: Assemble the Council

1. Identify which domains are relevant to the project
2. Brief the participating PD / Coords (or council seats, see `agents/council/`) with a `council-assembly` message:

```
TYPE: council-assembly
PURPOSE: project-kickoff
PROJECT: [project name]
SCOPE: [brief description]
DOMAINS_NEEDED: [list]
TIMELINE: [urgency/timeline]
PROJECT_LEAD: [me or designated PD]
---
[Full project brief]
```

3. Wait for participants to acknowledge
4. If a needed participant is unavailable, they may send a delegate or provide async input

---

## Step 3: Brainstorming Session

The council convenes to analyze the problem from multiple angles.

### Participant Input Format

Each participant (PD / Coord / council seat) should contribute:

```
FROM: [participant]
DOMAIN: [domain]
---
**What [my domain] sees in this problem:**
[Perspective, risks, opportunities from your domain]

**What [my domain] needs to succeed:**
[Requirements, dependencies, inputs from other domains]

**What [my domain] can deliver:**
[Concrete contributions, timelines, scope]

**Key risks I see:**
[Domain-specific risks to flag]

**Questions for other participants:**
[Any cross-domain questions or assumptions to validate]
```

### Synthesis (Parent AI)

After all participants have contributed, I synthesize:

1. **Shared understanding** — what the project actually is
2. **Cross-domain dependencies** — who needs what from whom
3. **Conflicting priorities** — where domains disagree
4. **Risk map** — technical, design, business, timeline risks
5. **Work breakdown** — who does what, in what order
6. **Escalation plan** — what needs human approval upfront

---

## Step 4: Project Team Formation

Based on the brainstorm:

1. **Create a project team** with `TeamCreate`
   - Include the relevant PD / Coords + me as project lead
   - Or designate one PD as project lead

2. **Define the project team channels**:
   - Project channel: all project team members
   - Domain channels: Coord + its Execs within the project

3. **Assign initial tasks**:
   - Each Coord receives its work package
   - Coords assign to Execs
   - Dependencies are explicit in task assignments

4. **Establish checkpoint cadence**:
   - Daily standups for fast projects
   - Weekly for longer projects
   - Ad-hoc for blockers

---

## Step 5: Transition to Execution

Once the project team is formed and tasks are assigned:

1. Council brainstorming channel closes (or moves to async)
2. Project team channel activates for daily coordination
3. Coords / PDs report progress to me via project team
4. Cross-domain blockers escalate to me for resolution
5. Tier 3 escalations surface to human with project context

---

## Project Team Templates

### Full Agency (template-full-team)

All domains (Coords + Execs). Use for: complex multi-domain projects, strategic initiatives, company-wide changes.

### Engineering-Heavy (template-engineering-team)

Engineering + PM + Testing + Design. Use for: feature development, product builds, technical projects.

### Content Launch (template-content-team)

Content + Design + Video + Critiques (`critique-*` via `/cc-loop`). Use for: launches, campaigns, content programs.

### Custom (template-custom-team)

Select domains as needed. Use for: focused projects with clear boundaries.

---

## Handoff to Execution

When transitioning from kickoff to execution, document:

```markdown
# Project: [Name] — Kickoff Summary

## Problem Statement
[One paragraph]

## Council Participants
| Domain | Owner | Contribution |
|------|--------|-------------|
| [domain] | [name] | [what they'll deliver] |

## Work Packages
| Domain | Work Package | Deadline | Dependencies |
|------|-------------|----------|-------------|
| [domain] | [description] | [date] | [depends on] |

## Escalations to Human
- [ ] [action needed — approve before work begins]
- [ ] [action needed — approve before work begins]

## Risks
| Risk | Domain | Likelihood | Mitigation |
|------|------|-----------|------------|
| [risk] | [domain] | [H/M/L] | [plan] |

## Checkpoint Cadence
[Daily/Weekly] — [day/time]
```

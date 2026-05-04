# Project Kickoff Protocol

How to spin up a project team, assemble the agency council for brainstorming, and transition into execution.

---

## When to Use This Protocol

Use this when:
- A new project is being started
- A significant new phase of an existing project begins
- A complex cross-department problem needs structured analysis
- The human or parent AI calls a council assembly

---

## Step 1: Determine Project Scope

Before assembling the council, establish:

1. **What is the project?** One-paragraph description
2. **What departments are involved?** Not every project needs every dept
3. **What is the timeline?** Urgency affects council size and depth
4. **Who is the project lead?** May be the parent AI or a designated council member

### Department Involvement Guide

| Project Type | Required Depts |
|-------------|---------------|
| Feature development | Engineering, Product, Testing |
| Full product build | Engineering, Design, Product, Testing, PM |
| Go-to-market launch | Marketing, Sales, Paid Media, Product |
| Customer-facing feature | Engineering, Design, Product, Support, Testing |
| Infrastructure | Engineering, PM, Testing |
| Content/campaign | Marketing, Design, Sales |
| Analysis/report | Product, Operations, Sales |

---

## Step 2: Assemble the Council

1. Identify which dept leaders are relevant to the project
2. Send a `council-assembly` broadcast to those leaders:

```
TYPE: council-assembly
PURPOSE: project-kickoff
PROJECT: [project name]
SCOPE: [brief description]
DEPARTMENTS_NEEDED: [list]
TIMELINE: [urgency/timeline]
PROJECT_LEAD: [me or designated leader]
---
[Full project brief]
```

3. Wait for leaders to acknowledge participation
4. If a needed dept leader is unavailable, they may send a delegate or provide async input

---

## Step 3: Brainstorming Session

The council convenes to analyze the problem from multiple angles.

### Leader Input Format

Each leader should contribute:

```
FROM: [dept-lead]
DEPARTMENT: [dept]
---
**What [my dept] sees in this problem:**
[Perspective, risks, opportunities from your domain]

**What [my dept] needs to succeed:**
[Requirements, dependencies, inputs from other depts]

**What [my dept] can deliver:**
[Concrete contributions, timelines, scope]

**Key risks I see:**
[Domain-specific risks to flag]

**Questions for other leaders:**
[Any cross-dept questions or assumptions to validate]
```

### Synthesis (Parent AI)

After all leaders have contributed, I synthesize:

1. **Shared understanding** — what the project actually is
2. **Cross-dept dependencies** — who needs what from whom
3. **Conflicting priorities** — where depts disagree
4. **Risk map** — technical, design, business, timeline risks
5. **Work breakdown** — who does what, in what order
6. **Escalation plan** — what needs human approval upfront

---

## Step 4: Project Team Formation

Based on the brainstorm:

1. **Create a project team** with `TeamCreate`
   - Include relevant dept leaders + me as project lead
   - Or designate one leader as project lead

2. **Define the project team channels**:
   - Project channel: all project team members
   - Dept channels: leader + their members within the project

3. **Assign initial tasks**:
   - Each dept leader receives their work package
   - Leaders assign to members
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
3. Leaders report progress to me via project team
4. Cross-dept blockers escalate to me for resolution
5. Tier 3 escalations surface to human with project context

---

## Project Team Templates

### Full Agency (template-full-team)

All dept leads + members. Use for: complex multi-domain projects, strategic initiatives, company-wide changes.

### Engineering-Heavy (template-engineering-team)

Engineering + Product + PM + Testing + Design leads + members. Use for: feature development, product builds, technical projects.

### Go-to-Market (template-gtm-team)

Sales + Marketing + Paid Media + Product + Design leads + members. Use for: launches, campaigns, customer acquisition.

### Custom (template-custom-team)

Select depts as needed. Use for: focused projects with clear boundaries.

---

## Handoff to Execution

When transitioning from kickoff to execution, document:

```markdown
# Project: [Name] — Kickoff Summary

## Problem Statement
[One paragraph]

## Council Participants
| Dept | Leader | Contribution |
|------|--------|-------------|
| [dept] | [name] | [what they'll deliver] |

## Work Packages
| Dept | Work Package | Deadline | Dependencies |
|------|-------------|----------|-------------|
| [dept] | [description] | [date] | [depends on] |

## Escalations to Human
- [ ] [action needed — approve before work begins]
- [ ] [action needed — approve before work begins]

## Risks
| Risk | Dept | Likelihood | Mitigation |
|------|------|-----------|------------|
| [risk] | [dept] | [H/M/L] | [plan] |

## Checkpoint Cadence
[Daily/Weekly] — [day/time]
```

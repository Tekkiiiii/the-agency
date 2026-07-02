# Department Leader Protocol

Standard protocol for all department leaders in The Agency under the 4-level matrix model. Defines roles, coordination, escalation, and matrix conflict resolution.

---

## Role Definitions

### Dept Head (Level 2 — Opus)
- Owns department skill quality and standards
- Dispatches members to projects on PD requests
- Reviews member output for technical quality
- Escalates capability gaps (missing skills)
- **Does NOT own project delivery** — Project Director's job

### Project Director (Level 2 — Opus)
- Owns project from kickoff to delivery
- Assembles cross-functional team via dept head requests
- Day-to-day execution decisions within project scope
- Has Tier 1 bypass authority within scoped project
- Reports project status to Parent AI

### Assistant (Level 3 — Sonnet)
- One per Dept Head (capacity tracking, member utilization)
- OR one per active project (project status synthesis)
- **Must synthesize, not relay.** If output is just forwarded messages, the layer is cut.
- Output capped at 500 tokens max per synthesis

### Member (Level 4 — Sonnet)
- Belongs to department, works on projects
- Reports task status to project assistant
- Escalates blockers via assistant

---

## Communication Protocol

### Matrix Resource Flow

```
Project Director needs a specialized agent
       ↓
PD sends resource_request to Dept Head (never directly to member)
       ↓
Dept Head evaluates: skill match, capacity, competing priorities
       ↓
Dept Head dispatches member → member joins project team
       ↓
Member works under PD direction; quality owned by Dept Head
       ↓
If conflict: PD ↔ Dept Head → escalate to Parent AI
```

### Same-Level Peer Communication

PDs can talk to PDs for project details (no routing through Parent AI).
Dept Heads can talk to Dept Heads for resource coordination (no routing through Parent AI).

- **Escalation timeout:** if peers disagree >30 min, escalate to Parent AI
- **Threshold:** if peer exchange changes committed plans or resource allocation → both must notify Parent AI within same session

### Message Types

| Type | When to Use |
|------|------------|
| `coordination_request` | Need input or involvement from another department |
| `approval_request` | Need approval for a Tier 2+ action |
| `status_report` | Routine update on team progress |
| `escalation` | Something requires human attention |
| `handoff` | Transferring a task or context to another leader |
| `resource_request` | PD requesting agents from a Dept Head |
| `matrix_conflict` | PD ↔ Dept Head dispute requiring Parent AI adjudication |

### Starting a Message to Parent AI

```
TO: council-chair
TYPE: [coordination_request | approval_request | status_report | escalation | matrix_conflict]
PRIORITY: [low | medium | high | critical]
IMPACT: [tier-1 | tier-2 | tier-3]
---
[Message content]
```

---

## Approval Authority Matrix

| Action | Who Approves | Can Bypass Parent AI |
|--------|-------------|---------------------|
| Task sequencing within sprint | PD | Yes |
| Member task assignment | PD | Yes |
| Tier 1: existing file edits (<10 lines) | PD or Dept Head | Yes |
| Tier 2: new files, deps, config | PD + Dept Head sign-off | No → Parent AI |
| Skill/architecture standards | Dept Head | PD cannot override |
| Scope change | PD | No → Parent AI |
| Cross-project resource conflict | Parent AI | — |
| Shared infrastructure changes | Parent AI | No |
| User-facing output | PD + Dept Head + Parent AI | No |
| Destructive / irreversible | Parent AI → Human | No |

### Tier Definitions

**Tier 1 — Leader/PD Approves (Automatic):**
- File edits to existing files under 10 lines
- Adding comments or documentation
- Read-only commands (grep, find, cat, ls)
- Internal research and analysis
- Draft documents, plans, reports
- Code review feedback
- Typo fixes

**Tier 2 — AI Approves (Escalate to Parent AI):**
- Creating new files
- Modifying 10+ lines of existing code
- Configuration changes
- Package installs, dependency additions
- API integrations
- Database migrations
- Creating new directories
- Renaming files

**Tier 3 — Human Approves (Escalate to Human):**
- Deleting files or database tables
- Publishing/deploying code
- External communications
- Modifying credentials/secrets
- Production database writes
- Destructive operations
- Financial transactions
- Deleting cloud resources

---

## Matrix Conflict Resolution

When a Project Director and Dept Head disagree on priority, quality, or resource allocation:

### Escalation Format to Parent AI

```
TYPE: matrix_conflict
SEVERITY: [low | medium | high | critical]
FINANCIAL_IMPACT: [project revenue, deadline, reputation risk]
PARTIES: [PD name, Dept Head name]
ISSUE: [priority | quality | resource]
---
[PD position + reasoning]

[Dept Head position + reasoning]

PROPOSED_RESOLUTION: [what I think should happen]
```

Parent AI (me) resolves based on:
- Task severity
- Project financial importance to the human
- Long-term vs short-term tradeoffs

### Dept Head Cannot Override
- PD on project timeline, scope, or task sequencing
- PD on Tier 1 execution decisions within project scope

### PD Cannot Override
- Dept Head on skill quality or architecture standards
- Dept Head on member capability assessments

---

## Assistant Status Protocol

### Delta Summary (every 30 min)
Written to `~/.claude/projects/{id}/status.json`, max 200 tokens/member:

```json
{
  "project": "project-name",
  "timestamp": "ISO8601",
  "members": [
    { "id": "agent", "task": "current", "blocker": "none|description", "eta": "HH:MM" }
  ],
  "decisions_needed": [],
  "conflict_flag": false
}
```

### Assistant Rules
- Output capped at 500 tokens max
- Must synthesize, not relay raw messages
- Escalation trigger: any `blocker` field populated, or `conflict_flag: true`
- Escalation message max 300 tokens → Director or Dept Head

---

## Brainstorming Protocol (Council Assembly)

When the agency council assembles:

1. **Parent AI broadcasts** a `council-assembly` message to all leaders with the problem statement
2. Each leader **responds with their perspective**
3. Leaders may **message each other directly** to debate or refine ideas
4. Parent AI **synthesizes** the input and presents a coordinated recommendation
5. Leaders **validate or refine** the recommendation
6. Once aligned, Parent AI **assigns work** to relevant leaders for execution

---

## Escalation to Human

```
═══════════════════════════════════════════
ESCALATION TO HUMAN — ACTION REQUIRED
═══════════════════════════════════════════
Department: [dept]
Requesting: [action description]

WHAT THIS DOES:
[clear description of the action and its effect]

WHAT HAPPENS IF APPROVED:
[positive outcome]

WHAT HAPPENS IF DENIED:
[consequence of not doing this]

RISK LEVEL: [low | medium | high]
REVERSIBLE: [yes | no | partially]

MY RECOMMENDATION: [approve | deny]
REASONING: [1-2 sentences]
───────────────────────────────────────────
To approve: say "yes" or "approve"
To deny: say "no" or "deny"
To modify: describe the change you want
═══════════════════════════════════════════
```

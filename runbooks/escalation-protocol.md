# Escalation Protocol

How leaders escalate decisions up the chain — from leader autonomy to AI review to human approval.

---

## The Escalation Chain

```
MEMBER (Level 4)
      │
      ▼ (reports via assistant)
PROJECT ASSISTANT (Level 3) ── synthesis ──► PROJECT DIRECTOR (Level 2)
                                                         │
DEPT ASSISTANT (Level 3) ◄── synthesis ◄── DEPT HEAD (Level 2)
                                                         │
                                                         ▼
                                                  PARENT AI (Level 1)
                                                         │
                                                         ├─► TIER 1: Independent (no action needed)
                                                         ├─► TIER 2: Reviews and approves/denies
                                                         └─► TIER 3: Surfaces to human with recommendation
```

**Matrix conflict path:** Project Director ↔ Dept Head disagree → both escalate to Parent AI with `matrix_conflict` type. Parent AI adjudicates based on severity + financial importance.

---

## When to Escalate to Parent AI (Tier 2)

Escalate when the action is:

- **New file creation** — any new file, not just code
- **Code modifications over 10 lines** — cumulative or single change
- **Dependency changes** — npm install, pip install, adding libraries
- **Configuration changes** — .env, config files, settings
- **Database changes** — schema changes, migrations
- **API integrations** — connecting to new external services
- **Pipeline changes** — CI/CD modifications
- **Deployment configurations** — Docker, Kubernetes, server configs

### Escalation Message Format

```
TYPE: approval_request
DEPARTMENT: [dept]
ACTION: [what you want to do]
FILES_AFFECTED: [list files or "new file(s)"]
LINES_CHANGED: [approximate or "N/A for new file"]
REASON: [why this is needed]
RISK: [low | medium | high]
TIER: 2
---
[Additional context, code snippets, or justification]
```

### Approval Response Format (from me)

```
TYPE: approval_response
DECISION: [approved | denied | approved_with_conditions]
DEPARTMENT: [dept]
CONDITIONS: [if applicable — what must be met]
REASONING: [brief justification]
---
[If denied: alternative approach or next steps]
```

---

## When to Escalate to Human (Tier 3)

Escalate when the action is:

- **Destructive** — deletes data, files, infrastructure
- **Irreversible** — cannot easily undo
- **External-facing** — sends messages, publishes content, creates PRs
- **Credential-related** — modifies secrets, API keys, passwords
- **Financial** — any monetary transaction
- **Permission-related** — changes access control, roles, authorization
- **Production-impacting** — affects live systems, customers, revenue

### Escalation to Human Format

```
═══════════════════════════════════════════
⚠️  ESCALATION TO HUMAN — ACTION REQUIRED
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

### Human Response Handling

When human approves:
- Execute the action immediately
- Report completion to the dept lead
- Log the approval in the escalation record

When human denies:
- Inform the dept lead
- Proceed without the action
- If the denial blocks critical work, escalate further context

When human modifies:
- Incorporate the modifications
- Re-confirm if the modification itself requires approval

---

## Escalation Response Expectations

| Tier | Expected Response Time |
|------|----------------------|
| Tier 1 | Immediate — decide and act |
| Tier 2 | Within session — wait for my response before proceeding |
| Tier 3 | Human availability — do not block; continue other Tier 1/2 work while waiting |

---

## Delegation Budget

Leaders have an implicit **delegation budget** — they can act autonomously on Tier 1 without notifying me, but should keep me informed of overall team activity through periodic `status_report` messages.

**Recommended status report cadence:**
- Weekly: summary of completed tasks, active tasks, blockers
- Ad-hoc: when hitting a blocker that requires cross-dept coordination

---

## Edge Cases

**What if I (parent AI) am unavailable?**
- Leaders operate within Tier 1 autonomy
- Tier 2 actions are queued — leaders proceed with caution and document
- Tier 3 actions wait until availability returns

**What if a member escalates directly to me instead of to their leader?**
- I will route the message back to the appropriate leader
- Members should always go through their dept lead first

**What if two leaders disagree on a cross-dept task?**
- Leaders negotiate directly first
- If unresolved after reasonable effort, either leader escalates to me
- I mediate and make a final decision

---

## Matrix Conflict Resolution

In the matrix model, conflicts between Project Directors and Dept Heads follow a specific escalation path.

### When a Conflict Occurs

1. **PD and Dept Head negotiate directly** for up to 30 minutes
2. **If unresolved:** either party escalates to Parent AI with `matrix_conflict` type
3. **Parent AI adjudicates** based on severity + financial importance

### Matrix Conflict Escalation Format

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

### Conflict Types and Resolution Rules

| Issue | Dept Head Wins | PD Wins | Escalate to Parent AI |
|-------|---------------|---------|----------------------|
| Skill quality / architecture | ✓ | — | If PD disputes |
| Project timeline / scope | — | ✓ | If it affects skill standards |
| Member priority (which project) | — | — | Always escalate |
| Resource conflict (same member) | — | — | Always escalate |
| Tier 1 execution decisions | — | ✓ | If Dept Head disputes |

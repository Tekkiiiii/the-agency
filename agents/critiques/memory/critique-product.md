# critique-product — Critic Memory

Append-only lesson log. Read at the start of every critique session. Never delete or rewrite entries.
Each entry captures one lesson: what worked, what was a blind spot, what wasted rounds.

Format:
## YYYY-MM-DD — brief title
3-8 lines of specific insight from that run.

---

## 2026-06-10 — Internal approval tool redesign, multi-role workflow

For internal B2B tools where the primary flow is approval (not creation), the highest-severity findings cluster around process integrity: unguarded destructive actions (Reject without confirmation) and premature commit actions (Approve without view). These are almost always present in first-round mockups because designers focus on the happy path.
Bilingual internal tools: always check that language-switch controls in the header actually match the scope of translation. Partial bilingual labeling (only some fields translated inline) should not be a global toggle — that sets false user expectations.
Raw database IDs leaking into user-facing screens (Node: role_1780644718478) are a reliable finding for tools built quickly on top of workflow engines. Always scan meta/subtitle areas.
The "focus list" pattern on dashboards needs explicit role-based framing: "needs your action" vs "your work in flight" are different audiences using the same screen, and mixing them without a visual group creates cognitive load for the approver persona.
When the BEFORE and AFTER screenshots appear identical, the redesign may be working from the same codebase — compare HTML structure (not just visuals) to understand what actually changed.
A "required reason dialog" annotation in small muted text is documentation, not a guard — always check whether the constraint is enforced in the interaction, not just described nearby. Approve remaining unguarded while Reject/Revision got dialogs created an asymmetry caught in R2.
Round-2 rescores from 74→88 are realistic for a tight one-round iteration that addressed all CRITICAL/HIGH findings. Terminal columns (Rejected, Archived) rendered empty by default are a reliable MEDIUM finding on any board-style tool.

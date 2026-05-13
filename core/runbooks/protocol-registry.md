---
name: Protocol Registry
description: Cross-department protocol index. Single source of truth for all protocols that span two or more departments. Dept Heads reference this before creating or modifying any cross-dept protocol.
type: runbook
owner: agency-council
lastUpdated: 2026-05-14
---

# Protocol Registry

## Purpose

This file is the single source of truth for every protocol that involves two or more departments. When a dept head creates, modifies, or deprecates a cross-department protocol, this registry is the canonical record.

Any protocol listed here has passed cross-dept sign-off and is considered active agency policy. Protocols not listed here are either internal to one department (and documented in that dept's `protocols/` directory) or are not yet approved.

---

## Registry

| Protocol | Owner Dept | Participants | Version | Status | File Path |
|---|---|---|---|---|---|
| content-request | content-creation | marketing | v1.0 | active | `agents/content-creation/protocols/content-request.md` |
| marketing-content-handoff | marketing | content-creation | v1.0 | active | `agents/marketing/protocols/marketing-content-handoff.md` |

**Column definitions:**
- **Protocol** — machine-readable slug, kebab-case, unique across the registry
- **Owner Dept** — the department that maintains and evolves the protocol
- **Participants** — other departments that consume or implement the protocol
- **Version** — semver, starts at v1.0 on first activation
- **Status** — `proposed` | `testing` | `active` | `deprecated`
- **File Path** — relative to `~/.agency/`, always the owner dept's `protocols/` directory

---

## Protocol Lifecycle

```
proposed → testing → active → deprecated
```

### proposed
- Owner dept drafts the protocol file in their `protocols/` directory.
- Owner dept head notifies all participant dept heads.
- No team may rely on a proposed protocol as a dependency.

### testing
- Both (or all) participant dept heads have reviewed and signaled agreement.
- Protocol is piloted on one initiative or pipeline cycle.
- Bugs and gaps are logged as open issues in the owner dept's state.

### active
- Testing cycle complete. No blocking issues.
- Row added to this registry (or status updated from `testing`).
- All participant depts update their members to follow the protocol.

### deprecated
- One or more dept heads proposes replacement or removal.
- Status updated to `deprecated` in this registry.
- File remains in place for audit trail. Do NOT delete.
- Replacement protocol (if any) listed in the deprecated file's header.

---

## How to Add a Protocol

1. Create the protocol file in the owning dept's `protocols/` directory:
   ```
   ~/.agency/agents/{owner-dept}/protocols/{protocol-slug}.md
   ```

2. Notify all participant dept heads via SendMessage with:
   ```
   TYPE: coordination_request
   SUBJECT: New cross-dept protocol — {protocol-slug}
   STATUS: proposed
   FILE: ~/.agency/agents/{owner-dept}/protocols/{protocol-slug}.md
   ---
   [Brief description and request for review]
   ```

3. Once both dept heads signal agreement (in writing, via SendMessage), update status to `testing` in the protocol file header.

4. After a successful testing cycle, add a row to this registry and update the protocol file's status to `active`.

5. Notify all participant dept heads of activation.

---

## How to Modify an Active Protocol

1. Owner dept head drafts the changes in the protocol file.
2. Bump the version (e.g. v1.0 → v1.1 for minor, v1.0 → v2.0 for breaking).
3. Notify all participant dept heads — same `coordination_request` format as above.
4. **Both dept heads must ACK the change before it takes effect.**
5. Update the version in this registry.

Minor changes (wording, clarification, non-breaking additions): dept head peer sign-off sufficient.

Breaking changes (changed message format, new required fields, removed steps): Tier 2 escalation to council-chair required before activation.

---

## Cross-Dept Approval Rule

No change to a cross-dept protocol takes effect without written ACK from every participant dept head.

If participant dept heads disagree, escalate to council-chair per `department-lead-protocol.md`:

```
TYPE: matrix_conflict
SEVERITY: [low | medium | high]
PARTIES: [{owner-dept} head, {participant-dept} head]
ISSUE: protocol
---
[Owner position + reasoning]
[Participant position + reasoning]
PROPOSED_RESOLUTION: [what each party proposes]
```

---

## Maintenance

This file is maintained by the agency-council. Dept heads may propose additions by following the "How to Add" steps above — the row is only added to this registry after the protocol reaches `active` status.

The agency-council reviews this registry quarterly and deprecates protocols that are no longer in use.

---

## References

- Dept-Coord protocol: `core/runbooks/dept-coord-protocol.md`
- Dept boot sequence: `core/runbooks/dept-boot-sequence.md`
- Dept lead protocol: `core/runbooks/department-lead-protocol.md`

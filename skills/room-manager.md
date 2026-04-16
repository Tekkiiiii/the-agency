---
name: room-manager
description: >
  Polls all active agency rooms, routes escalations to the right team, and
  throttles duplicate notifications so the same alert doesn't fire multiple
  times in quick succession. Trigger: when starting a shift, running a periodic
  health check, or integrating with monitoring tools (PagerDuty, Slack,
  Datadog). Key capabilities: concurrent room polling (all rooms checked at
  once), deduplication via 1-hour rolling window per alert fingerprint,
  escalation routing to the right team based on alert type, and a clean
  throttle report showing what fired, what was suppressed, and why. Also for:
  dry-run mode (see what would fire without sending), and tuning the throttle
  sensitivity based on alert type.
---

# /room-manager — Agency Room Monitor

Polls all active agency rooms for alerts, routes escalations to the right
team, and throttles duplicate notifications.

## When to Activate

Trigger `/room-manager` when:
- Starting a monitoring shift
- Running a periodic health check
- Integrating with external monitoring tools (PagerDuty, Slack, Datadog)

## Prerequisites

Requires a configured `~/.claude/memory/agency-rooms.json` file listing all
active rooms and their teams. Each room entry needs:
- `room_id`: unique identifier
- `team`: which team owns this room
- `escalation_policy`: how to route critical alerts
- `check_interval`: how often to poll (default: 5 minutes)

## Instructions

### Step 1: Load Room Configuration

Read the agency rooms config:
```bash
cat ~/.claude/memory/agency-rooms.json
```

Parse the room list and escalation policies.

### Step 2: Poll All Rooms Concurrently

For each room, send a poll request simultaneously. Collect:
- Current alert count
- Alert fingerprints (hash of alert type + source + severity)
- Room status (active, degraded, offline)

### Step 3: Deduplicate with 1-Hour Rolling Window

For each alert fingerprint received:
1. Check `~/.claude/memory/agency-alert-history.jsonl`
2. If the same fingerprint fired within the last 60 minutes → **suppress**
3. If not seen in the last 60 minutes → **route**

Keep a running tally of:
- Total alerts received
- Alerts suppressed (throttled)
- Alerts routed
- Rooms affected

### Step 4: Route Escalations

For each non-suppressed alert, determine the escalation path:

| Alert Type | Severity | Route To |
|-----------|----------|----------|
| infra.critical | CRITICAL | on-call + PagerDuty |
| infra.warning | HIGH | team Slack channel |
| security | ANY | security team + audit log |
| performance | MEDIUM | team Slack channel |
| general | LOW | team backlog |

Format the escalation message:
```
ALERT: {alert_type}
SOURCE: {room_id}
SEVERITY: {severity}
SUMMARY: {one-line alert summary}
TIMESTAMP: {when detected}
FINGERPRINT: {hash for deduplication}
```

### Step 5: Send to Appropriate Channel

Route the escalation via the configured method:
- PagerDuty: trigger incident via API
- Slack: send to team channel with `@team` mention
- Email: send to distribution list
- Log only: write to audit trail

### Step 6: Update Alert History

Append all alerts (suppressed and routed) to the rolling history log:
```json
{"ts":"ISO","fingerprint":"hash","room":"id","action":"routed|suppressed","alert_type":"type"}
```

Prune entries older than 2 hours (keep a buffer beyond the 1-hour throttle window).

### Step 7: Throttle Report

Output a summary:
```
ROOM MANAGER REPORT — {timestamp}
════════════════════════════
Rooms polled:      {N}
Alerts received:   {N}
  Routed:          {N}
  Suppressed:      {N} (throttled)
Rooms affected:   {N}

ESCALATIONS ROUTED:
  [Alert summary] → [team/channel]
  [Alert summary] → [team/channel]

SUPPRESSED (throttled):
  [Alert fingerprint] — last fired {X}m ago

VERDICT: {CLEAN | ACTION REQUIRED — N escalations routed}
```

## Dry-Run Mode

Run with `--dry-run` to see what would fire without sending any notifications:
```
/room-manager --dry-run
```

This polls rooms, deduplicates, and prints the full throttle report but skips
Step 5 (no messages sent). Use when tuning the throttle sensitivity.

## Tuning Throttle Sensitivity

By default, alerts with the same fingerprint are suppressed if fired within 60
minutes. Adjust by alert type:

| Alert Type | Throttle Window |
|-----------|----------------|
| infra.critical | 15 minutes |
| security | 5 minutes |
| infra.warning | 60 minutes |
| performance | 120 minutes |
| general | 240 minutes |

## Important Rules

- **Concurrent polling only.** Poll all rooms at once, not sequentially.
- **Fingerprint-based deduplication.** Suppress on hash match, not string
  match — allows grouping of similar alerts.
- **1-hour rolling window minimum.** Never suppress an alert for more than
  60 minutes without a clear escalation policy reason.
- **Log everything.** Both routed and suppressed alerts go to the history log
  — you need the full picture for tuning.
- **Security alerts never throttled.** `security` type alerts route
  immediately regardless of throttle window.

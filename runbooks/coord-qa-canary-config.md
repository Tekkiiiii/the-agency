# Coord-qa-Canary Configuration
# LAZY-LOAD source for pd-coordinator.md — extracted F19 (2026-06-23)
# Load this file when spawning a Coord-qa-Canary (Phase A per-L3 QA).

## Coord-qa-Canary Configuration (spawned by Coord, not PD)

PD spawns Coord-qa-Canary when all L3 Coords have been ACKed, before reporting to root.

**Spawn config:**
- Name: `Coord-qa-{slug}`
- Model: Sonnet
- Task type: `qa-only`
- Agent type: Testing Lead or Evidence Collector (from Agency catalog)

**Spawner provides:**
- `target`: project directory or URL for the combined L3 output
- `mode`: `qa-only` (report only — no fixes)
- `baseline`: path to previous session's QA report, or "none"
- `auth`: cookie file path or "none"
- `scope`: `full` | `quick` (30s) | `regression`

**Deliverables required:**
- Health score (0–100 integer)
- Issues by severity (CRITICAL/HIGH/MEDIUM/LOW)
- Screenshots in `{project}/memory/qa/screenshots/`
- Delta vs baseline (regression mode)
- Report at `{project}/memory/qa/qa-report-final-{timestamp}.md`

## ACK/NACK Reference Table

| Handoff | Reporter | Reviewer | ACK condition | NACK condition |
|---------|----------|----------|---------------|----------------|
| Exec → Coord | Exec sends DONE + QA | Coord reviews QA report | Health ≥ 85 (≥ 90 design/visual), no CRITICAL | Health < 85 (< 90 design/visual) OR CRITICAL/HIGH present |
| Coord → PD | Coord sends L3 complete + QA | PD reviews Coord QA report | Health ≥ 85 (≥ 90 design/visual), no CRITICAL | Health < 85 (< 90 design/visual) OR CRITICAL/HIGH present |
| PD → root | PD sends final digest + QA | root (the user) | Explicit ACK | Explicit NACK with fix list |

**ACK** = "looks good, die quietly" → reporting agent deletes scratch and stops
**NACK** = "fix: [list]" → reporter fixes → re-runs QA gate → re-reports

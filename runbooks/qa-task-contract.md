---
name: qa-task-contract
description: >
  Contract defining the QA dispatch protocol between PD/Coord (spawner) and
  Testing Lead (deliverer; evidence-collection work = general-purpose + /qa-only, /browse, /webapp-testing, role file {agency-root}/agents-archive/generalist-2026-10-06/testing/testing-evidence-collector.md). Must be read before accepting any
  QA dispatch from a PD or Coord.
department: testing
role: contract
---

# QA Task Contract

**Who must read this:** Any agent receiving a QA dispatch — Testing Lead, Evidence
Collector, or any QA-only agent spawned by PD or Coord.

---

## Spawner Must Provide

Before dispatching a QA task, the spawner (PD or Coord) must include all of the
following in the spawn prompt:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | URL(s) or file/scope paths | Yes | What to QA — URL for web, path for files/components |
| `mode` | `qa` or `qa-only` | Yes | `qa` = fix loop; `qa-only` = report only (QA gates use this) |
| `baseline` | path string | Yes | Path to previous QA report for regression, or `"none"` |
| `auth` | path or `"none"` | Yes | Cookie file path or credentials, or `"none"` |
| `scope` | `full`\|`quick`\|`regression`\|`critical-only` | Yes | Depth of QA pass |

---

## QA Deliverer Must Produce

After completing the QA pass, the deliverer sends a report with:

### Health Score
- **0–100 integer**
- General tasks: ≥ 85 AND no CRITICAL → QA passes, spawner ACKs
- Design/visual tasks: ≥ 90 AND no CRITICAL → QA passes, spawner ACKs
- Below threshold OR any CRITICAL → QA fails, spawner NACKs

### Issues List
Each issue must include:
- **Severity**: CRITICAL / HIGH / MEDIUM / LOW
- **Description**: What is wrong
- **Location**: File, component, URL, or line number
- **Screenshot**: One screenshot per issue in `{project}/memory/qa/screenshots/`

### Delta vs Baseline
(Required for `regression` mode only)
- New issues vs the baseline report
- Resolved issues (present in baseline, gone now)
- Regressed issues (worse than baseline)

### Report File
- Path: `{project}/memory/qa/qa-report-{slug}-{timestamp}.md`
- Must persist — survives session restarts
- Include health score, full issue list, screenshots (paths), delta

---

## Mode Reference

| Mode | Fix loop? | Who uses it | QA gate? |
|------|-----------|-------------|----------|
| `qa` | Yes — fix immediately | Executor → Coord gates | No |
| `qa-only` | No — report only | Coord → PD gates, PD → root | Yes |
| `regression` | No — delta report | Canary / post-deploy | Optional |
| `critical-only` | No | Fast pre-merge check | Yes |
| `quick` | No — 30s cap | Time-boxed checks | Yes |

---

## Example QA Dispatch

```
You are Coord-qa-Canary, spawned by PD-{slug}.
Target: ~/projects/myapp/src/components/
Mode: qa-only
Baseline: ~/projects/myapp/memory/qa/qa-report-final-2026-04-10.md
Auth: none
Scope: full

Read ~/.claude/runbooks/qa-task-contract.md before starting.
Load skills: qa-only, agent-browser.
QA the combined output of all L3 Executors.
Save report to ~/projects/myapp/memory/qa/qa-report-final-2026-04-17.md.
Send DONE + health score to "PD-{slug}" via SendMessage.
```

---

## Context Retrieval — Curator Agent

When you need project context (past decisions, brand guidelines, architecture conventions,
lessons learned) that wasn't provided in your spawn prompt, spawn a curator agent:

```
Agent({
  subagent_type: "curator",
  model: "sonnet",
  description: "Curator — {topic}",
  prompt: "Project: {slug}\nPath: {project_path}\nQuestion: {your question}"
})
```

Curator returns a concise answer (~300 tokens) from the project's knowledge graph, then dies.
This is cheaper than reading memory files directly into your context.

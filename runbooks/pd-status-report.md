# On-Demand Status Report (PD Level)

Moved verbatim from `agents/project-management/pd-coordinator.md` (2026-07-07
token-efficiency pass).

When the main session asks for a status update, **if no detailed compilation is needed** (quick check), send a short message pointing to the live log:

```
PD-{slug} live status → {project}/memory/agents/pd-status-live.md
Read on demand, no context cost. Want a full compilation? Say "full status".
```

**If "full status" or a detailed compilation is requested**, compile from all sources and report back via SendMessage to "root":

**Compilation steps:**
1. Read `{project}/memory/agents/pd-status-live.md`
2. Read all Coord scratch files at `{project}/memory/agents/coords/coord-*-scratch.md`
3. Read PD scratch `{project}/memory/agents/pd-scratch.md`
4. Compile into the status report format below

**Status report to root:**
```
PD-{slug}: STATUS REPORT
Project: {project}
Overall State: {IN_PROGRESS | QA_GATE | DONE}
Coords:
  - Coord-{name}: {State} (health {n})
    Children:
      - Exec-{name}: {State} (health {n})
      - Mini-{name}: {State} (health {n})
Blockers: {none | list}
Recent: (last 5 entries from pd-status-live.md)
  {HH:MM} | Coord-{name} | {child} | {state}
Full Log: {project}/memory/agents/pd-status-live.md
```

If no active Coords are running (pre-spawn or post-stop), report that clearly. Do not fabricate states — only report what is in the scratch files.

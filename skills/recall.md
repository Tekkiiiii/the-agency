---
name: recall
description: "Spawns a subagent to read a project's save-state files and output a tight 6-field briefing — fully autonomous, no user interaction. Trigger when the user invokes /recall [project-slug], says 'resume session', 'pick up where we left off', or 'continue from last session'. The subagent reads next-session.md, heartbeat.md, decisions.md, and save-state-state.json — all read-only. Outputs: Phase, Next action (1 sentence), Blockers (1 per line), Top 2 locked decisions, 1–2 mid-flight files, and context from the last session. Also for: quickly orienting to an unfamiliar project on first contact, checking whether a project has active work mid-session without reading all files manually, and resuming multi-project context across sessions by running /recall for each slug in sequence. SSOT for project paths is ~/.claude/memory/medium-term.md."
---

# Recall

Spawns a subagent that reads the project's save-state files and outputs a briefing.
Caller spawns and waits — zero work done in the calling session.

## SSOT: medium-term.md

The **primary source of truth** for project locations is `~/.claude/memory/medium-term.md`
— the Active Projects table. Read it FIRST.

## Project Map

Read from `~/.claude/memory/medium-term.md` — this is the SSOT for project paths.

| Project | Path |
|---------|------|
| {project-a} | `{project-a-directory}` |
| {project-b} | `{project-b-directory}` |

(Populate from your medium-term.md Active Projects table.)

## If Slug Not Found

1. Check `~/.claude/memory/medium-term.md` Active Projects table — the SSOT.
2. If not in medium-term.md → output:

   ```
   PROJECT NOT FOUND: {slug}
   Hint: Check ~/.claude/memory/medium-term.md for the current project list.
   ```

   **Stop. Do not fall back to other projects or search broadly.**

## Step 1 — Spawn Subagent

Use the Agent tool to spawn a general-purpose sonnet subagent. The subagent reads files
and outputs the briefing — do not do any reading yourself.

Subagent prompt:

"Read-only briefing. Do NOT write any files.

PERMISSIONS: read-only on ALL paths below. No write/edit/create.

## Scope
- Memory dir: `{project}/memory/` — next-session.md, heartbeat.md, decisions.md, sessions/
- State tracking: `{project}/.claude/save-state-state.json`
- Optional project root files: `{project}/STATE.md`, `{project}/CLAUDE.md`

FILES TO READ:
- {project}/memory/next-session.md — primary briefing (status, next, blockers, mid-flight)
- {project}/memory/heartbeat.md — phase status + blockers (not Session End history)
- {project}/memory/decisions.md — top 2 locked decisions
- {project}/.claude/save-state-state.json (if exists)

OUTPUT FORMAT (output exactly this, nothing else):

RECALL — {slug}

Phase: [current phase or status]
Next: [specific action — one sentence]
Blockers: [list one per line, or "none"]
Decisions: [top 2 locked decisions, one per line, or "none"]
Mid-flight: [1-2 mid-flight files, one per line, or "none"]
Context: [what was happening last session — 1-2 sentences]

--- Last Session (from heartbeat Session End) ---
Completed: [from heartbeat "Completed This Session" — top 2-3 bullets]
Remaining: [from heartbeat "In Progress" + "Top 3 Priorities"]

RULES:
- Read-only. Do NOT write or edit any files.
- If a file doesn't exist, skip that field and note "N/A".
- Keep every field to 1-2 lines max.
- Be specific — "fix BottomNav.tsx mobile layout" not "fix bugs".
- Output ONLY the briefing above. No preamble, no commentary."

subagent_type: Explore
model: sonnet

Wait for the subagent to complete.

## Step 2 — Graph enrichment (caller-side)

After the subagent returns the recall briefing, call:

```
mcp__graphify__query_graph(question="{slug} key components and active connections")
```

Append the top 5 returned node labels as a **Graph:** line at the end of the recall output:

```
Graph: <node1>, <node2>, <node3>, <node4>, <node5>
```

If the graphify MCP tool returns an error, append:
  Graph: ⚠️ graphify MCP unavailable — run: graphify serve ~/.claude/graphify-out/unified/graph.json
Do not silently skip. The graph context is load-bearing for session quality.

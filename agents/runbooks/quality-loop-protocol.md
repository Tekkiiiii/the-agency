---
name: quality-loop-protocol
description: Cross-cutting quality enforcement protocol. All creative pipelines invoke quality-loop-router as their final quality gate before delivery to user.
type: runbook
owner: critiques
participants: [content-creation, marketing, design, engineering, video-studio]
version: v1.0
status: active
lastUpdated: 2026-06-01
---

# Quality Loop Protocol — Cross-Cutting

## Purpose

Every creative deliverable produced by any agent, pipeline, or skill goes through a quality gate before reaching the user. This protocol defines that gate.

## Two Modes

### Mode A — Internal Creative Tasks (Claude-native)
- Used when: pipeline ran entirely within Claude (no paid external platforms)
- Pattern: produce → critique (task-type matched) → score → loop if needed → deliver
- Threshold: ask user on start (default avg >= 85, none below 75)
- Max rounds: 3
- Skill: `/quality-loop-router` (Mode A)

### Mode B — External Creative Tasks (Canva / Figma / NotebookLM / paid MCP)
- Used when: pipeline used a paid external platform for creation
- Pattern: produce → one critique pass → structured fix plan → user approval gate → apply fixes → deliver
- No loop (external platform costs/rate limits)
- Skill: `/quality-loop-router` (Mode B)

## Mode Detection

The quality-loop-router skill auto-detects mode by inspecting pipeline context:
- Any `mcp__claude_ai_Canva__*`, `mcp__plugin_figma_figma__*`, `mcp__notebooklm-mcp__*`, or paid MCP tools used → Mode B
- Otherwise → Mode A

## Critic Selection

| Task type | Critics invoked |
|-----------|----------------|
| content | critique-content + critique-marketing |
| content-web | critique-content + critique-marketing + critique-seo |
| design | critique-design (screenshots required) + critique-brand |
| product-ux | critique-product + critique-design (screenshots required) |
| code | critique-code + receiving-code-review |
| code-security | critique-security + critique-code |
| marketing | critique-marketing + critique-content |
| pedagogy | critique-pedagogy |
| report | critique-content + critique-marketing |
| deck | critique-design (screenshots required) + critique-content |
| video | critique-video (frames required) + critique-content |
| data | critique-data (screenshots required) + critique-product |

## Screenshots Rule

Design, video, and data critiques ALWAYS require visual evidence. The quality-loop-router captures screenshots/frames BEFORE running the critique agent. Never critique visual work from source code alone.

## Auto-Clone Protocol

If a task type has no matching critic in agents/critiques/:
1. quality-loop-router spawns Delegator to confirm the gap
2. If gap confirmed: creates new critic by cloning closest existing one
3. Registers new critic in INDEX.md, quality-loop-router skill, and this protocol
4. Logs creation in pipeline report

## Pipelines Using This Protocol

| Pipeline | Integration point | Mode |
|----------|-----------------|------|
| pipeline-content | Stage 5.5 after Polish | A (or B if Canva/Figma used) |
| pipeline-feature | Stage 7.5 if creative assets present | A (or B if Figma used) |
| pipeline-bugfix | Stage 5.5 if docs changed | A |
| pipeline-deploy | Stage 4.5 if content deployed | A |
| pipeline-audit | Stage 4.5 on the audit report | A |
| pipeline-seo-geo-aeo | Stage 7.5 on the audit report | A |
| blog-pipeline | Stage 6.5 after Polish | A |
| marketing-assessment-pipeline | Steps 5-6 (embedded critics) | A (equivalent) |

## CLAUDE.md Auto-Trigger

The following trigger phrases cause the parent AI to invoke quality-loop-router:
- "ship this" / "publish" / "finalize" / "deliver" / "ready for review" → on any creative deliverable
- End of any pipeline skill → quality-loop-router invoked as final step

## Related

- Skill: `{agency-root}/skills/quality-loop-router/SKILL.md`
- Critics: `{agency-root}/agents/critiques/`
- cc-loop: `{agency-root}/skills/cc-loop/SKILL.md` (Mode A reuses cc-loop primitives)
- skill-routing: `{agency-root}/memory/skill-routing.md`

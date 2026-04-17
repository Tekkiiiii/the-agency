# I built an autonomous AI team that coordinates itself across Claude Code sessions

**[link to repo]**

I've been running The Agency as my default workflow for the past few weeks. Here's what it does and what changed in the latest version.

## The problem it solves

AI agents that forget everything when you close the session. You re-open Claude Code and start from scratch — no context, no memory, no continuity. You become the project manager again.

The Agency makes Claude Code project-aware. A Project Director agent owns each project end-to-end. It decomposes tasks, assigns specialists, gates quality, and persists state. When you come back, the PD shows you exactly where things stand.

## What shipped in v2

**QA gates on every handoff.** Every agent-to-agent handoff now requires a health-score QA pass. No work gets approved without evidence. The gate is simple: health score ≥ 70, zero CRITICAL issues. Rejected work loops back through QA until it passes.

**Explicit ACK/NACK protocol.** Agents wait for explicit approval before stopping. You always know why something was accepted or rejected.

**Mini-Coords for deep decomposition.** Complex L6 tasks spin up a Mini-Coord that keeps decomposing to L7/L8/L9 without bouncing back to PD. The chain scales with problem complexity.

**4-tier architecture: PD → Coord → Mini-Coord → Task-Executor.** Each level has a clear termination point. No agent decomposes past its level.

## The stack

SQLite task store, filesystem memory, zero cloud dependencies. Your data stays on your machine. No API keys, no servers, no running processes. It's a git repo and a CLI.

```bash
git clone https://github.com/Tekkiiiii/the-agency.git
cd the-agency
npx agency init
agency new my-project "Build something"
```

Then in Claude Code: `/recall my-project` — the PD loads with full project context.

## What it can't do

This is not an agent framework for building LLM apps. It's not LangChain. It's a workflow system for running autonomous AI agents that coordinate and remember across sessions. If you want your AI agents to behave like a real team — with accountability, quality gates, and institutional memory — that's what this is.

GitHub: https://github.com/Tekkiiiii/the-agency

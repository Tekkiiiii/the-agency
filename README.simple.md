# The Agency

*Your AI workforce runs itself. Agents coordinate, remember, and ship — while you sleep.*

---

## What it does

The Agency is a system that lets you run autonomous AI agents like a real team — with project managers, specialists, and a memory that survives between sessions.

Instead of starting from scratch every time, your agents:

- **Remember** what was decided last session
- **Own** their work end-to-end (Project Directors)
- **Coordinate** through structured handoffs
- **Escalate** when they get stuck
- **Persist** everything between sessions

## What you get

**Projects that run themselves:**
```
You: "Build a task manager app"
PD: "Got it. Creating tasks, assigning specialists."
Specialists: work in parallel
PD: "Phase 1 done. All tests passing. Starting Phase 2."
You: [come back tomorrow] → PD shows you the current state
```

**Memory that sticks:**
- Session logs — what happened, what was decided
- Lessons — what went wrong and how to avoid it
- Project state — current phase, blockers, what's next
- Decisions — cross-project architectural choices

**Structured coordination:**
Agents hand off work with full context. No "I thought you were doing that." No duplicate work. Every handoff has: what's done, what's next, what to watch for.

## What you need

- Claude Code (free)
- Node.js 18+ (for the CLI)
- 5 minutes to set up

## How to start

### 1. Install

```bash
git clone https://github.com/the-agency/the-agency.git
cd the-agency
npx agency init
```

### 2. Create your first project

```bash
agency new my-project "Build a task manager app"
```

### 3. Talk to it in Claude Code

```
/recall my-project
```

The PD for your project loads. Tell it what to build. It creates tasks, assigns work, and coordinates specialists. When you're done for the day:

```
/save-state
```

Everything is saved. The next session picks up exactly where you left off.

## How it works

**You** give direction.
**Project Director (PD)** owns the project — breaks work down, assigns specialists, gates completed work.
**Specialists** execute — build the feature, write tests, document the API.
**PD** monitors the pipeline, escalates blockers to you.

The PD is like a product manager who never forgets, never drops the ball, and runs autonomously between sessions.

## What it looks like

```
Session 1:
  You: /recall my-project
  PD: "Project created. Starting Phase 1."
  PD: Creating 4 tasks...
  PD: Specialists now building auth, database, API, and UI in parallel.
  You: /save-state

Session 2:
  You: /recall my-project
  PD: "Phase 1 complete. Specialists shipped auth + database.
       Phase 2 starting. UI in progress."
  You: Great, keep going.
  PD: ...
```

## Skills

Skills are pre-built workflows that agents use. Things like:

| Skill | What it does |
|---|---|
| `/save-state` | Saves everything to memory before you close the session |
| `/recall` | Loads your project's current state at the start |
| `/swarm` | Runs multiple agents in parallel when work is independent |
| `/delegate` | Hands off a task to the right specialist with full context |
| `/self-healing` | Diagnoses and fixes what's broken before escalating |

Install more skills:
```bash
agency skill install backend
agency skill install frontend
agency skill install security
```

## Privacy

Everything runs locally. Your task store, session logs, and project memory live in `~/.claude/` on your machine. Nothing is sent to any server except Claude Code.

## Extending it

The Agency is designed to grow with you:

- **New skills**: `agency skill install <name>`
- **New projects**: `agency new <name> "<description>"`
- **Custom agents**: add them to the `skills/` directory
- **Custom coordination**: use the NEXUS handoff system in any project

## License

MIT — it's yours to use and modify.

---

*Built on Claude Code. Runs without a server. Scales with your ambition.*

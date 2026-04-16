---
name: self-healing
description: Diagnose and fix broken workflows without giving up
category: ops
trigger: "/self-healing" | something isn't working
---

# Self-Healing

Use this skill when something is broken — a script fails, a workflow stalls, a test won't pass.

## Diagnostic Flow

### 1. Investigate — What happened?
- Read the error message carefully
- Check the session log for context
- Run the failing command again to observe

### 2. Scope — How big is the problem?
- One file or system-wide?
- Known cause or unknown?
- First time or recurring?

### 3. Hypothesize — What likely caused it?
- Write your best guess
- Test it

### 4. Fix — Implement the fix
- Fix the root cause, not the symptom
- One change at a time
- Verify after each change

### 5. Verify — Confirm it works
- Run the original command
- Run related tests
- Check session log

## Common Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Script won't run | Wrong path | Use absolute paths |
| API call fails | Missing env var | Set in `.env` |
| Test times out | External dependency | Mock or skip |
| Type error | Import path wrong | Check `node_modules` |
| Module not found | Not installed | `npm install` |

## Key Rules

- **Iron Law**: no fix without root cause
- Don't patch symptoms — fix the root
- If you can't fix in 3 tries → escalate
- Document what broke in session log
- Append lesson to `lessons/{stack}.md` if it was a new failure type

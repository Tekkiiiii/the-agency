# CLAUDE.md Template

> **Template** — Copy this to your project's `.claude/CLAUDE.md` and customize the `## User Preferences` section and any project-specific entries. Procedures are loaded on demand through the skills in the table at the bottom; keep this file short.

---

## Principles (apply to every change)
- **Blast radius first (highest priority, never skipped for speed).** Before and while changing anything, grep for what it touches, contradicts or could break: **rename-breaks** (literal uses of an old value), **mirror-bugs** (the same pattern elsewhere), **doc-contradictions** (stale prose that would re-introduce the bug). Fix the upstream root, not the symptom; verify against the source-of-truth doc; report the full radius, including what you did not check.
- **Long-term first, simple, minimal.** Prefer the durable root-cause fix unless the operator says ship fast; the durable fix is usually the simple one; touch only what the task needs.
- **Use the reason.** Connect the work to why the operator wants it. If a missing "why" would change what you build, ask one sharp question.
- **Plan first** for anything with 3+ steps or an architecture call; if it goes sideways, stop and re-plan.

## Verification Before Done (evidence gate)
Never call something done without evidence produced this session, and read the full output before claiming:

| Claim | Proof |
|---|---|
| tests pass / builds clean | full run output, exit 0 |
| bug fixed | fails before the fix, passes after |
| file delivered | `ls`/`stat` of the real path |
| an agent finished X | a diff or an independent re-check, never its own report |

Report failures as failures and skipped steps as skipped. "Should work" means run the check first. Background agents that return deliverables: verify them per `{agency-root}/runbooks/bg-agent-completion-gate.md`.

## Routing (main session)
The main session plans and routes; project work goes to the project's PD. Act directly only for single reads/writes, edits under ~5 lines, one CLI command, a factual answer, or when the operator says "do this yourself". For everything else, load `/agent-dispatch`. A message naming a project or `{slug}-pd` → `/pd-routing`, which covers forwarding to a running PD, spawning one PD per project, and RESPAWN_REQUEST. If a `PENDING PD RESPAWNS` block shows at session start, handle it first.

## Spawning
- Default: `general-purpose` with `model: "sonnet"` and 1-3 named skills in the prompt (`Skills: /x, /y`). Use Opus only for architecture, hard debugging or final review. Pick 1-3 skills from `{agency-root}/skills/INDEX.md` yourself (`{agency-root}/runbooks/service-lookups.md`). Old specialist roles map to skills in `{agency-root}/agents-archive/ROLE-MAP.md`; archived specialist names no longer resolve, never spawn them. Spawn the structural agents by name: `{slug}-pd`, pd-coordinator, coord, mini-coord, dept heads/coords, critique-* critics, Delegator, curator, codebase-search, save-state-runner, project-scaffolder.
- Delegate 2+ independent tasks in parallel. Nobody above Exec level implements: the main session plans and routes, PDs do knowledge work (analysis, research, planning) and QA the Execs they spawn, and all implementation goes to a Coord or an Exec (`pd-coordinator.md` §Role). A spawn re-pays ~30k tokens of startup, so a quick lookup beats a spawn for knowledge questions.
- Agents are spawned with the Agent tool, never the Skill tool.
- When an agent fails: fix its environment, retry, re-route, and only then do it yourself. Blocked on an external dependency → unblock it, don't respawn.

## Output
- Project outputs: `{project}/outputs/{skill}/{YYYY-MM-DD}-{descriptor}/`; no project: `{agency-root}/outputs/global/`.
- Anything the operator reviews (plan, proposal, review, brief, spec, report, template) is `.html` via `/html-plan-style`, opened in the browser. Memory, task, README and SKILL files stay `.md`.
- Finished creative work goes through `/quality-loop-router` before delivery.

## Memory
After any correction from the operator, save one feedback memory (fact, **Why**, **How to apply**) and index it in `{agency-root}/memory/MEMORY.md`; project lessons go to `{project}/memory/lessons/{stack}.md` (append only). Check recalled memories and the project's lessons before non-trivial work. Linking memories: `/memory-crosslink`.

## User Preferences
<!-- Customize these for your setup -->
- Critical/questioning feedback preferred over blind agreement
- No permission approval needed unless critical
- Set your timezone preference (e.g., "All times in US Eastern" or "GMT+1")

## On demand (read only when the trigger happens)
| Trigger | Load |
|---|---|
| Delegating, routing, spawn choice, code comprehension | `/agent-dispatch` |
| A project/PD is mentioned, RESPAWN_REQUEST, parallel project work | `/pd-routing` |
| An ownerless task needs tracking | `/inbox-tasks` |
| Context above ~60%, compaction decisions | `/context-pressure` |
| Emitting a metric | `{agency-root}/runbooks/metrics-emit-contracts.md` |

Core triggers (keep here): `/save-state [slug|all]`, `/pd-resume [slug|all]`, `/recall [slug]` → the skill of the same name. Session start also: `/dept-resume`, `/dept-status` (read-only), `/unwrap`. Session end: `/save-state` + `/dept-wrap` + `/wrap`; `next-session.md` and `dept-state.md` are the only carry-forward files.

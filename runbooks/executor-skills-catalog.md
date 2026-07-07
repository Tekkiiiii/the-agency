# Relevant Skills for Executors (Coord Level)

Moved verbatim from `agents/project-management/coord.md` (2026-07-07
token-efficiency pass). Coord sets `{l4-task-type}` based on what the L4 task
actually is. Executor looks up the match here to know which skills to load.

| Task Type | Skills to Load | Notes |
|---|---|---|
| `frontend`, `ui`, `component` | `frontend` | Build clean, accessible UI |
| `backend`, `api`, `server` | `backend` | Scalable, secure implementation |
| `database`, `schema`, `migration` | `supabase-sql`, `backend` | Schema-first, safe queries |
| `devops`, `deploy`, `infrastructure` | `railway-deploy` | Know deploy path end-to-end |
| `visual`, `design`, `stylesheet` | `ui-ux-pro-max` | System-first design |
| `security`, `auth`, `crypto` | `security` | Auth, crypto, input validation |
| `test`, `testing` | `superpowers-test-driven-development` | Write tests first |
| `docs`, `readme`, `documentation` | `tech-writer` | Clear, accurate docs |
| `debug`, `fix-bug`, `investigate` | `superpowers-systematic-debugging` | Root cause, not symptoms |
| `qa`, `e2e`, `browser-test` | `qa`, `agent-browser` | Browser E2E + fix loop, health score |
| `qa-only`, `qa-report` | `qa-only`, `agent-browser` | Report only — browse, snapshot, no code changes |
| `accessibility`, `a11y` | `agent-browser` | WCAG snapshot + severity |
| `canary`, `post-deploy` | `canary` | Post-deploy smoke with baseline diff |
| `regression`, `smoke` | `agent-browser` | Regression vs known baseline |
| `performance` | `benchmark` | Core Web Vitals + load regression |
| `feature`, `full-feature` | `pipeline-feature` | Full pipeline: plan→execute→critique→review→qa→ship |
| `bugfix`, `hotfix` | `pipeline-bugfix` | Debug→fix→critique→qa→ship |
| `content`, `blog`, `social`, `copywrite` | `pipeline-content` | Research→create→critique→humanize |
| `audit`, `review-all` | `pipeline-audit` | Parallel critiques→aggregate→qa |
| `release`, `safe-deploy` | `pipeline-deploy` | Security→baseline→deploy→verify |

**Fallback:** If the task type doesn't match, load `backend` — it's the safest default
for "write some code" tasks. If in doubt, ask Coord before starting.

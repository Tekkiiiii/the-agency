---
name: context-mode
description: "Use whenever the context-mode MCP server is present, or when Bash output exceeds ~20 lines, files are read for analysis, or web pages are fetched. Routes output through ctx_execute / ctx_batch_execute / ctx_fetch_and_index so raw output never floods context. Mandatory in context-mode sessions."
---

# context-mode

Context-mode routes data-heavy tool calls through sandboxed MCP tools, preventing raw outputs from flooding the context window.
Applies automatically when context-mode MCP server is running in the session. Always enforced — do not skip.

---

## When Invoked
- Always active when context-mode MCP server is present in the session
- Detected automatically by the session environment
- No explicit user trigger needed — enforce at all times

---

## Tool Routing Rules

Route every tool call to its sandbox equivalent:

| Instead of | Use | Why |
|---|---|---|
| Bash commands (>20 lines output) | `batch_execute` or `ctx_execute` | Captures output, prevents context bloat |
| Read for analysis | `ctx_execute_file` | Raw content never enters context |
| WebFetch | `ctx_fetch_and_index` then `search` | Fetch, index, then query by search |
| Follow-up searches | `ctx_search` | Query indexed content on demand |
| Batch commands/queries | `ctx_batch_execute` | One call replaces many steps |

---

## Forbidden Patterns

- **NEVER use Bash** for commands producing >20 lines of output — use `ctx_execute` or `ctx_batch_execute`
- **NEVER use Read** for analysis tasks — use `ctx_execute_file`
- **NEVER use WebFetch** — use `ctx_fetch_and_index` then `ctx_search`
- **NEVER use curl/wget in Bash** — use `ctx_execute` or `ctx_fetch_and_index`
- Bash is ONLY for: git, mkdir, rm, mv, navigation, and short commands (<20 lines)

---

## Output Rules

- Keep responses under 500 words
- Write artifacts (code, configs) to files — never return them as inline text
- Return only: file path + 1-line description

---

## Local Dev Notes (for working on context-mode itself)

- Hook dispatcher: `context-mode hook <platform> <event>`
- Delete `server.bundle.mjs` during local dev to load changes from `build/server.js`
- Version must sync across 4 files
- Tests: `npm test` (Vitest, parallel), `npm run test:watch`
- TDD workflow: failing test first → minimum code → refactor
- Add tests to existing test files covering the same domain — do not create new test files

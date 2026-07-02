# Service Lookups — Curator / Delegator / codebase-search (full protocol)

Loaded on demand from CLAUDE.md §Agent Dispatch. Revised 2026-07-02: lookups
replaced default agent spawns (a spawn re-pays ~30-40k tokens of fixed context
to answer what a grep or MCP query returns for 1-3k; weekly-limit discipline).

## Project knowledge (was: Curator-first)

**Default — direct lookups, no spawn:**
1. Project graph: `mcp__graphify__query_graph` on the unified graph, or Read
   `{project}/memory/graphify-out/graph.json` (edges under `"links"`, not
   `"edges"`).
2. Semantic recall: `mcp__plugin_pinecone_pinecone__search-records` (index
   `agent-memory`) for past-session content.
3. Topic notebooks: `mcp__notebooklm-mcp__notebook_query` per
   `notebooklm-registry.md`.
4. Plain files: `{project}/memory/decisions.md`, `next-session.md`,
   `pd-structure.md`.

**Spawn the curator agent ONLY when** the question needs synthesis across
multiple sources (graph + Pinecone + notebooks + files) or you cannot name
which source holds the answer. Curator has a restricted tool set (no Agent
tool) and is read-only.

**Event contract (unchanged):** emit `curator_skip` (lookup answered it — use
`skip_reason_excerpt`) or `curator_spawn`. Templates:
`~/.claude/runbooks/metrics-emit-contracts.md`.

## Routing (was: Delegator-first)

**Default — file lookups, no spawn:**
1. `~/.claude/memory/delegator-cache.md` — exact task-pattern match (exact
   string only). Hit → use route, emit `delegator_cache_hit`.
2. `~/.claude/memory/agency-dispatch.md` — Step 0 protocol table, then Step 1
   domain table. Unambiguous single-domain row → use it.

**Spawn the Delegator agent ONLY when** the task is ambiguous, cross-domain,
or matches no dispatch row. On answer: append the route to delegator-cache.md,
emit `delegator_spawn`. Delegator may return `GAP` → follow CLAUDE.md
Create-on-gap.

**Pre-approved spawns that never need routing:** pd-coordinator (via
/pd-resume, /pd-spawn), coord, mini-coord, task-executor, curator,
codebase-search, save-state-runner, Explore, Plan.

## codebase-search (unchanged)

Invoke INSTEAD of running `find`/`grep`/`rg` sprawl across `~/.claude/` or
active projects when you do NOT know where something lives. Skip when you
already have the exact file path, or when a single targeted grep in a known
directory answers it.

## Violation metric

`general-purpose`/`claude` outside allowed conditions → emit
`generalist_ban_violation` BEFORE spawning, STOP, resolve a named agent
(CLAUDE.md hard-ban + Create-on-gap). Template: metrics-emit-contracts.md.

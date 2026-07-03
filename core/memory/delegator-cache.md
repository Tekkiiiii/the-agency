# Delegator Cache Manifest

Cache of verified-stable task-pattern → agent routing pairs.

## Usage

Before spawning Delegator, scan this file for an exact task-pattern match.
**Exact string match only — no fuzzy matching, no "close enough."**
If the task description matches a Pattern line verbatim → use the cached Agent and skip Delegator.
If no exact match → spawn Delegator as normal, append (task-pattern → route) here, emit delegator_spawn event.

Cache hits must be logged in the spawn record: "cache hit: {pattern} → {agent}" and emit delegator_cache_hit event.

## Entries

_Empty — entries accumulate as the Delegator resolves new task patterns. See `runbooks/service-lookups.md` for the lookup-first protocol._

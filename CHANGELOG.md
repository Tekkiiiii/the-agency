# Changelog

All notable changes to The Agency are documented here, grouped by release wave (date-based — this repo has no separate version file, so dates are the single source of truth and can never desync from git history).

## [Unreleased]

### Added
- `agency upgrade` now prints the CHANGELOG.md entries covering what was just pulled after a successful upgrade — best-effort, date-header based (no commit-hash mapping, no new deps), capped at ~40 lines with a pointer to CHANGELOG.md for the rest. Silent when already up to date.

### Fixed
- `scripts/` (save-state.py, mem-gardener.sh, setup-graphify.sh, etc.) is now deployed to `{agency root}/scripts/` by `agency init` and `agency upgrade` — previously it was never synced, so any skill referencing `~/.claude/scripts/...` (e.g. `/save-state`) would fail on a clean install with a "file not found" error.
- Removed hardcoded personal absolute-path examples (`/Users/Tekki/...`) from 5 shipped agent/skill files that are meant to run generically for any user — two of these were functional bugs (instructions that told the agent to literally write the string `/Users/Tekki` into another user's own files).

## [2026-07-24] — Skill sync self-heal (`00cd410`)

### Fixed
- Skills sync rewritten to content-hash comparison — mtime/size were unreliable after a `git checkout` resets file timestamps, which meant installs could silently skip updated skill files.
- Directory-only `skills/<name>/SKILL.md` is now the sole canonical layout. This self-heals any install previously poisoned by a flat `skills/<name>.md` file, which was invisible to the sync and never reached installs.

## [2026-07-22] (`dd9d64f`)

### Security
- Additional private-slug scrub from synced assets, closing a gap where internal project slugs could leak into shipped files.

### Added
- MCP-schema-overload trio and dept-coord sync (wave 8+9).

## [2026-07-16] (`fab3727`, `9958328`)

### Deprecated
- `lite` orchestration tier — scheduled for removal, see `docs/tiers.md`.

### Security
- Scrubbed PII (personal email address, GTM container ID) from public docs.

## [2026-07-13 to 2026-07-14] (`7162f84`, `e0b0e5c`)

### Added
- Memory v2 P2/P3 tooling and gardener runbook.
- Orchestrator tools: floor and context-budget documentation.
- Lesson sync (wave 6).

## [2026-07-03 to 2026-07-07] (`cf2bf3e`, `46daa28`, `801c548`, `eb6f60a`, `7ef9710`)

### Added
- Lookup-first Delegator routing doctrine.
- Fable-on-Opus reasoning-discipline hook.

### Fixed
- Perpetual git-dirty churn on every `agency upgrade`.
- False CLI relink spam on every `agency upgrade`.

### Changed
- PD/Coord token-efficiency slimming (`N_global=5`).

## [2026-07-02] (`1bc1244`, `f837d84`)

### Security
- Removed personal PD files that had leaked into the public repo.

### Added
- `/save-state` INLINE and SUBAGENT modes.
- Moved `runbooks/` to the repo top level.

## [2026-06-22] (`2ab2ca6`, `9ec9cad`)

### Fixed
- `agency upgrade` now preserves the user's tier setting and re-execs with freshly-pulled code — a zero-lag self-updater that prevents running stale upgrade logic against new repo state.

## [2026-06-08 to 2026-06-18] (`597da37`, `632ae1a`, `1eb2345`, `f0aaac3`, `1873c01`, `187a6a3`, `1cff59f`, `0e146a7`, `4c2c5ba`, `3d9fc95`, `cba6781`, `058369b`, `a767808`, `f300f9e`)

### Added
- Director Upgrade architecture.
- Mandatory service agents.
- `understand-*` agent family.
- Fabrication-guard hooks, autonomy tier gate, LS-PROOF gate.
- `bootstrap-machine.sh` (3-layer portable machine bootstrap) and the `agency initiate` CLI command.
- Graphify MCP setup.

### Removed
- omnivoice-studio and other unportable tools from bootstrap.

## [2026-06-01 to 2026-06-05] (`0979b1c`, `5007c52`, `39db1aa`, `3ae4f3a`, `911d930`, `a3aa2e1`)

### Added
- Critiques department (13 agents).
- Video Studio department (17 agents).
- Dual lite/standard tier packaging.

### Fixed
- CLI symlink re-linking on init/upgrade after a stale clone.

### Security
- Removed private skill entries that had leaked into the public INDEX.

## [2026-05-21 to 2026-06-01] (`6f07124`, `dfb5fcc`, `03c554a`)

### Added
- Delegator-first enforcement.
- Spawn-gate hook.
- Quality-loop protocol plus 8 new skills.

### Security
- Removed `general-purpose` from the spawn-gate allowlist.

## [2026-05-13 to 2026-05-18] (`b471e31`, `0fc1a3e`, `e506a39`, `3ee3bbb`, `5d183cb`, `5135f5a`)

### Added
- `agency onboard` interactive setup wizard.
- Dept-Coord system.
- Delegator and Curator agents.
- `rescue.sh` recovery script.
- Hook lifecycle system (10 scripts).
- `codebase-search` agent.

### Fixed
- Clone target corrected to `~/.claude/` (was briefly `~/the-agency/`).

## [2026-05-08 to 2026-05-12] (`ae18064`, `e03a10b`, `9e8707b`, `d314243`)

### Added
- Memory v2 — 4-typed model with YAML frontmatter.
- Skills restructured to directory layout with an INDEX catalog.
- Installer now copies skills and agents cross-platform.

### Fixed
- Genericized hardcoded paths in the NEXUS protocol for portability.

## [2026-04-16 to 2026-04-18] (`a396fe6`, `538049b`, `9607f2d`)

Initial public release.

### Added
- v2 core system.
- 32 skills.
- PD protocol.
- Agency Rooms.
- Tiered PD → Coord → Task-Executor architecture.
- QA gates with ACK/NACK protocol.

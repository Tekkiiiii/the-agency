---
name: tech-writer
description: "Use when writing developer docs, API references, READMEs, tutorials, docstrings, changelogs, release notes, ADRs or runbooks, or fixing unclear docs. Follows Diataxis (tutorial, how-to, reference, explanation) with templates per doc type; inline comments explain why, not what."
---

# Technical Writing Skill

## When to Activate

Trigger when the user asks to:
- Write developer docs, API references, or README files
- Write tutorials, onboarding guides, or runbooks
- Add inline code comments or docstrings
- Maintain a CHANGELOG or release notes
- Write an Architecture Decision Record (ADR)
- Improve unclear or incomplete documentation

## Documentation Types

| Type | Purpose | Key Questions |
|------|---------|---------------|
| Tutorial | Learning-oriented | What does the user need to try? |
| How-to | Task-oriented | What steps achieve a goal? |
| Reference | Information-oriented | What does X do exactly? |
| Explanation | Understanding-oriented | Why does this work this way? |
| Decision | Rationale | Why did we choose A over B? |

## README Template

Every project deserves a README with these sections:

```
# Project Name

One-line description. Target audience. Current status.

## Quick Start

3-5 commands to go from zero to running. No setup beyond this.

## What This Does

2-3 paragraphs. Lead with outcomes, not implementation.

## Core Concepts

Named concepts, each with a one-paragraph explanation.
Link to deeper docs.

## Examples

The most common use cases, with code.
Zero edge cases here — just the happy path.

## Contributing

Link to full CONTRIBUTING.md or inline process.
```

## API Reference Structure

For every endpoint, document:
- **Endpoint** — method and path
- **Parameters** — name, type, required, description, default
- **Request body** — schema with field types
- **Response** — status codes and response body schema
- **Errors** — all error codes with cause and resolution
- **Example** — curl + response pair

## Inline Comment Standards

Good comments explain **why**, not **what**:
```python
# Retry up to 3x with exponential backoff — NVD API returns 503 under heavy load
# NOT: "This loops 3 times"
```

TODO format with ownership:
```python
# TODO(tkelly, 2026-04-01): Remove this workaround when NVD API adds rate limiting
# Related: github.com/example/sentinel/issues/47
```

## Changelog Format

```
## [1.2.0] — YYYY-MM-DD

### Added
- New endpoint: GET /api/v1/feed with severity filtering
- Daily digest email via SendGrid

### Changed
- Upgraded to FastAPI 0.110 — breaking: /health now returns JSON

### Fixed
- Crawler now retries on 503 from NVD API (was silently dropping)
```

## Runbook Structure

```
# Runbook: [Problem Title]

## Problem Statement
One sentence. Who is affected.

## Symptoms
- Bullet list of what users/operators see

## Diagnosis
Numbered steps with expected vs. actual output.

## Fix
Step-by-step. Each step idempotent.
After each step: how to verify it worked.

## Escalation
When to escalate. Who to contact. What to include in the handoff.
```

## Markdown Quality Rules

- Active voice throughout
- Short sentences — one idea per sentence
- Code blocks always include the language tag
- Avoid walls of text — use tables, bullet lists, headings
- Link to related docs rather than duplicating information
- Spell out acronyms on first use

---
name: tech-writer
description: >
  Technical documentation using the Diátaxis framework — produces four
  doc types (tutorials, how-to guides, reference, explanation), each with
  correct structure and appropriate tone. Triggers when: writing new
  documentation, auditing existing docs, writing README files, or
  documenting a feature. Key capability: Diátaxis-correct doc types that
  match reader intent. Also for: API reference generation, architecture
  decision records (ADRs), runbook templates, and release notes.
---

# /tech-writer — Technical Documentation

Write clear, well-structured technical documentation using the Diátaxis framework.

## When to Activate

Trigger `/tech-writer` when:
- Writing new documentation
- Auditing existing docs
- Writing README files
- Documenting a feature
- Writing API reference
- Creating runbooks

## The Diátaxis Framework

Four doc types, each for a different reader need:

```
DIÁTAXIS DOC TYPES
════════════════════════════════

TUTORIAL — Learning
  Goal:    Learn fundamentals
  Reader:  Beginner, newcomer
  Tone:    Warm, encouraging, directive
  Example: "Getting Started with X"

HOW-TO — Task-oriented
  Goal:    Accomplish a specific thing
  Reader:  Intermediate user
  Tone:    Practical, direct, goal-focused
  Example: "How to Configure OAuth"

REFERENCE — Information
  Goal:    Look up facts
  Reader:  Experienced user
  Tone:   Precise, accurate, no opinion
  Example: "API Reference"

EXPLANATION — Understanding
  Goal:    Understand a topic
  Reader:  Anyone curious
  Tone:    Exploratory, conceptual
  Example: "How Authentication Works"
```

**Rule:** Don't mix types. A tutorial is not a how-to. A how-to is not reference.

## Tutorial Template

### Structure

```
# Tutorial: {title}

## Goal
By the end of this tutorial, you will {specific outcome}.

## Prerequisites
- {required skill or software, e.g., "Node.js 18+ installed"}
- {required skill or software}

## Step 1: {Action}
Do this thing.

{code example or screenshot}

{Expected result explanation}

## Step 2: {Next action}
Do this next thing.

{code example}

## Step 3: {Final action}
{final step}

## Next steps
- {link to related tutorial}
- {link to how-to guide}
- {link to reference docs}
```

### Tutorial Rules

- **Start from a working baseline.** Reader hasn't installed anything yet.
- **Every step has a concrete outcome.** "You should see X" or "Y is now running."
- **No choices.** Tutorials are linear — one way to do it.
- **Celebrate success.** End with a working result.
- **No caveats, troubleshooting, or alternatives.** Save for end or separate doc.

## How-To Guide Template

### Structure

```
# How to: {specific goal}

## Before you start
- {assumptions, e.g., "You have a Vercel account"}
- {assumptions}

## Step 1: {action verb}
{one specific task}

{code or CLI command}

{what to expect}

## Step 2: {action verb}
{another task}

{code or CLI command}

## Step 3: {action verb}
{final task}

{optional "what if" section for common variations}

## Related tasks
- {link to related how-to}
```

### How-To Rules

- **Address the reader's goal directly.** Don't explain, just do.
- **Name the steps as actions.** "Configure", "Deploy", "Set up" — not "Step 1".
- **Include troubleshooting callouts.** If this step commonly fails, warn.
- **Offer variations.** "You can also do X if you prefer Y."

## Reference Template

### API Reference Structure

```
# API Reference

## Authentication
{how to authenticate, token format, where to get tokens}

## Endpoints

### GET /resource
Description of what this returns.

**Request:**
{headers, query params, body if any}

**Response:** `200 OK`
```json
{response shape}
```

**Errors:**
- `401 Unauthorized` — {reason}
- `404 Not Found` — {reason}
- `422 Unprocessable` — {reason}

### POST /resource
{repeat structure}

## Data Types

### Resource
```typescript
{type definition}
```

## Rate Limits
{limits and headers}
```

### Reference Rules

- **Accurate only.** No "approximately" or "usually" — these are facts.
- **Complete.** Include all parameters, all response fields, all error codes.
- **No explanation.** Reference docs don't explain WHY — only WHAT.
- **Machine-readable if possible.** OpenAPI spec alongside human docs.

## Explanation Template

```
# {Concept name}

## Overview
{one-paragraph plain-language summary}

## How it works
{technical explanation without implementation}

## Why it matters
{what problem this solves, why the reader should care}

## Common use cases
- {use case 1}
- {use case 2}

## Related concepts
- {link to related explanation}
- {link to how-to guide that uses this concept}
```

### Explanation Rules

- **Conceptual first.** What is this, why does it exist, when would I use it?
- **No step-by-step.** Save for how-to guides.
- **No code snippets.** Code belongs in how-to and tutorial.

## README Template

```
# {Project Name}

{One-line description}

[![CI](https://img.shields.io/github/actions/workflow/status/{org}/{repo}/ci.yml)](https://github.com/{org}/{repo}/actions)
[![npm](https://img.shields.io/npm/v/{package})](https://npmjs.com/{package})

## Install

npm:     `npm install {package}`
Yarn:    `yarn add {package}`
pnpm:    `pnpm add {package}`

## Quick Start

{2-3 lines of most common usage}

## Documentation

- [Getting Started](docs/getting-started.md)
- [API Reference](docs/api.md)
- [How to: {task}](docs/how-to/{task}.md)
- [Contributing](CONTRIBUTING.md)

## Requirements

- Node.js 18+
- {other requirements}

## License

MIT
```

## Architecture Decision Record (ADR) Template

```
# ADR {number}: {title}

**Date:** {YYYY-MM-DD}
**Status:** {PROPOSED | ACCEPTED | SUPERSEDED | REJECTED}

## Context
{problem statement and background}

## Decision
{what was decided}

## Consequences

**Positive:**
- {benefit 1}

**Negative:**
- {drawback 1}

**Neutral:**
- {neither positive nor negative}

## Alternatives considered

### Alternative 1: {name}
Pros: {pros}
Cons: {cons}

### Alternative 2: {name}
Pros: {pros}
Cons: {cons}
```

## Runbook Template

```
# Runbook: {title}

## What this runbook covers
{one sentence}

## Prerequisites
- Access to {system}
- Permissions: {list}
- Tools: {list}

## Procedure

### Normal operation
{steps for normal day-to-day operation}

### Incident response
{steps when something goes wrong}

#### Symptoms
- {symptom 1}
- {symptom 2}

#### Diagnosis
{how to determine what's happening}

#### Resolution
{how to fix}

## Rollback
{how to undo this change}

## Contacts
- On-call: {contact}
- Team: {contact}
```

## Important Rules

- **Match type to reader intent.** A beginner needs a tutorial. An expert needs reference.
- **Never mix types.** A doc is one type, not a combination.
- **Tutorials teach. How-tos guide. Reference informs. Explanation explains.**
- **Write for scanning.** Most readers skim first, read second. Headings, bullets, bold.
- **No jargon without definition.** If you use a technical term, define it first or link to definition.
- **Keep reference accurate.** Stale reference is worse than no reference.

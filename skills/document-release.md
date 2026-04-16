---
name: document-release
description: >
  Post-ship documentation — produces changelog, cross-document consistency
  checks, release summaries for teammates, and compliance audit trail. Triggers
  when: after shipping a new feature, version bump, or significant change;
  during release retrospective; or when onboarding new team members who need
  to understand what shipped and why. Key capability: automatic changelog
  generation from git history, conventional commit parsing, and diff-to-doc
  mapping. Also for: API changelog maintenance, runbook updates triggered by
  deploy, and doc versioning alignment.
---

# /document-release — Post-Ship Documentation

Generate and maintain documentation when software ships.

## When to Activate

Trigger `/document-release` when:
- After shipping a new feature or version
- During release retrospective
- Onboarding new team members
- API changelog needs updating
- Runbook needs deploy-triggered update

## Preamble

```
/document-release {target}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} describe --tags --abbrev=0 2>/dev/null || echo "no tag"
git -C {target} log --oneline -20
git -C {target} ls-files CHANGELOG.md HISTORY.md docs/ 2>/dev/null
```

## Step 1: Parse Release Commits

### Get commits since last release

```bash
# Since last tag
git -C {target} log $(git -C {target} describe --tags --abbrev=0 2>/dev/null)..
--oneline --format="|%s|%an|%ad" --date=short 2>/dev/null

# Since last release branch
git -C {target} log origin/release/last..HEAD --oneline 2>/dev/null

# From PR merge commits
git -C {target} log --merges --format="%s" -10 2>/dev/null
```

### Parse conventional commits

```
CONVENTIONAL COMMIT FORMAT: type(scope): description

Types:
- feat:     New feature
- fix:      Bug fix
- docs:     Documentation only
- style:    Formatting, no code change
- refactor: Code change that neither fixes nor adds
- perf:     Performance improvement
- test:     Adding or updating tests
- chore:    Maintenance tasks
- revert:   Reverting a previous change

Parse each commit and categorize:
```

| Commit | Type | Scope | Description |
|--------|------|-------|-------------|
| `feat(auth): add OAuth2 login` | feat | auth | ... |
| `fix(api): handle null user id` | fix | api | ... |
| `docs: update README` | docs | — | ... |

### Aggregate by type

```
RELEASE SUMMARY — {version}
════════════════════════════════

Features: {N}
- {list of feature descriptions}

Bug Fixes: {N}
- {list of bug fix descriptions}

Breaking Changes: {N}
- {list with migration instructions}

Documentation: {N}
- {list of doc changes}

Other: {N}
- {list}
```

## Step 2: Generate or Update CHANGELOG

### Find CHANGELOG.md

```bash
ls {target}/CHANGELOG.md {target}/HISTORY.md {target}/CHANGES.md 2>/dev/null
```

### Update existing CHANGELOG

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{version}] — {YYYY-MM-DD}

### Added
- Feature: {description} ({scope})
- Feature: {description} ({scope})

### Changed
- Change: {description}

### Fixed
- Fix: {description}

### Deprecated
- Deprecation: {description}

### Removed
- Removal: {description}

### Security
- Security: {description}

### Breaking Changes
- Breaking: {description} — migration: {instructions}
```

### Generate unreleased section

```bash
# Preview what would go into the changelog
git -C {target} log --oneline --format="* %s" $(git -C {target} describe --tags --abbrev=0)..HEAD 2>/dev/null
```

## Step 3: Cross-Document Consistency Check

### Verify consistency across docs

```bash
# List all doc files
git -C {target} ls-files | grep -E '\.(md|rst|txt)$' | grep -v node_modules | grep -v '.git'

# Check README references the current version
grep -E '(version|Version|VERSION|v[0-9])' {target}/README.md 2>/dev/null

# Check API docs match implementation
git -C {target} ls-files | grep -E 'api|openapi|swagger' 2>/dev/null
```

### Checklist

```
CROSS-DOC CONSISTENCY CHECKLIST
════════════════════════════════

README.md:
□ Version number current
□ Installation instructions accurate
□ Dependencies listed and correct
□ Badges (CI, coverage, version) up to date

API Documentation:
□ Endpoint list matches routes
□ Request/response schemas current
□ Authentication section accurate
□ Error codes documented

Runbooks / Operations:
□ Deploy steps match current process
□ Rollback procedure accurate
□ Environment variables documented
□ Secrets documented (not values)

Architecture Decision Records (ADRs):
□ New decisions recorded
□ Previous decisions still valid
□ Status: ACCEPTED | SUPERSEDED | REJECTED
```

### Update README if needed

```bash
# Read current README
head -50 {target}/README.md

# Check for version badges
grep -E '!(.*)\.svg' {target}/README.md

# Check links
grep -E '\[.*\]\(.*\)' {target}/README.md | head -20
```

## Step 4: Release Notes

### Generate for different audiences

**For developers (internal):**
```markdown
## What's New for Developers — v{version}

### Breaking Changes
- {description}
  Migration: {steps}

### New Features
- {Feature name}: {description}
  PR: #{number}

### Bug Fixes
- {description}
  PR: #{number}

### Internal Changes
- {refactor/test/infra}
```

**For end users (external):**
```markdown
## What's New in v{version}

### New Features
- {user-facing feature descriptions}

### Improvements
- {improvement descriptions}

### Bug Fixes
- {fix descriptions}

### Known Issues
- {issues with workaround if available}
```

**For stakeholders (summary):**
```markdown
## Release Summary — v{version}
- {N} new features shipped
- {N} bugs fixed
- {N} breaking changes
- Estimated deploy time: {N} minutes
- Rollback plan: {procedure}
```

## Step 5: API Changelog

### Check for API changes

```bash
# Find API route files
find {target} -name "routes*" -o -name "*route*" -o -name "*controller*" -o -name "*handler*" 2>/dev/null | grep -v node_modules | head -20

# Check OpenAPI/Swagger specs
find {target} -name "openapi*" -o -name "swagger*" -o -name "*.yaml" -o -name "*.yml" 2>/dev/null | grep -v node_modules | head -10
```

### API change categories

```
API CHANGES — {version}
════════════════════════════════

New endpoints: {N}
- Method /path — {description}

Modified endpoints: {N}
- GET /items — added filter param

Deprecated endpoints: {N}
- GET /legacy — deprecated, remove in v{next}

Removed endpoints: {N}
- DELETE /old — removed, use POST /new

Schema changes:
- {model} field changes
```

## Step 6: Compliance & Audit Trail

### Document decisions for audit

```bash
# Check for security-relevant changes
git -C {target} diff $(git -C {target} describe --tags --abbrev=0)..HEAD \
  -- '*auth*' '*security*' '*permission*' '*role*' '*encrypt*' 2>/dev/null | head -50
```

### Audit checklist for compliance

```
COMPLIANCE AUDIT — v{version}
════════════════════════════════

Data handling changes:
□ New fields collected: {list}
□ New PII fields: {list or "none"}
□ New third-party integrations: {list or "none"}

Security changes:
□ New auth mechanisms: {list}
□ New permissions model: {describe}
□ New data access paths: {list}

Breaking changes affecting compliance:
□ List changes that affect audit trails
□ List changes that affect data retention
□ List changes that affect consent flows
```

## Step 7: Doc Version Alignment

### Version docs if multi-version

```bash
# Check versioning strategy
ls {target}/docs/versions/ 2>/dev/null
ls {target}/docs/{major}/ 2>/dev/null
git -C {target} tag --list 'v*' | tail -5
```

### Update version docs

```
DOC VERSION ALIGNMENT — v{version}
════════════════════════════════

Current docs version: {version}
Status: UP TO DATE | NEEDS UPDATE | NEW VERSION

Changes requiring doc update:
1. {change 1}
2. {change 2}

Files to update:
- docs/{file} — {reason}
- README.md — {reason}

Files to create:
- docs/{new-file} — {reason}
```

## Step 8: Announcement Draft

### Generate team announcement

```
RELEASE ANNOUNCEMENT — v{version}
════════════════════════════════

Subject: Shipped: v{version} {one-line summary}

Hi team,

v{version} is live. Here's what shipped:

Highlights:
- {most important feature}
- {second most important feature}

For developers:
- Breaking changes: {list with migration links}
- New env vars: {list}
- Migration guide: {link}

For QA:
- Test scope: {list}
- Smoke test cases: {link}

For ops:
- Deploy time: ~{N} minutes
- Rollback: {procedure}
- Hotfix process: {link}

Full changelog: {link}

Thanks to: {contributors}

— {your name}
```

## Important Rules

- **CHANGELOG is not optional.** Every release gets a CHANGELOG entry.
- **Breaking changes are non-negotiable to document.** Don't let them sneak out undocumented.
- **Cross-doc consistency is a real problem.** A feature that shipped but isn't in the README isn't shipped.
- **Conventional commits make this automatic.** Enforce them via CI.
- **Compliance documentation is auditable.** If it's not written down, it didn't happen.

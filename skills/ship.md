---
name: ship
description: >
  Automates the full ship workflow: base branch detection → fetch/checkout →
  diff analysis → bisect to clean commits → CHANGELOG/VERSION update →
  PR creation → test run → review gate → deploy trigger. The ship skill is
  the connective tissue between "done with a branch" and "deployed to
  production" — it runs after feature work is complete and drives everything
  to the point where the PR exists and is ready for merge. Trigger when the
  user says "ship it", "ready to merge", "/ship", or similar. Also for:
  forcing a ship (skip review gate), shipping a specific range of commits,
  and checking ship status mid-flight. Best for: developers who want one
  command to take a clean feature branch from "done" to "PR created and
  CI green."
---

# /ship — Ship a Feature Branch

Takes a feature branch from "done" to "PR created, reviewed, and ready to
merge" in one command.

## When to Activate

Trigger `/ship` when:
- Feature work on a branch is complete
- All tests pass locally
- You're ready to create a PR
- You want to run the full ship workflow

## Arguments

- `/ship` — standard ship, all steps
- `/ship --force` — skip review gate (ship without review)
- `/ship <sha>..HEAD` — ship a specific commit range
- `/ship --status` — check ship status mid-flight

## Instructions

### Step 0: Detect Base Branch

Determine which branch this PR targets:

```bash
gh pr view --json baseRefName -q .baseRefName
```

If no PR exists yet, detect the default branch:

```bash
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
```

Print the detected base branch name. Use this throughout.

### Step 1: Fetch and Verify

```bash
git fetch origin {base}
git log {base}..HEAD --oneline
```

Show the commit log. If there are no commits beyond base, stop: "Nothing to
ship — branch is identical to base."

### Step 2: Analyze the Diff

```bash
git diff {base}...HEAD --stat
```

Show what changed: files, lines added/removed, categories (feat/fix/docs/test).

### Step 3: Bisect to Clean Commits

For each commit in the range:
1. Run `git log -1 --format="%s" <sha>` to get the commit message
2. Classify as: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `unknown`
3. Flag any commit that looks like it shouldn't be shipped (WIP, debug, etc.)

If messy commits are found, offer to squash interactively:
```
RECOMMENDATION: Squash into clean commits before shipping.
- feat: add user authentication
- fix: correct CORS headers
- docs: update README
```

### Step 4: Update CHANGELOG and VERSION

Read the current `CHANGELOG.md` and `VERSION` file.

**VERSION bump decision:**
- Major bump (X+1.0.0): breaking API changes
- Minor bump (X.Y+1.0): new features, backward-compatible
- Patch bump (X.Y.Z+1): bug fixes, no feature changes

Ask if not clear from context.

**CHANGELOG entry:**
Write a changelog entry for this release. Format:
```
## [{version}] — {date}

### Added
- {feature 1}
- {feature 2}

### Changed
- {change 1}

### Fixed
- {fix 1}
```

Write the entry at the top of CHANGELOG.md (after the header).

### Step 5: Stage and Commit Doc Updates

```bash
git add CHANGELOG.md VERSION
git commit -m "chore: bump version to {version} for release"
```

### Step 6: Push Branch

```bash
git push origin HEAD
```

### Step 7: Create or Update PR

```bash
gh pr create --title "[{version}] {short description}" --body-file /tmp/pr-body-{pid}.md
```

**PR body template:**
```
## What Changed

{summary of changes from diff analysis}

## Testing

- [ ] Tests pass locally
- [ ] No new linting errors
- [ ] Hand-tested the feature

## Deploy Notes

{any special deploy steps, env var changes, etc.}

## Screenshots

{if UI changes}
```

### Step 8: Run Tests (if CI configured)

```bash
bun test 2>&1 | tail -20
```

If tests pass, proceed. If they fail, stop and report failures.

### Step 9: Review Gate

**Standard mode:** Check for required reviews:
- Are any REQUIRED reviewers configured on this repo?
- If yes, has the PR been assigned to them?

Show the PR URL and ask: "Ready to request review from [reviewers]?"

**Force mode (`--force`):** Skip the review gate. Print a warning: "Review gate skipped — ship forced."

### Step 10: Trigger Deploy (if configured)

If the project has a deploy workflow (GitHub Actions, CI/CD):
```bash
gh run list --branch HEAD --limit 3
```

Show the deploy status.

### Step 11: Ship Report

```
SHIP REPORT — {version}
═══════════════════════════
Branch:       {branch} → {base}
Commits:      {N} ({clean list or "squash recommended"})
Version:      {old} → {new}
PR:           {url}
Tests:        {pass|fail}
Deploy:       {triggered|not configured}

Next steps:
- Open {PR URL} and request review
- Monitor CI at: {run URL}
- Run /land-and-deploy when ready to merge
```

## Important Rules

- **Bisect to clean commits.** Don't ship WIP commits or debug artifacts.
- **CHANGELOG is for users.** Write what changed from a user perspective,
  not a developer perspective.
- **VERSION follows semver.** Don't skip minor bumps for features.
- **PR body is a checklist.** Make it easy for reviewers to know what to test.
- **/ship is not /land-and-deploy.** This creates the PR. `/land-and-deploy`
  merges it and verifies production.

---
name: land-and-deploy
description: >
  End-to-end merge-to-deploy pipeline — merges a branch, runs the full
  CI/CD pipeline, monitors canary traffic, promotes or rolls back based on
  health signals, and sends a status report. The pre-merge readiness gate
  catches broken deploys before they ship. Trigger when: merging to main for
  release, deploying to production, or managing a staged rollout (canary →
  full). Key capability: zero-downtime rollback at every stage. Also for:
  hotfix deploys, release candidate promotion, and multi-environment
  sequential deploys.
---

# /land-and-deploy — End-to-End Deploy Pipeline

Full merge → deploy → canary → promote pipeline with health gates.

## When to Activate

Trigger `/land-and-deploy` when:
- Merging to main for release
- Deploying to production
- Managing a staged rollout
- Hotfix promotion
- Release candidate pipeline

## Preamble

```
/land-and-deploy {branch-to-deploy}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} branch -a
git -C {target} remote -v
git -C {target} ls-files .github/workflows/ .gitlab-ci.yml docker-compose.yml Dockerfile* Railway.toml fly.toml vercel.json 2>/dev/null
```

**gstack update check:**
```
────────────────────────────────────────
PREAMPBLE CHECK — LAND-AND-DEPLOY
────────────────────────────────────────
1. Run:    git -C {target} log --oneline -1
2. Update: Check ~/.claude/gstack/update.json
           Compare {target} against last-deploy SHA
           If current SHA matches last-deploy SHA → SKIP (nothing to deploy)
3. Repo mode detection:
           git -C {target} rev-parse --is-inside-work-tree 2>/dev/null
           git -C {target} ls-files 2>/dev/null | head -5
           git -C {target} remote -v 2>/dev/null
           Detect: monorepo | multi-repo | single | unknown
4. Deploy scope:  {target}/
           Deployable subpackages: {list}
5. Last deploy:   {SHA or "none"}
   This deploy:   {current SHA}
────────────────────────────────────────
```

## Step 0: Pre-Merge Readiness Gate

**Run BEFORE merging. This gate catches broken deploys before they ship.**

### 0a: Verify branch is ready

```bash
cd {target}
git fetch origin

# Verify branch state
git log origin/main..{branch} --oneline
# Expected: clean, intentional commits

# Verify tests pass locally
npm test 2>&1 | tail -10
# or
pytest tests/ -v 2>&1 | tail -10
# or
cargo test 2>&1 | tail -20
```

### 0b: Run QA on the branch

```
/qa {target}
```

See `/qa` skill for full QA loop. Key checks:
- Critical paths load without JS console errors
- No layout breakage at common viewport sizes
- Hot paths return expected status codes

**Gate: QA must pass before proceeding.** If QA fails, stop and report findings.

### 0c: Check for risky changes

```bash
# Warn on these changes without blocking
git diff origin/main --stat | grep -E '(package-lock|yarn.lock|package.json)' && echo "⚠️ Dependency changes — verify lock file is committed"

# Block on these without confirmation
git diff origin/main --stat | grep -E '(docker-compose|Dockerfile|\.gitlab-ci|\.github/workflows/)' && echo "⚠️ Infra changes — verify CI passes"
```

### 0d: Check CI status

```bash
# GitHub Actions
gh run list --limit 5

# Check if CI is green on the branch
gh run list --branch {branch} --limit 3
```

**Gate: CI must be passing on the branch before merge.**

### Pre-Merge Gate Summary

```
PRE-MERGE GATE — {branch}
════════════════════════════════
Local tests:       PASS | FAIL
QA result:         PASS | FAIL
CI status:         PASS | FAIL | UNKNOWN
Dependency diff:   CLEAN | CHANGED
Infra diff:        CLEAN | CHANGED

GATE: READY TO MERGE | STOP — FIX ISSUES
```

## Step 1: Merge to Main

```bash
cd {target}

# Option A: GitHub UI merge (preferred — better history)
gh pr merge {pr-number} --squash --delete-branch
# Then pull
git pull origin main

# Option B: CLI merge (when GitHub is unavailable)
git checkout main
git pull origin main
git merge {branch}
git push origin main
```

## Step 2: Tag the Release

```bash
# Determine version
# Read current version:
cat VERSION.txt 2>/dev/null || git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"

# Prompt for version bump:
# PATCH (bug fixes): v1.2.3 → v1.2.4
# MINOR (new features): v1.2.3 → v1.3.0
# MAJOR (breaking): v1.2.3 → v2.0.0

git tag v{NEW_VERSION}
git push origin v{NEW_VERSION}
```

## Step 3: Run CI Pipeline

```bash
# Monitor GitHub Actions
gh run list --limit 3

# Follow the run
gh run watch {run-id}

# View logs on failure
gh run view {run-id} --log-failed | tail -50
```

**Gate: CI must pass before deploy proceeds.**

## Step 4: Deploy

### Detect platform and deploy

```bash
# Check for deploy config
if [ -f "vercel.json" ]; then
  echo "Platform: Vercel"
  npx vercel deploy --prod
elif [ -f "Railway.toml" ]; then
  echo "Platform: Railway"
  railway deploy --environment production
elif [ -f "fly.toml" ]; then
  echo "Platform: Fly.io"
  flyctl deploy --remote-only
elif [ -f ".github/workflows/deploy.yml" ]; then
  echo "Platform: GitHub Actions (watch for workflow trigger)"
  echo "Monitor: gh run list"
else
  echo "Platform: Unknown — manual deploy required"
fi
```

### Wait for deploy completion

```bash
# Poll until healthy
for i in {1..30}; do
  URL=$(get_deploy_url)
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$URL/health" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "DEPLOY HEALTHY at ${i}s"
    break
  fi
  echo "Waiting... ${i}s (status: $STATUS)"
  sleep 5
done
```

## Step 5: Canary Deployment

**Canary traffic: 5% → 25% → 100%**

### Canary Phase 1: 5% Traffic

```bash
# Route 5% to new version
# Vercel: automatic via percentage split in dashboard
# Railway: railway variables set CANARY_WEIGHT=5
# Fly.io: flyctl alloc active -p {percentage}=5

echo "CANARY PHASE 1: 5% traffic"
echo "Duration: 5 minutes"
sleep 300

# Check metrics
curl -sf "https://$PROD_URL/health" > /dev/null && echo "OK" || echo "ERROR"
```

### Canary Phase 2: 25% Traffic

```bash
echo "CANARY PHASE 2: 25% traffic"
echo "Duration: 10 minutes"
# Adjust traffic split
sleep 600

# Check error rate
ERROR_RATE=$(get_error_rate)
if [ "$ERROR_RATE" -gt 1 ]; then
  echo "ERROR RATE HIGH: $ERROR_RATE% — ROLLBACK?"
  # See Step 7
fi
```

### Canary Phase 3: 100% Promotion

```bash
echo "CANARY PHASE 3: Full promotion"
# Promote canary to 100%
# Remove old version
```

## Step 6: Monitor

### Health signals

```bash
# Error rate
ERROR_RATE=$(get_error_rate)
# Threshold: > 1% → alert, > 5% → rollback

# Latency
P50_LATENCY=$(get_p50_latency)
P99_LATENCY=$(get_p99_latency)
# Threshold: P99 > 500ms → alert

# Uptime
curl -sf "https://$PROD_URL/health" || echo "UNHEALTHY"
```

### Monitor loop

```
MONITOR — {version}
════════════════════════════════
Error rate:  {N}% (threshold: 1%)
P99 latency: {N}ms (threshold: 500ms)
Uptime:     OK | DEGRADED | DOWN

Status: MONITORING | PROMOTING | ROLLING BACK
```

## Step 7: Rollback

### Trigger rollback

```bash
# Railway
railway rollback --deployment @previous

# Vercel
npx vercel alias d_YYYYYYYY.vercel.app production

# Fly.io
flyctl deploy --image {previous-image}

# Generic
git checkout v{previous-version}
# Redeploy via CI or direct push
```

### Rollback procedure

```
ROLLBACK — {version} → v{previous}
════════════════════════════════
Trigger:   {reason}
Timestamp: {ISO time}
Duration:  {estimated}

Executing rollback...
Rolling back...
Verifying health...
Rollback complete.
```

## Step 8: Ship Report

```
═══════════════════════════════════════════════════════
LAND-AND-DEPLOY REPORT — {version}
═══════════════════════════════════════════════════════

COMMIT:     {sha} {message}
BRANCH:     {branch} → main
MERGED BY:  {actor}
DEPLOYED:   {ISO timestamp}
PLATFORM:   {platform}
DURATION:   {total minutes} minutes

CANARY:
Phase 1 (5%):  {N}s — {PASS|FAIL}
Phase 2 (25%): {N}s — {PASS|FAIL}
Phase 3 (100%): {N}s — {PASS|FAIL}

FINAL STATE:
Error rate:   {N}%
P99 latency:  {N}ms
Health:       {OK|DEGRADED|DOWN}

STATUS: SHIPPED | ROLLED BACK

REPORT GENERATED: {ISO timestamp}
```

## Important Rules

- **Pre-merge gate is non-negotiable.** Don't skip QA or CI checks to save time.
- **Canary phases exist for a reason.** Each phase is a chance to catch failures.
- **Rollback is not failure.** A good rollback is a working safety system.
- **Tag everything that ships.** Tags are the only reliable rollback target.
- **Report everything.** Post-deploy reports are how you learn from releases.

---
name: github-deploy
description: >
  GitHub Actions deployment — sets up and manages CI/CD pipelines for any
  platform using the gh CLI, GitHub Actions, and platform-specific deploy
  steps. Handles secrets management, environment promotion, rollback, and
  rollback triggers. Trigger when: setting up a new deploy pipeline, fixing
  a broken GitHub Actions workflow, adding a new environment (staging/prod),
  or rotating deploy secrets. Key capability: platform templates for
  Railway, Fly.io, Vercel, and generic shell deploys. Also for: GitHub
  Actions troubleshooting, secrets rotation, and multi-environment promotion.
---

# /github-deploy — GitHub Actions Deployment Pipeline

Set up, manage, and troubleshoot GitHub Actions deployment pipelines.

## When to Activate

Trigger `/github-deploy` when:
- Setting up a new CI/CD pipeline
- Fixing a broken GitHub Actions workflow
- Adding a new environment (staging, production)
- Rotating deploy secrets
- Troubleshooting a failed deploy

## Preamble

```
/github-deploy {workflow-name}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} remote -v
git -C {target} ls-files .github/workflows/ 2>/dev/null
```

## Platform Templates

### Railway Template

```yaml
name: Deploy to Railway
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway deploy --service ${{ vars.RAILWAY_SERVICE }}

      - name: Health Check
        run: |
          sleep 10
          curl -sf ${{ vars.RAILWAY_URL }}/health || exit 1
```

**Secrets needed:** `RAILWAY_TOKEN`
**Variables needed:** `RAILWAY_URL`, `RAILWAY_SERVICE`

### Fly.io Template

```yaml
name: Deploy to Fly.io
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Flyctl
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: flyctl deploy --remote-only
```

**Secrets needed:** `FLY_API_TOKEN`

### Vercel Template

```yaml
name: Deploy to Vercel
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy-preview:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy Preview
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          github-token: ${{ secrets.GITHUB_TOKEN }}

  deploy-production:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy Production
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Secrets needed:** `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

### Generic Shell Deploy Template

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        if: runner.os == 'Linux'
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Deploy
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
          SERVER: ${{ vars.DEPLOY_SERVER }}
        run: |
          # Your deploy command here
          echo "Deploying to $SERVER"
          ssh $SERVER "cd /app && git pull && npm install && pm2 restart app"
```

## Adding a New Environment

### Step 1: Create environment file

Create `.github/environments/{env}.yml`:

```yaml
name: Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    environment:
      name: production
      url: https://prod.example.com
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... deploy steps
```

### Step 2: Add environment protection rules

```bash
# Via gh CLI
gh api repos/{owner}/{repo}/environments/production -X PUT \
  -f wait_timer=30 \
  -f reviewers='[{"type":"User","id":"123"}]' \
  -f deployment_branch_policy='{"protected_branches":true,"custom_branch_policies":false}'
```

### Step 3: Add environment secrets

```bash
gh secret set SECRET_NAME --env production < value.txt
```

## Secrets Management

### List current secrets

```bash
gh secret list --env production
gh secret list --org ORG --env production
```

### Rotate a secret

```bash
# 1. Generate new token in platform dashboard
# 2. Update via gh
gh secret set DEPLOY_TOKEN --env production
# Paste new token when prompted

# 3. Verify workflow uses correct secret
grep -r 'secrets\.' .github/workflows/
```

### Secret naming conventions

| Secret | Purpose |
|--------|---------|
| `DEPLOY_TOKEN` | Platform API token |
| `SSH_KEY` | Server access key |
| `REGISTRY_TOKEN` | Container registry auth |
| `CODECOV_TOKEN` | Coverage reporting |

## Troubleshooting GitHub Actions

###查看失败的 workflow run

```bash
# List recent runs
gh run list --limit 5

# View run details
gh run view {run-id}

# View failure logs
gh run view {run-id} --log-failed | tail -50

# Download logs
gh run view {run-id} --log > run-logs.txt
```

### Common failures and fixes

**Permission denied:**
```yaml
# Add to workflow
permissions:
  contents: read
  deployments: write
```

**Secret not found:**
```bash
# Verify secret exists in correct scope
gh secret list --env production
gh api repos/{owner}/{repo}/environments/production/secrets
```

**Runner not found:**
```yaml
# Specify correct runner
runs-on: ubuntu-latest
# or self-hosted:
runs-on: self-hosted
```

## Rollback via GitHub Actions

### Add rollback job to workflow

```yaml
rollback:
  runs-on: ubuntu-latest
  if: failure() && github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4

    - name: Rollback Railway
      env:
        RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      run: railway rollback --deployment @previous
```

### Trigger rollback manually

```bash
gh workflow run rollback.yml --field environment=production
```

## Important Rules

- **Secrets go in GitHub, not in code.** Never commit tokens.
- **Environment protection is real.** Require reviewers before prod deploys.
- **Test workflows with pull requests.** Don't let main break.
- **Logs are your friend.** `gh run view --log-failed` before asking for help.
- **Idempotent deploys.** The same workflow should succeed if run twice.

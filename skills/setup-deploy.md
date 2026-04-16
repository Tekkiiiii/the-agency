---
name: setup-deploy
description: >
  Deploy configuration — detects the current platform, configures the
  deployment pipeline, writes the CLAUDE.md deploy section, and creates
  platform-specific configuration files. Triggers when: setting up a new
  project for deployment, configuring CI/CD for the first time, or moving
  a project to a new hosting platform. Key capability: automatic platform
  detection and configuration generation for Fly.io, Render, Vercel, Netlify,
  and GitHub Actions. Also for: multi-cloud setup, environment configuration
  management, and initial hosting provider onboarding.
---

# /setup-deploy — Deploy Configuration

Detect platform, configure pipeline, write CLAUDE.md deploy section.

## When to Activate

Trigger `/setup-deploy` when:
- Setting up a new project for deployment
- Configuring CI/CD for the first time
- Moving to a new hosting platform
- Multi-cloud setup
- Initial hosting provider onboarding

## Preamble

```
/setup-deploy {target}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} remote -v
git -C {target} ls-files package.json Dockerfile docker-compose.yml Railway.toml fly.toml vercel.json netlify.toml .github/workflows/ 2>/dev/null
```

## Step 1: Platform Detection

### Detect existing platform

```bash
# Check for existing deploy configs
if [ -f "{target}/vercel.json" ]; then
  PLATFORM="vercel"
elif [ -f "{target}/Railway.toml" ] || [ -f "{target}/railway.toml" ]; then
  PLATFORM="railway"
elif [ -f "{target}/fly.toml" ]; then
  PLATFORM="fly"
elif [ -f "{target}/netlify.toml" ]; then
  PLATFORM="netlify"
elif [ -f "{target}/.github/workflows/deploy.yml" ]; then
  PLATFORM="github-actions"
else
  PLATFORM="none"
fi

echo "Detected platform: $PLATFORM"
```

### Check repo type

```bash
git -C {target} ls-files --empty-dirs 2>/dev/null | head -20
git -C {target} remote -v 2>/dev/null
```

### Detect project type

```bash
# Node.js
if [ -f "{target}/package.json" ]; then
  cat {target}/package.json | grep -E '"(start|build|dev|scripts)"' | head -5
fi

# Python
if [ -f "{target}/requirements.txt" ] || [ -f "{target}/pyproject.toml" ]; then
  echo "Python project detected"
fi

# Go
if [ -f "{target}/go.mod" ]; then
  echo "Go project detected"
fi

# Ruby
if [ -f "{target}/Gemfile" ]; then
  echo "Ruby project detected"
fi
```

## Step 2: Generate Deploy Config

### Fly.io

```bash
# Generate fly.toml
flyctl init --no-interactive \
  --app {app-name} \
  --org {org-name}

# Or create manually:
cat > {target}/fly.toml << 'EOF'
app = "{app-name}"
primary_region = "iad"

[build]
  builder = "paketo-buildpacks/nodejs"

[env]
  PORT = "8080"

[[services]]
  http_checks = []
  internal_port = 8080

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.checks]]
    path = "/health"
    interval = "10s"
    timeout = "2s"
    grace_period = "5s"
    restart_limit = 3
EOF
```

### Render

```bash
# Create render.yaml
cat > {target}/render.yaml << 'EOF'
services:
  - type: web
    name: {app-name}
    env: node
    region: oregon
    plan: starter
    buildCommand: npm run build
    startCommand: npm start
    healthCheckPath: /health
    envVars:
      - key: NODE_ENV
        value: production
    autoDeploy: true
EOF
```

### Vercel

```bash
# Create vercel.json
cat > {target}/vercel.json << 'EOF'
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": null,
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.js" },
    { "src": "/(.*)", "dest": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
EOF
```

### Netlify

```bash
# Create netlify.toml
cat > {target}/netlify.toml << 'EOF'
[build]
  command = "npm run build"
  publish = "dist"
  functions = "functions"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
EOF
```

## Step 3: Environment Configuration

### Create .env.example

```bash
# Generate .env.example from existing .env or code inspection
# Always exclude: .env, .env.local, .env.production, .env.*.local

cat > {target}/.env.example << 'EOF'
# Required environment variables
# Copy to .env.local for local development

# Application
NODE_ENV=development
PORT=3000

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Auth
JWT_SECRET=your-secret-here
SESSION_SECRET=your-session-secret

# External services
STRIPE_API_KEY=sk_test_xxx
SENDGRID_API_KEY=SG.xxx

# Optional
LOG_LEVEL=info
CACHE_TTL=3600
EOF

# Add to .gitignore
if ! grep -q "\.env" {target}/.gitignore 2>/dev/null; then
  echo -e "\n# Environment" >> {target}/.gitignore
  echo ".env" >> {target}/.gitignore
  echo ".env.local" >> {target}/.gitignore
  echo ".env.production" >> {target}/.gitignore
fi
```

### Environment matrix

```
ENVIRONMENT CONFIG MATRIX
════════════════════════════════

Development (.env.local):
  NODE_ENV=development
  DEBUG=true
  LOG_LEVEL=debug

Staging:
  NODE_ENV=staging
  DEBUG=false
  LOG_LEVEL=info

Production:
  NODE_ENV=production
  DEBUG=false
  LOG_LEVEL=warn

All environments require:
  - DATABASE_URL
  - JWT_SECRET
  - PORT (default set by platform)
```

## Step 4: Write CLAUDE.md Deploy Section

```bash
# Read current CLAUDE.md
cat {target}/CLAUDE.md 2>/dev/null || echo "No CLAUDE.md found"

# Append deploy section
cat >> {target}/CLAUDE.md << 'EOF'

## Deployment

### Platform
{platform}

### Deploy command
{npm run deploy / railway up / etc.}

### Environment variables
See .env.example for required variables.

### Health check
{path and expected response}

### Rollback
{rollback command for this platform}

### CI/CD
{GitHub Actions workflow name or "none"}
EOF
```

## Step 5: GitHub Actions (if no existing CI)

### Generate workflow for platform

```bash
mkdir -p {target}/.github/workflows

# Fly.io workflow
cat > {target}/.github/workflows/fly.yml << 'EOF'
name: Deploy to Fly.io
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - name: Deploy
        run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
EOF

# Generic Node.js deploy
cat > {target}/.github/workflows/node.yml << 'EOF'
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          # Replace with platform-specific deploy
          echo "Add deploy command here"
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
EOF
```

## Step 6: Secrets Setup

```bash
# Create secrets guide
cat > {target}/DEPLOY_SECRETS.md << 'EOF'
# Deploy Secrets Guide

## Required secrets

| Secret | Where to get it | Used by |
|--------|-----------------|---------|
| DEPLOY_TOKEN | {platform dashboard} | GitHub Actions |
| DATABASE_URL | Supabase/Neon/Railway | App runtime |
| JWT_SECRET | Generate: `openssl rand -base64 32` | App runtime |

## Setting secrets

GitHub:
```bash
gh secret set SECRET_NAME --repo owner/repo
```

Local (never commit these):
```bash
cp .env.example .env.local
# Edit .env.local with real values
```

## Rotating secrets

1. Generate new secret in platform
2. Update via `gh secret set` or platform dashboard
3. Trigger redeploy
4. Verify works
5. Remove old secret
EOF
```

## Step 7: Verify Setup

```bash
# Verify all files created
ls -la {target}/{fly.toml,render.yaml,vercel.json,netlify.toml,render.yaml,deploy.sh} 2>/dev/null

# Verify .env.example exists
cat {target}/.env.example

# Verify CLAUDE.md has deploy section
grep -A 20 "## Deployment" {target}/CLAUDE.md

# Test platform detection
echo "Platform: $PLATFORM"
```

## Setup Report

```
═══════════════════════════════════════════════════════
SETUP-DEPLOY REPORT — {target}
═══════════════════════════════════════════════════════

PLATFORM:          {detected or "none — manual setup needed"}
PROJECT TYPE:      {node|python|go|etc.}

CONFIG FILES:
  vercel.json:     {"created"|"exists"|"none"}
  Railway.toml:    {"created"|"exists"|"none"}
  fly.toml:        {"created"|"exists"|"none"}
  netlify.toml:    {"created"|"exists"|"none"}
  render.yaml:     {"created"|"exists"|"none"}
  GHA workflows:   {list}

DOCS:
  .env.example:    {"created"|"exists"}
  DEPLOY_SECRETS.md: {"created"|"exists"}
  CLAUDE.md deploy: {"appended"|"created"}

NEXT STEPS:
1. Set required secrets in GitHub/Actions
2. Test deploy locally (railway up / flyctl deploy / etc.)
3. Trigger first CI run

STATUS: READY TO DEPLOY | NEEDS MANUAL SETUP
```

## Platform Quick Reference

| Platform | Config file | Deploy command | Health check |
|----------|-------------|----------------|--------------|
| Vercel | vercel.json | npx vercel --prod | Automatic |
| Railway | Railway.toml | railway up | /health |
| Fly.io | fly.toml | flyctl deploy | port 8080 |
| Render | render.yaml | Auto from git | /health |
| Netlify | netlify.toml | Auto from git | / |
| GitHub Actions | .github/workflows/*.yml | Platform-specific | Manual |

## Important Rules

- **Detect before configuring.** If platform already has config, don't overwrite.
- **Never commit real secrets.** .env files are gitignored, .env.example is not.
- **CLAUDE.md deploy section is the source of truth.** Keep it updated.
- **Test the deploy locally.** `railway up`, `flyctl deploy`, `vercel deploy` all work without CI.
- **Secrets rotation is a procedure.** Document it — don't rely on memory.
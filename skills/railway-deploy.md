---
name: railway-deploy
description: >
  Railway CLI deployment — manages Railway projects including environment
  setup, service configuration, deployments, and rollback. Uses Railway MCP
  tools for full lifecycle management. Trigger when: deploying to Railway,
  configuring environment variables, rolling back a broken deployment, or
  troubleshooting Railway infrastructure. Key capability: Railway MCP tools
  for environment inspection, deployment management, and variable configuration.
  Also for: multi-service setup, domain configuration, and team access setup.
---

# /railway-deploy — Railway Deployment Pipeline

Deploy and manage Railway projects using Railway CLI and MCP tools.

## When to Activate

Trigger `/railway-deploy` when:
- Deploying to Railway
- Configuring environment variables
- Rolling back a broken deployment
- Troubleshooting Railway infrastructure
- Multi-service setup
- Team access configuration

## Preamble

```
/railway-deploy {target}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} ls-files Railway.toml railway.toml docker-compose.yml Dockerfile* 2>/dev/null

# Check Railway CLI
railway --version

# List current projects
railway list
```

## Railway MCP Tools

Railway has MCP tools available for project management. Use these when available:

| Tool | Purpose |
|------|---------|
| `railway_list_projects` | List all Railway projects |
| `railway_list_services` | List services in a project |
| `railway_list_variables` | Show environment variables |
| `railway_set_variables` | Set environment variables |
| `railway_deploy` | Trigger deployment |
| `railway_get_logs` | View deployment logs |
| `railway_generate_domain` | Generate public domain |
| `railway_link_environment` | Link to environment |
| `railway_link_service` | Link to service |
| `railway_create_environment` | Create new environment |
| `railway_create_project` | Create new Railway project |

## Step 1: Initial Setup

### Create or link project

```bash
# Check Railway status
railway status

# Link to existing project
railway init
# Or link to specific project
railway link {project-id}

# Login if needed
railway login
```

### Create new project

```bash
# Create via CLI
railway create {project-name}
# Then link
railway link {project-id}

# Or use MCP:
railway_create_project({projectName: "{project-name}", workspacePath: "{target}"})
```

## Step 2: Configure Service

### Set up Railway.toml

```toml
# Railway.toml
[build]
  builder = "nixpacks"
  # Or specify Dockerfile:
  # builder = "dockerfile"

[deploy]
  numReplicas = 1
  restartPolicyType = "OnFailure"
  restartPolicyMaxRetries = 10

# Health check (optional)
[healthcheck]
  path = "/health"
  port = 3000
```

### Or use Dockerfile

```dockerfile
# Dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["node", "dist/index.js"]
```

## Step 3: Environment Variables

### Set via CLI

```bash
# Set single variable
railway variables set NODE_ENV=production

# Set multiple
railway variables set DATABASE_URL=$DATABASE_URL API_KEY=$API_KEY

# Set for specific environment
railway variables --environment staging set DEBUG=true
```

### Set via MCP

```bash
# Set variables
railway_set_variables({
  workspacePath: "{target}",
  variables: ["NODE_ENV=production", "PORT=3000"]
})

# List variables (shows names, not values)
railway_list_variables({workspacePath: "{target}"})
```

### Variable scoping

```
ENVIRONMENT VARIABLE SCOPES
════════════════════════════════

Project-level:
  - Shared across all environments
  - Railway Dashboard → Project Settings → Variables

Environment-level:
  - staging, production, etc.
  - Railway Dashboard → Environment → Variables

Service-level:
  - Per-service overrides
  - Railway Dashboard → Service → Variables

Priority (highest first):
  1. Service variables
  2. Environment variables
  3. Project variables
```

### Common variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `NODE_ENV` | Environment | `production` |
| `PORT` | HTTP port Railway exposes | `3000` |
| `DATABASE_URL` | Database connection | `postgresql://...` |
| `RAILWAY_STATIC_URL` | Public URL (auto-set) | `https://xxx.up.railway.app` |

## Step 4: Deploy

### Via CLI

```bash
# Deploy current directory
railway up

# Deploy specific directory
railway up ./api-service

# Deploy to specific environment
railway up --environment production
```

### Via MCP

```bash
# Trigger deployment
railway_deploy({workspacePath: "{target}"})

# With specific environment
railway_link_environment({workspacePath: "{target}", environmentName: "production"})
railway_deploy({workspacePath: "{target}"})
```

### Wait for healthy

```bash
# Watch deployment
railway logs --follow

# Check deployment status
railway status

# Get domain
railway domain
```

## Step 5: Generate Domain

```bash
# Via CLI
railway domain

# Via MCP
railway_generate_domain({workspacePath: "{target}"})
# Returns the public URL

# Custom domain
railway domains add example.com
railway domains verify example.com
```

## Step 6: View Logs

```bash
# Recent logs
railway logs

# Follow logs in real time
railway logs --follow

# Filter logs
railway logs --filter "ERROR"

# Via MCP
railway_get_logs({
  workspacePath: "{target}",
  logType: "deploy",
  lines: 100,
  filter: "ERROR"
})
```

## Step 7: Rollback

### Via CLI

```bash
# List recent deployments
railway deployments list

# Rollback to previous deployment
railway rollback

# Rollback to specific deployment
railway rollback --deployment d{deployment-id}
```

### Rollback procedure

```
ROLLBACK PROCEDURE — Railway
════════════════════════════════

1. Identify broken deployment:
   railway deployments list

2. Rollback command:
   railway rollback --deployment d{N}

3. Verify health:
   curl -sf https://$(railway domain)/health

4. If still broken:
   railway rollback --deployment d{N-1}
```

## Step 8: Multi-Service Setup

### Monorepo structure

```toml
# Railway.toml (root)

[build]
  builder = "nixpacks"

# api service
[api]
  path = "./services/api"
  [api.healthcheck]
    path = "/health"
    port = 3000

# web service
[web]
  path = "./services/web"
  [web.healthcheck]
    path = "/"
    port = 8080
```

### Deploy specific service

```bash
railway up --service api
railway up --service web
```

## Step 9: Team Access

```bash
# Invite team member (via dashboard)
# Settings → Team → Invite by email

# Transfer ownership
# Settings → Team → Transfer Ownership

# Check team members
# Via Railway dashboard
```

## Step 10: CI/CD Integration

### GitHub Actions

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

      - name: Deploy
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway deploy

      - name: Health Check
        run: |
          sleep 10
          curl -sf ${{ vars.RAILWAY_URL }}/health || exit 1
```

### Get Railway token

```bash
# Via CLI
railway login
# Opens browser for OAuth

# Via dashboard:
# Project Settings → Deployments → New Token
```

## Troubleshooting

### Deployment failed

```bash
# View detailed logs
railway logs --json | jq '.message'

# Check build output
railway build output

# Common issues:
# - Build command failed: check Railway.toml build section
# - Missing env vars: railway variables list
# - Port mismatch: PORT env var vs Listen port
```

### Service not starting

```bash
# Check health check
railway variables list | grep -E "PORT|HEALTH"

# Verify PORT matches app.listen()
# Railway sets PORT env var — use it:
# const PORT = process.env.PORT || 3000

# Check logs for crashes
railway logs | grep -E "SIGKILL|SIGSEGV|exited"
```

### Environment variables not updating

```bash
# Redeploy after changing variables
railway up

# Force redeploy
railway up --service {service} --force
```

## Important Rules

- **PORT is set by Railway.** Don't hardcode — use `process.env.PORT`.
- **Health check is critical.** Railway uses it to determine when a deploy is ready.
- **Variables are scoped.** Make sure you're setting them in the right environment.
- **Rollback is instant.** Railway keeps previous deployments — rollback is a swap.
- **Idempotent deploys.** `railway up` should succeed even if already deployed.

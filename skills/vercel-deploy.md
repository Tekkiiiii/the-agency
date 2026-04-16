---
name: vercel-deploy
description: >
  Vercel deployment — sets up and manages Vercel CLI-based deployments,
  environment variables, preview/production promotion, health checks, and
  rollback. Trigger when: deploying to Vercel, configuring environment
  variables, promoting a preview to production, or rolling back a broken
  deploy. Key capability: complete workflow from first deploy to production
  with health verification. Also for: Vercel project reconfiguration,
  aliasing preview deploys, and domain setup.
---

# /vercel-deploy — Vercel Deployment Pipeline

Deploy, configure, and manage Vercel projects.

## When to Activate

Trigger `/vercel-deploy` when:
- First deploy to Vercel
- Configuring environment variables
- Promoting preview to production
- Rolling back a broken deploy
- Troubleshooting a Vercel deploy failure

## Preamble

Run at start:
```bash
git -C {target} log --oneline -1
git -C {target} remote -v
git -C {target} ls-files vercel.json .vercel 2>/dev/null
```

## Step 1: Initial Setup

### Option A: Import existing project

```bash
cd {target}
npx vercel login
npx vercel link
# Follow prompts to link to existing project
```

### Option B: Create new project

```bash
cd {target}
npx vercel login
npx vercel
# First deploy creates the project
```

### Verify linked project

```bash
npx vercel project ls
npx vercel teams
cat vercel.json 2>/dev/null || echo "No vercel.json found"
```

## Step 2: Environment Variables

### Set environment variables

```bash
# Production only
npx vercel env add NODE_ENV production
npx vercel env add DATABASE_URL

# Preview and production
npx vercel env add NEXT_PUBLIC_API_URL

# Pull from .env file
npx vercel env pull .env.local
```

### Environment variable types

| Type | Flag | Use |
|------|------|-----|
| Secret | (default) | Encrypted, hidden in UI |
| Plaintext | `--plain` | Public values |
| System | `--system` | Built-in (NODE_ENV, etc.) |

### List and manage

```bash
npx vercel env ls                    # List all env vars
npx vercel env get VAR_NAME          # View a secret
npx vercel env rm VAR_NAME          # Remove
npx vercel env pull                 # Pull to .env.local
```

### Secrets rotation

```bash
# 1. Add new secret value
npx vercel env add API_KEY production
# Paste new value

# 2. Redeploy with new secret
npx vercel deploy --prod

# 3. Verify works
curl -sf $(npx vercel domain confirm) > /dev/null && echo "OK"

# 4. Remove old secret (after verification)
npx vercel env rm OLD_API_KEY
```

## Step 3: Deploy

### Preview deploy

```bash
npx vercel                          # Preview URL
npx vercel --prod                   # Production
```

### Deploy with options

```bash
# Specific directory
npx vercel /path/to/project

# With build command override
npx vercel --build-command "npm run build:staging"

# With environment
npx vercel --environment preview
npx vercel --environment production

# Skip build
npx vercel --no-build
```

### Git-triggered deploys

```bash
# Connect GitHub repo via UI
# Or use Vercel GitHub integration:
npx vercel github connect
```

To configure in vercel.json:
```json
{
  "github": {
    "silent": true,
    "autoJobCancelation": true
  }
}
```

## Step 4: Health Check

```bash
# Get deployment URL
npx vercel ls

# Check health
URL=$(npx vercel ls --output json 2>/dev/null | jq -r '.deployments[0].url')
curl -sf "https://$URL/health" && echo "HEALTHY" || echo "UNHEALTHY"
curl -sf "https://$URL/api/health" && echo "API HEALTHY" || echo "API UNHEALTHY"

# Check logs
npx vercel logs "$URL"
```

### Add health endpoint

```typescript
// app/api/health/route.ts (Next.js)
export async function GET() {
  return Response.json({ status: 'ok', timestamp: Date.now() })
}
```

## Step 5: Preview → Production Promotion

### Option A: Instant promotion (if same build)

```bash
npx vercel alias $PREVIEW_URL production
```

### Option B: Promote via deploy

```bash
# Find the preview deployment
npx vercel ls | grep preview

# Promote specific deployment
npx vercel alias dXXXXXXXX.vercel.app production
```

### Option C: Atomic swap

```bash
# Production deploy gets a stable URL
npx vercel alias set d_NEW.vercel.app production

# Old production becomes a rollback target
# Rollback:
npx vercel alias set d_OLD.vercel.app production
```

## Step 6: Rollback

### Rollback to previous deployment

```bash
# List recent deployments
npx vercel ls

# Alias previous to production
npx vercel alias d_YYYYYYYY.vercel.app production
```

### Rollback via CLI

```bash
# Quick rollback to last known good
npx vercel rollback --environment production
```

### Rollback to specific Git ref

```bash
git checkout v1.2.3
npx vercel deploy --prod
git checkout main
```

## Step 7: Domain Configuration

### Add custom domain

```bash
npx vercel domains add example.com
npx vercel domains verify example.com
```

### Configure apex + www

```bash
# Add both
npx vercel domains add example.com
npx vercel domains add www.example.com

# Redirect www to apex via vercel.json
# Add to vercel.json:
{
  "redirects": [
    {
      "source": "/(.*)",
      "destination": "https://example.com/$1",
      "status": 307
    }
  ]
}
```

## Step 8: CI/CD Integration

### With GitHub Actions

```yaml
- name: Deploy to Vercel
  uses: amondnet/vercel-action@v25
  with:
    vercel-token: ${{ secrets.VERCEL_TOKEN }}
    vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
    vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
    vercel-args: '--prod'
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Get Vercel credentials

```bash
npx vercel token list
# Create new token:
npx vercel tokens create "GitHub Actions"
```

## Troubleshooting

### Deploy failed

```bash
# Get detailed build output
npx vercel deploy --debug

# Check build logs
npx vercel logs --follow
```

### Environment variable not found

```bash
# Verify it's set for correct scope
npx vercel env ls production

# Add to production
npx vercel env add VAR_NAME production --token $VERCEL_TOKEN
```

### Build too slow

```bash
# Use caching
# vercel.json:
{
  "buildCommand": "npm run build",
  "installCommand": "npm ci --prefer-offline"
}
```

### Build failed on Vercel but works locally

```bash
# Check Node.js version match
node --version
# Add engines to package.json:
{
  "engines": {
    "node": "20.x"
  }
}
```

## Important Rules

- **Always health check after deploy.** Don't assume success.
- **Promote, don't rebuild.** Use `vercel alias` to promote preview → production for speed and reliability.
- **Secrets are encrypted.** Don't put real values in vercel.json.
- **One project per repo.** Multi-repo → multi-project.
- **Rollback is aliasing.** Vercel rollback is instant because it's just DNS swap.

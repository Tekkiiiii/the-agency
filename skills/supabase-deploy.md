---
name: supabase-deploy
description: >
  Supabase CLI deployment — manages Supabase projects including migrations,
  edge functions, database management, and CI/CD integration. Trigger when:
  setting up Supabase from scratch, running database migrations, deploying
  edge functions, or configuring Supabase for a new environment. Key capability:
  migration dry-run to catch breaking changes before they reach production.
  Also for: local development with Supabase, production database management,
  and disaster recovery procedures.
---

# /supabase-deploy — Supabase CLI Deployment

Manage Supabase projects, migrations, edge functions, and CI/CD.

## When to Activate

Trigger `/supabase-deploy` when:
- Setting up Supabase from scratch
- Running database migrations
- Deploying edge functions
- Configuring new environment
- Local Supabase development
- Production database management

## Preamble

```
/supabase-deploy {target}
```

**Run at start:**
```bash
git -C {target} log --oneline -1
git -C {target} remote -v
git -C {target} ls-files supabase/ supabase/** 2>/dev/null
ls {target}/supabase/config.toml 2>/dev/null
```

## Step 1: Initial Setup

### Install Supabase CLI

```bash
# macOS
brew install supabase/tap/supabase

# Linux
npm install -g supabase

# Or download binary
curl -fsSL https://github.com/supabase/supabase/releases/latest/download/supabase-linux-amd64.tar.gz | tar xz
```

### Link to project

```bash
cd {target}
supabase login
supabase link --project-ref {project-ref}
# Get project-ref from: https://supabase.com/dashboard → Project Settings → API
```

### Initialize local config

```bash
supabase init
# Creates supabase/config.toml
# Creates supabase/migrations/ directory
```

## Step 2: Migrations

### Create a migration

```bash
supabase migration new {descriptive_name}
# Creates: supabase/migrations/{timestamp}_{descriptive_name}.sql
```

### Write migration

```sql
-- supabase/migrations/{timestamp}_{descriptive_name}.sql

-- Migration description
-- Author: {name}

-- Example: add users table
CREATE TABLE public.users (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users are viewable by everyone"
  ON public.users FOR SELECT
  USING (true);

CREATE POLICY "Users can update own profile"
  ON public.users FOR UPDATE
  USING (auth.uid() = id);

-- Indexes
CREATE INDEX idx_users_email ON public.users(email);
```

### Dry-run migration

```bash
# Preview what will run
supabase db push --dry-run
# Shows SQL that would execute without applying it
```

### Apply migration

```bash
# Local
supabase db reset  # Reset local DB and reapply all migrations

# Remote (staging/production)
supabase db push --project-id {project-id}
# Prompts for confirmation before applying

# Skip confirmation (CI)
supabase db push --project-id {project-id} --db-url ${DATABASE_URL}
```

### Migration safety rules

```
MIGRATION SAFETY CHECKLIST
════════════════════════════════

□ DROP TABLE requires existing table — verify
□ DROP COLUMN removes data — has backup been tested?
□ ALTER COLUMN type — will it truncate data?
□ Adding NOT NULL — existing rows handle it?
□ Renaming — all references updated?
□ Adding FK — existing data satisfies constraint?

Blocking migrations (require manual review):
□ DROP TABLE
□ DROP COLUMN
□ TRUNCATE
□ ALTER COLUMN TYPE on large table
□ Adding NOT NULL without DEFAULT
```

## Step 3: Edge Functions

### Create edge function

```bash
supabase functions new {function-name}
# Creates: supabase/functions/{function-name}/index.ts
```

### Write edge function

```typescript
// supabase/functions/{function-name}/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Auth
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'No authorization header' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: authHeader } } }
    )

    const { data: { user } } = await supabaseClient.auth.getUser()

    if (!user) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Business logic here
    const result = await doSomething(user.id)

    return new Response(
      JSON.stringify({ data: result }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
```

### Deploy edge function

```bash
# Deploy single function
supabase functions deploy {function-name}

# Deploy all functions
supabase functions deploy

# With secrets
supabase secrets set MY_SECRET=value --project-ref {project-ref}
```

### Edge function secrets

```bash
# Set per-project
supabase secrets set API_KEY=xxx --project-id {project-id}

# List secrets
supabase secrets list --project-id {project-id}

# Remove secret
supabase secrets unset OLD_KEY --project-id {project-id}
```

## Step 4: CI/CD Integration

### GitHub Actions workflow

```yaml
name: Supabase Deploy
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Supabase CLI
        run: npm install -g supabase

      - name: Apply migrations
        if: github.ref == 'refs/heads/main'
        env:
          SUPABASE_PASSWORD: ${{ secrets.SUPABASE_PASSWORD }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
        run: |
          supabase db push \
            --project-id ${{ vars.SUPABASE_PROJECT_ID }} \
            --db-url "postgresql://postgres:$SUPABASE_PASSWORD@db.${{ vars.SUPABASE_PROJECT_ID }}.supabase.co:5432/postgres"

  deploy-functions:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Install Supabase CLI
        run: npm install -g supabase

      - name: Deploy Edge Functions
        env:
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
        run: supabase functions deploy
```

## Step 5: Local Development

### Start local Supabase

```bash
supabase start
# Starts Docker containers for:
# - Postgres
# - Kong (API Gateway)
# - GoTrue (Auth)
# - PostgREST (API)
# - Storage
# - Realtime

# Output includes local URLs:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
```

### Link to local

```bash
supabase link --project-id localhost
# Or use local config
supabase status
```

### Apply migrations to local

```bash
supabase db push  # Applies pending migrations to local
supabase db reset # Full reset + migrations
```

### Stop local Supabase

```bash
supabase stop
# With reset
supabase stop --no-backup
```

## Step 6: Production Management

### Check project health

```bash
supabase projects api status --project-ref {project-ref}
# Shows: DB connected, API healthy, Auth healthy
```

### View database stats

```bash
# Via Supabase CLI
supabase db stats --project-id {project-id}

# Or direct connection
psql "$DATABASE_URL" -c "SELECT count(*) FROM pg_stat_activity;"
```

### Backup and restore

```bash
# Point-in-time recovery (via dashboard)
# Dashboard: Project Settings → Database → Point in Time Recovery

# Manual pg_dump
pg_dump "$DATABASE_URL" > backup.sql

# Restore
psql "$DATABASE_URL" < backup.sql
```

## Troubleshooting

### Migration fails

```bash
# Check migration status
supabase migration list --project-id {project-id}

# Check pending migrations
supabase db push --dry-run

# Check migration history
psql "$DATABASE_URL" -c "SELECT * FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 10;"
```

### Edge function not found

```bash
# Verify deployment
supabase functions list --project-id {project-id}

# Check logs
supabase functions logs {function-name} --project-id {project-id}

# Redeploy
supabase functions deploy {function-name} --no-verify-jwt
```

### Auth issues

```bash
# Verify anon key
curl -H "apikey: {ANON_KEY}" -H "Authorization: Bearer {TOKEN}" \
  {SUPABASE_URL}/rest/v1/users

# Check GoTrue logs
supabase admin query "SELECT * FROM vault.secrets WHERE name LIKE '%auth%';"
```

## Important Rules

- **Dry-run before every migration push.** Don't push to production without previewing.
- **Migrations are additive by default.** Prefer ADD COLUMN over ALTER COLUMN.
- **RLS is always on.** Every table needs explicit policies.
- **Edge functions run in Deno.** Don't expect Node.js APIs.
- **Environment parity.** Local, staging, and production should use the same migration files.

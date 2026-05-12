# Claimable Postgres

Instant ephemeral Postgres databases — no account required. Databases expire after 72 hours unless claimed to a Neon account.

## When to Apply

- Local development needing a real Postgres DB without Neon account
- Prototyping, demos, test environments
- Auto-provisioning on `vite dev` when `DATABASE_URL` is missing
- Any task that needs a database and the user hasn't provided one

## Quick Start

```bash
curl -s -X POST "https://neon.new/api/v1/database" \
  -H "Content-Type: application/json" \
  -d '{"ref": "agent-skills"}'
```

Parse `connection_string` and `claim_url` from the JSON. Write `connection_string` to `.env` as `DATABASE_URL`.

## Methods Comparison

| Method | Best For |
|--------|----------|
| REST API | Agents needing structured JSON output |
| CLI (`px neon-new@latest --yes`) | One-step setup, writes `.env` automatically |
| SDK (`neon-new`) | Programmatic provisioning in scripts |
| Vite plugin | Auto-provision on `vite dev` |

## REST API

**Base URL:** `https://neon.new/api/v1`

**Create:**
```bash
curl -s -X POST "https://neon.new/api/v1/database" \
  -H "Content-Type: application/json" \
  -d '{"ref": "agent-skills"}'
```

**Response:**
```json
{
  "id": "019beb39-...",
  "status": "UNCLAIMED",
  "connection_string": "postgresql://...",
  "claim_url": "https://neon.new/claim/019beb39-...",
  "expires_at": "2026-01-26T14:19:14.580Z"
}
```

The `connection_string` is **pooled**. For direct connections (e.g. Prisma migrations), remove `-pooler` from the hostname.

**Check status:**
```bash
curl -s "https://neon.new/api/v1/database/{id}"
```

**Errors:**
| Condition | HTTP | Message |
|-----------|------|---------|
| Missing `ref` | 400 | Missing referrer |
| Invalid ID | 400 | Database not found |
| Invalid JSON | 500 | Failed to create the database |

## CLI

```bash
npx neon-new@latest --yes --ref agent-skills
```

Always use `@latest` and `--yes` (skips prompts that stall agents).

**Options:**
| Option | Alias | Description | Default |
|--------|-------|-------------|---------|
| `--yes` | `-y` | Skip prompts | false |
| `--env` | `-e` | `.env` file path | `./.env` |
| `--key` | `-k` | Env var key | `DATABASE_URL` |
| `--seed` | `-s` | Path to seed SQL | none |
| `--logical-replication` | `-L` | Enable logical replication | false |

CLI writes both `DATABASE_URL` (pooled) and `DATABASE_URL_DIRECT` (for migrations).

## SDK

```ts
import { instantPostgres } from 'neon-new';

const { databaseUrl, databaseUrlDirect, claimUrl, claimExpiresAt } = await instantPostgres({
  referrer: 'agent-skills',
  seed: { type: 'sql-script', path: './init.sql' },
});
```

## Vite Plugin

For Vite projects: `npm install -D vite-plugin-neon-new`
Auto-provisions on `vite dev` if `DATABASE_URL` is missing.

## Agent Workflow

**API path:**
1. Confirm intent if ambiguous (user may want a permanent DB)
2. `POST https://neon.new/api/v1/database` with `{"ref": "agent-skills"}`
3. Parse `connection_string`, `claim_url`, `expires_at`
4. Check existing `.env` — do NOT overwrite existing `DATABASE_URL`
5. Write `DATABASE_URL=<connection_string>` to `.env`
6. Run seed SQL if applicable: `psql "$DATABASE_URL" -f seed.sql`
7. Report: where written, which key, claim URL, expiry

**CLI path:**
1. Check `.env` for existing key — skip if present
2. Confirm intent if ambiguous
3. Run: `npx neon-new@latest --yes --ref agent-skills --env .env.local`
4. Verify `.env` was written
5. Report same as API path

## Claiming

Optional. Database works immediately without claiming.

- **API/SDK:** Give user the `claim_url`
- **CLI:** `npx neon-new@latest claim` reads URL from `.env` and opens browser

**⚠️ Users cannot claim into Vercel-linked orgs** — must choose another Neon org.

## Limits

| | Unclaimed | Claimed (Free) |
|-|-----------|----------------|
| Storage | 100 MB | 512 MB |
| Transfer | 1 GB | ~5 GB |
| Branches | No | Yes |
| Expiration | 72 hours | None |

Region: `us-east-2` (cannot change). Postgres 17.

## Safety Rules

- **Do NOT overwrite existing env vars.** Check first.
- Ask before running destructive seed SQL (DROP, TRUNCATE, mass DELETE).
- For production: recommend standard Neon provisioning, not temporary databases.
- After writing credentials, check `.gitignore` covers the `.env` file. Warn if not.

---

**Source:** https://officialskills.sh/neondatabase/skills/claimable-postgres
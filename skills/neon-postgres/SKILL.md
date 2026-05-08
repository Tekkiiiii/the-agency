# Neon Postgres

Serverless Postgres with autoscaling, branching, instant restore, and scale-to-zero.

## When to Apply

- Setting up Neon projects, branches, or connection strings
- Using `@neondatabase/serverless`, WebSocket, or HTTP transports
- Implementing branching for preview environments or CI
- Configuring connection pooling for serverless workloads
- Read replicas, autoscaling, or point-in-time restore

## Key Concepts

- **Organizations → Projects → Branches → Endpoints**
- Branches are copy-on-write clones (instant, no full data copy)
- Each branch has its own compute endpoint
- Storage is independent from compute (scale-to-zero works)

## Docs Fetching

Neon docs can be fetched as markdown:

```
https://neon.com/docs/introduction/branching.md
curl -H "Accept: text/markdown" https://neon.com/docs/introduction/branching
```

Find any page: search https://neon.com/docs/llms.txt

## Connection Methods

| Transport | Use Case |
|-----------|----------|
| TCP (libpq) | Long-running processes, standard Postgres clients |
| HTTP (serverless) | Edge, Vercel, Cloudflare Workers, AWS Lambda |
| WebSocket | Transactions in serverless environments |
| Pooled (`-pooler`) | High-concurrency serverless (PgBouncer) |

**Pooled connection:** append `-pooler` to endpoint hostname.

## @neondatabase/serverless

```ts
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL!);

// HTTP query (auto-rewrites transactions)
const result = await sql`SELECT * FROM users WHERE id = ${userId}`;
```

## Branching

**Create:**
```bash
neonctl branches create --name feature-123
# or via MCP server / Admin API
```

**Key points:**
- Instant (copy-on-write)
- Can branch from any point in time (PITR)
- Endpoints per branch
- Compare schemas between branches

## Autoscaling

- Compute scales automatically with workload
- CU (Compute Unit) sizing determines scale range
- Scale-to-zero suspends after 5min idle (configurable)
- Cold start: ~hundreds of ms after suspend

## Connection Pooling

```ts
// Use pooled connection for serverless
const pooledUrl = endpointHost + "-pooler" + remainingUrl;
```
Essential for bursty concurrency in serverless runtimes.

## Auth

Neon Auth: managed user auth + UI components.
Neon JS SDK embeds auth: combined Auth + Data API with PostgREST-style querying.

## Admin API / CLI

```bash
npx neonctl@latest init
neonctl branches list
neonctl branches create --name my-branch
```

MCP server available for AI tool integration: `neonctl mcp --cursor`

## Reference Links

| Topic | Link |
|-------|------|
| What is Neon | https://neon.com/docs/ai/skills/neon-postgres/references/what-is-neon.md |
| Getting Started | https://neon.com/docs/ai/skills/neon-postgres/references/getting-started.md |
| Connection Methods | https://neon.com/docs/ai/skills/neon-postgres/references/connection-methods.md |
| Serverless Driver | https://neon.com/docs/ai/skills/neon-postgres/references/neon-serverless.md |
| Neon JS SDK | https://neon.com/docs/ai/skills/neon-postgres/references/neon-js.md |
| CLI / DevTools | https://neon.com/docs/ai/skills/neon-postgres/references/neon-cli.md |
| Branching | https://neon.com/docs/ai/skills/neon-postgres/references/branching.md |
| Connection Pooling | https://neon.com/docs/introduction/connection-pooling.md |
| Autoscaling | https://neon.com/docs/introduction/autoscaling.md |
| Scale to Zero | https://neon.com/docs/introduction/scale-to-zero.md |
| Read Replicas | https://neon.com/docs/introduction/read-replicas.md |
| Instant Restore | https://neon.com/docs/introduction/branch-restore.md |

---

**Source:** https://officialskills.sh/neondatabase/skills/neon-postgres
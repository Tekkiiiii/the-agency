# Better Auth — Best Practices

Guidance for Better Auth server and client setup, database adapter configuration, session management, plugin integration, and environment variable handling.

## When to Apply

- Setting up a Better Auth server with Drizzle or Prisma adapter
- Adding OAuth providers like Google alongside email/password login
- Configuring session storage with Redis as secondary storage
- Wiring in plugins like twoFactor or magicLink with correct import paths
- Mapping ORM model names to database tables without breaking migrations

## Quick Reference

**Always consult better-auth.com/docs for code examples and latest API.**

## Setup Workflow

1. Install: `npm install better-auth`
2. Set env vars: `BETTER_AUTH_SECRET` and `BETTER_AUTH_URL`
3. Create `auth.ts` with database + config
4. Create route handler for your framework
5. Run `npx @better-auth/cli@latest migrate`
6. Verify: call `GET /api/auth/ok` — should return `{ status: "ok" }`

## Environment Variables

- `BETTER_AUTH_SECRET` — Encryption secret (min 32 chars). Generate: `openssl rand -base64 32`
- `BETTER_AUTH_URL` — Base URL (e.g., `https://example.com`)

Only define `baseURL`/`secret` in config if env vars are NOT set.

## CLI Commands

- `npx @better-auth/cli@latest migrate` — Apply schema (built-in adapter)
- `npx @better-auth/cli@latest generate` — Generate schema for Prisma/Drizzle
- `npx @better-auth/cli mcp --cursor` — Add MCP to AI tools

**Re-run after adding/changing plugins.**

## Core Config Options

| Option | Notes |
|--------|-------|
| `appName` | Optional display name |
| `baseURL` | Only if `BETTER_AUTH_URL` not set |
| `basePath` | Default `/api/auth`. Set `/` for root. |
| `secret` | Only if `BETTER_AUTH_SECRET` not set |
| `database` | Required for most features. See adapters docs. |
| `secondaryStorage` | Redis/KV for sessions & rate limits |
| `emailAndPassword` | `{ enabled: true }` to activate |
| `socialProviders` | `{ google: { clientId, clientSecret }, ... }` |
| `plugins` | Array of plugins |
| `trustedOrigins` | CSRF whitelist |

## Database

**Direct connections:** Pass `pg.Pool`, `mysql2` pool, `better-sqlite3`, or `bun:sqlite` instance.

**ORM adapters:** Import from `better-auth/adapters/drizzle`, `better-auth/adapters/prisma`, `better-auth/adapters/mongodb`.

**Critical:** Better Auth uses adapter model names, NOT underlying table names. If Prisma model is `User` mapping to table `users`, use `modelName: "user"` (Prisma reference), not `"users"`.

## Session Management

**Storage priority:**
- If `secondaryStorage` defined → sessions go there (not DB)
- Set `session.storeSessionInDatabase: true` to also persist to DB
- No database + `cookieCache` → fully stateless mode

**Cookie cache strategies:**
- `compact` (default) — Base64url + HMAC. Smallest.
- `jwt` — Standard JWT. Readable but signed.
- `jwe` — Encrypted. Maximum security.

**Key options:** `session.expiresIn` (default 7 days), `session.updateAge` (refresh interval), `session.cookieCache.maxAge`, `session.cookieCache.version` (change to invalidate all sessions).

## User & Account Config

**User:** `user.modelName`, `user.fields` (column mapping), `user.additionalFields`, `user.changeEmail.enabled` (disabled by default), `user.deleteUser.enabled` (disabled by default).

**Account:** `account.modelName`, `account.accountLinking.enabled`, `account.storeAccountCookie` (for stateless OAuth).

**Required for registration:** `email` and `name` fields.

## Email Flows

- `emailVerification.sendVerificationEmail` — Must be defined for verification to work
- `emailVerification.sendOnSignUp` / `sendOnSignIn` — Auto-send triggers
- `emailAndPassword.sendResetPassword` — Password reset email handler

## Security

In `advanced`:
- `useSecureCookies` — Force HTTPS cookies
- `disableCSRFCheck` — ⚠️ Security risk
- `disableOriginCheck` — ⚠️ Security risk
- `crossSubDomainCookies.enabled` — Share cookies across subdomains
- `ipAddress.ipAddressHeaders` — Custom IP headers for proxies
- `database.generateId` — Custom ID generation or `"serial"` / `"uuid"` / `false`

**Rate limiting:** `rateLimit.enabled`, `rateLimit.window`, `rateLimit.max`, `rateLimit.storage` (`"memory"` | `"database"` | `"secondary-storage"`).

## Hooks

**Endpoint hooks:** `hooks.before` / `hooks.after` — Array of `{ matcher, handler }`. Use `createAuthMiddleware`. Access `ctx.path`, `ctx.context.returned` (after), `ctx.context.session`.

**Database hooks:** `databaseHooks.user.create.before/after`, same for `session`, `account`. Useful for adding default values or post-creation actions.

**Hook context (`ctx.context`):** `session`, `secret`, `authCookies`, `password.hash()/verify()`, `adapter`, `internalAdapter`, `generateId()`, `tables`, `baseURL`.

## Plugins

**Import from dedicated paths for tree-shaking:**

```ts
import { twoFactor } from "better-auth/plugins/two-factor"
```

NOT from `"better-auth/plugins"`.

**Popular plugins:** `twoFactor`, `organization`, `passkey`, `magicLink`, `emailOtp`, `username`, `phoneNumber`, `admin`, `apiKey`, `bearer`, `jwt`, `multiSession`, `sso`, `oauthProvider`, `oidcProvider`, `openAPI`, `genericOAuth`.

Client plugins go in `createAuthClient({ plugins: [...] })`.

## Client

Import from: `better-auth/client` (vanilla), `better-auth/react`, `better-auth/vue`, `better-auth/svelte`, `better-auth/solid`.

**Key methods:** `signUp.email()`, `signIn.email()`, `signIn.social()`, `signOut()`, `useSession()`, `getSession()`, `revokeSession()`, `revokeSessions()`.

## Type Safety

Infer types: `typeof auth.$Infer.Session`, `typeof auth.$Infer.Session.user`.

For separate client/server projects: `createAuthClient<typeof auth>()`.

## Common Gotchas

- **Model vs table name** — Config uses ORM model name, not DB table name
- **Plugin schema** — Re-run CLI after adding plugins
- **Secondary storage** — Sessions go there by default, not DB
- **Cookie cache** — Custom session fields NOT cached, always re-fetched
- **Stateless mode** — No DB = session in cookie only, logout on cache expiry
- **Change email flow** — Sends to current email first, then new email

---

**Source:** https://officialskills.sh/better-auth/skills/best-practices
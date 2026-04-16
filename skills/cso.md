---
name: cso
description: >
  Chief Security Officer audit — full security review of an architecture or
  implementation. Covers OWASP Top 10, STRIDE threat model, secrets management,
  dependency vulnerabilities, auth/implementations, network exposure, and
  compliance. 15-phase pipeline produces a finding-per-finding report with
  severity, evidence, impact, and remediation. Trigger when: security audit,
  pre-launch checklist, new infrastructure, compliance review, or after a
  breach. Key capability: structured threat modeling that finds what scanners
  miss — business logic flaws, auth edge cases, data flow exposure. Also for:
  pen-test prep, SOC2 readiness, and security regression testing. Not for:
  interactive fixing (use /fix-security for that).
---

# /cso — Chief Security Officer Audit

Full-spectrum security review. Finds what scanners miss.

## When to Activate

Trigger `/cso` when:
- "Security audit" or "security review"
- Pre-launch checklist
- New infrastructure or service
- Compliance review (SOC2, ISO 27001)
- After a breach or incident
- Penetration test preparation

## Important Preamble

This skill uses the **gstack prependamble** system. Run it exactly as shown:

```
/cso {target}

────────────────────────────────────────
PREAMPBLE CHECK — CSO AUDIT
────────────────────────────────────────
1. Run:    git -C {target} log --oneline -1
2. Update: Check ~/.claude/gstack/update.json
           Compare {target} against last-audit SHA
           If current SHA matches last-audit SHA → SKIP audit (nothing new)
3. Repo mode detection:
           git -C {target} rev-parse --is-inside-work-tree 2>/dev/null
           git -C {target} ls-files 2>/dev/null | head -5
           git -C {target} remote -v 2>/dev/null
           git -C {target} log --oneline -3 2>/dev/null
           Detect: monorepo | multi-repo | single | unknown
4. Audit scope:  {target}/
           Monorepo subpackages: {list}
5. Last audit:   {SHA or "none"}
   This audit:   {current SHA}
────────────────────────────────────────
```

**Skip condition:** If the current SHA matches the last-audit SHA from `update.json`, output:
```
SKIPPED — no new commits since last audit
Last audit SHA: {SHA}
Current SHA:    {current SHA}
```
Then stop. Do not repeat an unchanged audit.

## Audit Pipeline (15 Phases)

### Phase 1: Scope & Threat Model

```
CSO AUDIT — {target}
═══════════════════════════════════

PHASE 1: SCOPE & THREAT MODEL
Target:   {target}
Auditor:  CSO
Date:     {date}

THREAT MODEL: STRIDE
┌─────────────┬──────────────┐
│ Threat      │ What it means│
├─────────────┼──────────────┤
│ Spoofing    │ Impersonate  │
│ Tampering   │ Alter data   │
│ Repudiation │ Deny action  │
│ Info Discl. │ Data leak    │
│ DoS        │ Availability │
│ Priv. Esc.  │ Gain access  │
└─────────────┴──────────────┘

IN SCOPE:
- Application layer
- API surface
- Authentication & authorization
- Data storage & transit
- Secrets management
- Dependency供应链
- Network exposure
- Session management
- Input validation
- Error handling
- Logging & monitoring
```

### Phase 2: Reconnaissance

```bash
# Discover the attack surface
git -C {target} ls-files | grep -E '\.(js|ts|py|go|rb|java|rs|tsx|jsx)$'
git -C {target} ls-files | grep -E '\.(yaml|yml|toml|json|env|tf|hcl)$'
git -C {target} ls-files | grep -E '(Dockerfile|docker-compose|\.dockerignore)'
git -C {target} ls-files | grep -E '\.(md|txt|rst)$' | grep -iE '(README|SECURITY|CONTRIBUTING|INSTALL)'
find {target} -name "*.tf" -o -name "*.hcl" 2>/dev/null | head -20

# Check for exposed secrets history
git -C {target} log --all --full-history --source --pattern 'PASSWORD\|SECRET\|API_KEY\|TOKEN' --oneline 2>/dev/null | head -10

# Network-facing services
grep -rE '(listen|bind|host|server|port|:3000|:8080|:8000|http\.listen|express\.listen|flask|fastapi)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | head -20
```

### Phase 3: Secrets Management

```
PHASE 3: SECRETS MANAGEMENT

CHECKLIST:
┌───────────────────────────────────────┬───────────┐
│ Item                                  │ Status    │
├───────────────────────────────────────┼───────────┤
│ No hardcoded secrets in source        │ □ PASS    │
│                                        │ □ FAIL    │
│                                        │ □ N/A     │
│ .env files in .gitignore              │ □ PASS    │
│                                        │ □ FAIL    │
│                                        │ □ N/A     │
│ Secrets via env vars or secret manager│ □ PASS    │
│                                        │ □ FAIL    │
│                                        │ □ N/A     │
│ No commit history of secrets          │ □ PASS    │
│                                        │ □ FAIL    │
│                                        │ □ N/A     │
│ Rotated secrets after repo exposure   │ □ PASS    │
│                                        │ □ FAIL    │
│                                        │ □ N/A     │
└───────────────────────────────────────┴───────────┘
```

**If PASS:** Evidence: `{command showing no hardcoded secrets}`

**If FAIL:** File: `{path}`, Line: `{N}`, Secret: `{type}`, Remediation: `{fix}`

### Phase 4: Authentication & Authorization

```bash
# Find auth implementations
grep -rE '(password|bcrypt|hash|jwt|session|cookie|auth|login|signin|token)' {target}/ --include='*.ts' --include='*.js' --include='*.py' --include='*.go' 2>/dev/null | grep -v node_modules | grep -v test | head -30

# Check auth middleware
find {target} -name "middleware*" -o -name "auth*" 2>/dev/null | grep -v node_modules | head -10

# Check for auth in routes
grep -rE '(router\.(get|post|put|delete|patch)|@router\.|route\(|defineRoute)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | grep -v test | head -20
```

**Findings to capture:**
- Auth mechanism: `{mechanism}`
- Session handling: `{how}`
- Where auth is enforced (middleware, route-level, etc.)
- Where auth is missing but should exist

### Phase 5: Input Validation & Injection

```
PHASE 5: INPUT VALIDATION & INJECTION

OWASP A03:2021 Coverage:

┌─────────────────────────────────────┬───────────┐
│ Vector                               │ Status    │
├───────────────────────────────────────┼───────────┤
│ SQL injection (parameterized queries)│ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ NoSQL injection (sanitized input)   │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ XSS (output encoding)               │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Command injection (no shell exec)   │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Path traversal (path validation)   │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ SSRF (URL validation)               │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
└─────────────────────────────────────┴───────────┘
```

### Phase 6: Dependency Audit

```bash
# Check for known vulnerabilities
# package-lock.json / yarn.lock / package.json
grep -E '"(lodash|axios|request|node-fetch|express|jsonwebtoken|jose)"' {target}/package*.json 2>/dev/null

# Pipfile / requirements.txt / pyproject.toml
grep -E '(requests|urllib|jinja|flask|django|sqlalchemy)' {target}/requirements*.txt {target}/Pipfile {target}/pyproject.toml 2>/dev/null

# Cargo.toml / go.mod / go.sum
grep -E '(reqwest|hyper|http|yaml)' {target}/Cargo.toml {target}/go.mod 2>/dev/null

# Check for outdated packages with known CVEs
# Run npm audit if available
(cd {target} && npm audit --production 2>/dev/null || echo "npm audit not available")

# Check for dev-only deps in production image
grep -E '(devDependencies|dev_deps)' {target}/package.json 2>/dev/null
```

**Severity matrix:**
- Critical (CVSS 9-10): Immediate fix required
- High (CVSS 7-9): Fix before launch
- Medium (CVSS 4-6): Fix within 30 days
- Low (CVSS 0-3): Track and fix

### Phase 7: Data Protection

```
PHASE 7: DATA PROTECTION

┌─────────────────────────────────────┬───────────┐
│ Control                              │ Status    │
├───────────────────────────────────────┼───────────┤
│ Data encrypted at rest (DB)          │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Data encrypted in transit (TLS)    │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ PII fields encrypted or masked      │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ No sensitive data in logs           │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Backup encryption                   │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Data retention policy defined      │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
└─────────────────────────────────────┴───────────┘
```

### Phase 8: Session Management

**Checklist:**
- Session token entropy: `{bits}` (need 128+)
- Session cookie flags: `HttpOnly`, `Secure`, `SameSite`
- Session timeout: `{minutes}` (15 max for sensitive apps)
- Concurrent session limit: `{limit or none}`
- Session revocation on logout: `{enforced or not}`
- Session fixation protection: `{enforced or not}`

### Phase 9: Error Handling & Information Disclosure

```bash
# Check for stack traces in production
grep -rE '(stack|trace|error\.stack|err\.stack|printStackTrace)' {target}/ --include='*.ts' --include='*.js' --include='*.py' --include='*.go' 2>/dev/null | grep -v node_modules | grep -v test | head -10

# Check for verbose error responses
grep -rE '(throw new Error|raise|return.*error|res\.error|res\.status.*500)' {target}/ --include='*.ts' --include='*.js' --include='*.py' --include='*.go' 2>/dev/null | grep -v node_modules | grep -v test | head -15

# Check .gitignore includes error logs
grep -rE '\.log|\.err|error.log' {target}/.gitignore 2>/dev/null
```

### Phase 10: Logging & Monitoring

```
PHASE 10: LOGGING & MONITORING

┌─────────────────────────────────────┬───────────┐
│ Capability                           │ Status    │
├───────────────────────────────────────┼───────────┤
│ Auth events logged (login/logout)    │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Sensitive ops logged (data access) │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Errors logged with context          │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ No sensitive data in logs          │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Log integrity protected (tamper evid)│ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ SIEM or central log ingestion       │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Alert on anomaly (failed auth burst)│ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
└─────────────────────────────────────┴───────────┘
```

### Phase 11: CSRF & CORS

```bash
# CSRF protection
grep -rE '(csrf|csrf-token|xsrf|double-submit)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | grep -v test | head -10

# CORS configuration
grep -rE '(cors|Access-Control-Allow-Origin|allow-origin|CORS' {target}/ --include='*.ts' --include='*.js' --include='*.py' --include='*.yaml' --include='*.yml' 2>/dev/null | grep -v node_modules | head -10
```

**Findings:**
- CSRF tokens: `{present or absent}`
- CORS origin whitelist: `{list or wildcard}`
- Wildcard CORS risk: `{LOW|MEDIUM|HIGH|CRITICAL}`

### Phase 12: File Upload & Storage

```bash
# File upload handling
grep -rE '(upload|multer|multipart|file\.upload|storage|bucket|s3|gs|gcs)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | head -15

# Check for presigned URL usage vs public bucket
grep -rE '(public-read|public:true|acl:|presigned|private)' {target}/ --include='*.ts' --include='*.js' --include='*.py' --include='*.yaml' 2>/dev/null | grep -v node_modules | head -10
```

### Phase 13: API Security

```bash
# Rate limiting
grep -rE '(rateLimit|rate_limit|throttle|limit.*request|max.*request|express-rate-limit)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | head -10

# API versioning
grep -rE '(v1|v2|v3|/api/|/api/v)' {target}/ --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | grep -v node_modules | grep -v test | head -10

# GraphQL-specific checks
grep -rE '(graphql|GraphQL|schema|query|mutation|subscription)' {target}/ --include='*.ts' --include='*.js' 2>/dev/null | grep -v node_modules | head -10
```

### Phase 14: Infrastructure Security

```bash
# Check container security
grep -E '(FROM|RUN|sudo|root|USER|WORKDIR|COPY|ADD)' {target}/Dockerfile* 2>/dev/null

# Check for network exposure
grep -rE '(0\.0\.0\.0|:80|:443|INADDR_ANY|network.*host|--network)' {target}/docker-compose*.yml {target}/Dockerfile* {target}/*.yaml {target}/*.yml 2>/dev/null | head -10

# Cloud provider config
find {target} -name "*.tf" -o -name "*.hcl" -o -name "*.tfvars" 2>/dev/null | head -10
grep -rE '(public.*subnet|security.*group|ingress.*0\.0\.0\.0|port.*0\.|allow.*all)' {target}/ --include='*.tf' --include='*.hcl' 2>/dev/null | head -10
```

### Phase 15: Compliance Mapping

```
PHASE 15: COMPLIANCE MAPPING

┌─────────────────────────────────────┬───────────┐
│ Control family                      │ Status    │
├───────────────────────────────────────┼───────────┤
│ IDAM (identity & access mgmt)       │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Cryptography (encryption in transit)│ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Vulnerability management            │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Incident response                  │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Logging & monitoring               │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Supply chain (dependency audit)    │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
│ Data protection                    │ □ ✓       │
│                                      │ □ ✗       │
│                                      │ □ N/A     │
└─────────────────────────────────────┴───────────┘

COMPLIANCE FRAMEWORKS:
- SOC 2: {coverage}%
- OWASP Top 10: {coverage}%
- STRIDE: {coverage}%
```

## Findings Report

```
═══════════════════════════════════════════════════════
CSO AUDIT FINDINGS — {target}
═══════════════════════════════════════════════════════

SUMMARY:
Critical: {N}  High: {N}  Medium: {N}  Low: {N}  Info: {N}

---
FINDING {N}: {title}
Severity:  CRITICAL | HIGH | MEDIUM | LOW | INFO
 OWASP:     {reference}
 STRIDE:    {threat type}
 Location:  {file}:{line}
 Evidence:  {what was found}
 Impact:    {what an attacker gains}
 Remediation: {specific fix}
 Status:    OPEN | IN PROGRESS | RESOLVED
```

## Remediation Roadmap

```
REMEDIATION PRIORITY:

P0 — BEFORE LAUNCH:
1. {critical finding 1}
2. {critical finding 2}

P1 — WITHIN 1 WEEK:
1. {high finding 1}
2. {high finding 2}

P2 — WITHIN 30 DAYS:
1. {medium finding 1}

P3 — NEXT QUARTER:
1. {low finding 1}
```

## Important Rules

- **Phase order matters.** Don't skip phases because a system "looks fine."
- **STRIDE every surface.** Apply the full threat model, not just OWASP.
- **Severity is evidence-based.** Don't soften findings to avoid conflict.
- **No false confidence.** A clean Phase 6 (deps) doesn't mean the app is secure.
- **Remediation must be specific.** "Fix auth" is not a finding — "JWTalg set to 'none' in line 42 of auth.ts" is.

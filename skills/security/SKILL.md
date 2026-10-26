---
name: security
description: "Use when code or design touches auth, API keys, secrets, encryption, user input, payments or network requests, or on \"is this secure?\", OWASP, SQL injection, XSS, CSRF, security review. Checks OWASP Top 10, secrets, JWT/session, IDOR, CORS, dependency CVEs, PII; reports by severity with fixes."
---

# Security Skill

## When reviewing code or architecture, always check:

### Secrets & Credentials
- No hardcoded API keys, passwords, or tokens in source code
- Secrets loaded from environment variables or secret managers (Vault, AWS Secrets Manager, etc.)
- `.env` files in `.gitignore`

### Authentication & Authorization
- Verify JWT/session token validation on every protected route
- Check for broken object-level authorization (BOLA/IDOR)
- Enforce least-privilege principles
- MFA recommended for sensitive operations

### Input Validation
- Sanitize and validate all user inputs server-side
- Parameterized queries / ORM to prevent SQL injection
- Encode outputs to prevent XSS
- CSRF tokens on state-changing requests

### API Security
- Rate limiting on all public endpoints
- CORS configured restrictively
- HTTPS enforced everywhere
- Sensitive data not exposed in URLs or logs

### Dependency Security
- Flag outdated or CVE-listed packages
- Recommend `npm audit`, `pip-audit`, `snyk`, or equivalent

### Data Protection
- PII encrypted at rest and in transit
- Minimal data collection principle
- Proper error messages (no stack traces to users)

## Output Format
Always provide:
1. **Findings** — list of issues by severity (Critical / High / Medium / Low)
2. **Recommended Fix** — concrete code or config change for each finding
3. **Quick Wins** — top 3 things to fix immediately
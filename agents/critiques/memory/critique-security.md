# critique-security — Critic Memory

Append-only lesson log. Read at the start of every critique session. Never delete or rewrite entries.
Each entry captures one lesson: what worked, what was a blind spot, what wasted rounds.

Format:
## YYYY-MM-DD — brief title
3-8 lines of specific insight from that run.

---

## 2026-06-10 — Scoped diff review: webhook, RBAC, compositing

- Scoped diff reviews are faster and more useful than full codebase audits when the request names specific concerns. Follow the scope exactly.
- Fail-close webhook pattern: the old `if (secret && ...)` guard is a classic fail-open bug. The fix (check `!secret` first, return 503) is the right pattern. JS `!==` comparison is fine for long-lived secrets — no timing attack risk at this scale.
- When a diff adds a `company_id` filter to one function in a family of similar functions, check the siblings. `submitForApproval` got the fix; `updateSubmitterNote` and `resubmitWorkItem` did not. Variant-analysis on isolation fixes is high-yield.
- RLS WITH CHECK that derives company_id from a subquery (`SELECT company_id FROM work_items WHERE id = work_item_id`) is a solid pattern — cross-company bypass would require the RLS subquery to return the wrong row, which would be a Postgres or Supabase bug, not an app bug.
- `console.error` logging raw Error objects from native modules (sharp) can leak internal file paths to log aggregators — flag as LOW but worth noting.
- Synchronous compositing behind `requireAuth` with per-variant try/catch is not a DoS vector. The auth gate is the key check.

# Stripe Best Practices

**Latest Stripe API version: 2026-02-25.clover.** Always use the latest API version and SDK unless the user specifies otherwise.

## Integration Routing

| Use Case | Recommended API | Reference |
|---|---|---|
| One-time payments | Checkout Sessions | references/payments.md |
| Custom payment form with embedded UI | Checkout Sessions + Payment Element | references/payments.md |
| Saving a payment method for later | Setup Intents | references/payments.md |
| Connect platform or marketplace | Accounts v2 (/v2/core/accounts) | references/connect.md |
| Subscriptions or recurring billing | Billing APIs + Checkout Sessions | references/billing.md |
| Embedded financial accounts / banking | v2 Financial Accounts | references/treasury.md |

Read the relevant reference file before answering any integration question or writing code.

## Key Documentation

- **Integration Options** — Start here when designing any integration.
- **API Tour** — Overview of Stripe's API surface.
- **Go Live Checklist** — Review before launching.

---

**Source:** https://officialskills.sh/stripe/skills/stripe-best-practices

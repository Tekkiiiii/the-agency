# critique-brand — Critic Memory

Append-only lesson log. Read at the start of every critique session. Never delete or rewrite entries.
Each entry captures one lesson: what worked, what was a blind spot, what wasted rounds.

Format:
## YYYY-MM-DD — brief title
3-8 lines of specific insight from that run.

## 2026-06-12 — Brand consistency reference integrated

- Design quality reference now at: `~/.claude/agents/design/memory/design-quality-principles.md`
- For brand consistency critique, always check design-quality-principles.md § 7 (Brand Consistency) before issuing findings.
- The 6 common brand consistency failures (from McKinsey/Lucidpress research) that are ALWAYS flagged as critique items:
  1. Color drift — "close enough" colors instead of exact hex codes
  2. Font substitution — system fonts appearing when brand fonts aren't installed
  3. Logo distortion — squishing or stretching logos to fit a space
  4. Rogue gradients — gradients on flat brands or vice versa
  5. Spacing inconsistency — different padding/margin values across materials (fix: 8-point grid)
  6. Off-brand photography — stock photos emotionally misaligned with brand voice
- Revenue impact reference: McKinsey says consistent brand presentation increases revenue up to 23%; Lucidpress says 33%. Use these figures to frame severity when brand failures are systemic.
- Agency-specific rule: each client brand must have a `brand-guidelines.md` file. If missing, flag as HIGH in critique findings.

---

## 2026-06-15 — Multi-page demo critique: d231/d230 experimental fork vs live brand

- When a demo is an "experimental fork" with explicitly locked new palette/type decisions, the critique reference must be the fork brief, not the live brand-guidelines.md. The two will conflict on fonts, colors, and layout — that's intentional. Check the task brief first.
- CTA label drift is the most common multi-page brand failure. With 5 pages there were 4 distinct CTA surface phrasings — "Marketing Assessment", "Book Marketing Assessment", "DM Marketing Assessment", "Send Assessment Request". Always enumerate every CTA string across all pages before scoring.
- Navy-as-hover is a carry-over pattern: legacy brand colors bleed into new design systems through button hover states. Check hover/active colors specifically — they often escape palette audits.
- Placeholder text in forms ("Santiago Fernández") is a HIGH-visibility brand issue in demos. Clients see placeholders; test data leaks signal carelessness.
- Dead utility classes (e.g., `.ta` defined but never used in body HTML on 4/5 pages) aren't visual bugs but they create governance drift risk — flag them LOW, don't skip them.
- A brand-guidelines.md file that contradicts itself (MARKETING AUDIT vs MARKETING ASSESSMENT in different sections) is worth flagging as a finding even if the demo HTML is correct. The source of truth being wrong is a future failure waiting to happen.

---

## 2026-06-16 — HTSC homepage: duplicate i18n keys mask fabricated claims

- When old + new i18n dict entries are merged (not replaced), JS last-write-wins means the LAST value renders — but the FIRST (orphan) value is a latent risk if key order changes. Always grep for duplicate keys after i18n extension work.
- "ISO 9001:2015" and "SLA 24/7" were the specific unverified claims in this project. Never assume standard-sounding certs/SLAs are confirmed — check brand-kit explicitly. Absence from brand-kit = fabricated claim.
- ISO 9001 appeared in 6 separate locations: HTML static text ×2, i18n dict EN ×2, i18n dict VI ×2. Each must be hunted independently — searching one only misses the rest. Always grep for the claim string after any brand fix to find all instances.
- Preserved "original" nmore template sections are NOT exempt from brand compliance — the partners/trust-badge section contained a fabricated cert. Audit ALL sections, not just the new ones.
- Brand claims check order: (1) grep for numbers/certifications in HTML body, (2) grep in i18n dict EN, (3) grep in i18n dict VI, (4) grep in HTML static fallback text of data-i18n elements. All four must be clean.
- "9 Vietnamese tech products" chip text was in the page — this is also unverified. The brand kit does not confirm a specific product count. Any number-claim in a badge/chip needs explicit brand-kit sourcing.

---

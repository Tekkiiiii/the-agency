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

# critique-design — Critic Memory

Append-only lesson log. Read at the start of every critique session. Never delete or rewrite entries.
Each entry captures one lesson: what worked, what was a blind spot, what wasted rounds.

Format:
## YYYY-MM-DD — brief title
3-8 lines of specific insight from that run.

---

## 2026-05-22 — Day 4 Hermes R1→R2: green palette persists through partial fixes

- D2 (amber circles) fixed the targeted slides (4.24, 4.30) but missed a residual green circle on 4.31c — the "loop back" step that the fixer intentionally colored differently. When giving palette fix instructions, specify ALL instances including special/last-child elements, not just the main selector.
- D4 (4.02a density) changed the slide background from dark to light but left the green card palette untouched. When a fix changes layout/bg, the color must be audited in the same pass — they're not independent.
- D1 (cream-dim by bg) partially worked: callout boxes on dark slides now use highlight-box with amber tint and white text (passes). But the homework TABLE inside a highlight-box on 4.37 still had navy TH text — same fix did not propagate to table header cells. Table elements inside callout boxes need explicit color overrides; they don't inherit from the box.
- Navy text on dark bg is functionally invisible. It reads as "no text" rather than "hard to read." Always check table TH/TD color inside dark-background containers explicitly — inherited values are treacherous.
- Playwright file:// protocol blocked — always start an http.server before navigating. Port 7742 worked cleanly.
- Screenshots saved to ~/.claude/ root by default (not project dir) — always cp to target dir after capture. Include cp step in workflow.

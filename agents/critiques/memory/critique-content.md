# critique-content — Critic Memory

Append-only lesson log. Read at the start of every critique session. Never delete or rewrite entries.
Each entry captures one lesson: what worked, what was a blind spot, what wasted rounds.

Format:
## YYYY-MM-DD — brief title
3-8 lines of specific insight from that run.

---

## 2026-05-22 — Day 4 Hermes deck, R1→R2 iteration

All 7 mandatory R1 fixes landed cleanly — no new issues introduced during the fix pass. Common failure mode (fixer creates new errors while correcting) did not occur here. R1 LOW carryover (4.15a "bạn" code comment) was not mandated and was not applied; carry it to R2.

New issues found in R2 were both on slide 4.18a (model table added in this version): (1) internal contradiction — default model marked in the table did not match the config.yaml shown two slides earlier; (2) a non-existent model ID (gpt-5o-mini instead of gpt-4o-mini). Both are factual/accuracy class errors, not voice or register errors. Lesson: accuracy scan should always cross-check technical claims in tables against code blocks shown earlier in the same deck. A table row that contradicts a code block shown live is a session liability.

The ambiguous comparative "làm tốt nhất con người" (4.02a) was a clarity miss not caught in R1 — the slide was present in R1 but the phrase was not flagged. Calibration note: scan comparative claims in introductory card slides more carefully; they set up the whole deck's capability framing.

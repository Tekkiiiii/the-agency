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

## 2026-06-09 — VN short-form video copy, metaphor consistency + pricing accuracy

Diacritics in rendered frames were clean across all 9 QA frames — tone marks held through Remotion export pipeline. No missed-mark errors. Good to establish this as a lower-risk dimension for this stack going forward.

Main catch: metaphor split on S5 — on-screen card used "sinh viên mới ra trường" while kinetic caption used "lính mới." Both are in the brief but assigned to different surfaces, creating a mixed-metaphor problem within one scene. Lesson: when a brief uses multiple analogies for the same subject, cross-check that each surface (on-screen vs caption) consistently applies a single chosen metaphor per scene.

Critical accuracy flag: pricing table showed Opus $5/$25 with a "June 2026" source label, but Opus 4 (current as of June 2026) is priced at $15/$75. The $5/$25 figures match Opus 3 (legacy). This is exactly the table-vs-external-source cross-check pattern from the 2026-05-22 lesson — applies beyond code blocks to any cited pricing/version data. Always verify API pricing against live source at time of publish.

En-dash vs em-dash: S3 rendered with en-dash (–) in "Mạnh nhất – và đắt nhất." where em-dash (—) was intended. Minor but worth flagging as a Remotion Unicode rendering concern — check character codes in source, not just visual copy.

## 2026-06-09 — VN institutional strategy doc, register + consistency failures

Primary failure class was not diacritics (those were clean throughout) but register contamination: internal-system references ("Tekki xác nhận," "PD-hti" author credit, "T-PILOT-C-SMOKE" test ID) survived into a board-facing document. These are the highest-credibility-risk items in a govtech/defense context — an institutional reader notices them before they notice a missing tone mark. Lesson: for any Vietnamese deliverable flagged as "board-facing" or "for leadership review," run an explicit internal-artifact scan before scoring tone/register.

Accuracy inconsistency pattern: document correctly flagged revenue baseline as [GIẢ ĐỊNH] but applied the flag inconsistently — derived figures (50% YoY, CAGR 38%) appeared as confirmed fact while the base they derived from was flagged uncertain. Lesson: when a [GIẢ ĐỊNH] flag exists on a source number, scan every derived figure in the document and apply consistent flagging. The derivative is never more certain than the base.

Vietnamese number notation: formal VN board documents use "triệu VND" not "M VND"; decimal separator is comma not period ("1,2 tỷ" not "1.2 tỷ"). Fast catch from formal-documents.md — always cross-check number format against that reference for institutional Vietnamese.

Title-case headings: all h2/h3/h4 used Vietnamese title case (initial cap on each word) — this is the English convention, not the Vietnamese formal convention (sentence-initial only). Systemic pattern, one fix instruction covers all headings.

## 2026-06-09 — VN institutional strategy doc R2: fix round partial, 3 new issues

Fix round resolved the highest-severity R1 items (internal artifacts, author credit, Philippines softening, budget notation, [GIẢ ĐỊNH] chips on KPI cards). Main residuals:

Heading case fix was partial: applied to some h2/h3 but missed all h5 elements and several h3s inside brand-card components. Lesson: when fixing heading case in an HTML document, enumerate ALL heading tags (h2 through h5) in a single pass — component-scoped headings (inside .brand-card, .phase-block, .card-dark) are the ones most likely to be skipped.

Workflow artifact language survived in 3 locations despite "Tekki xác nhận" being cleaned. Pattern: the fixer searched for personal names/IDs but not for system-task vocabulary ("phiên làm việc tiếp theo", filename strings like "brand-kit-hti-services.md"). Lesson: run a second artifact scan for file extension strings (.md) and workflow-session phrases, not just for personal names and task IDs.

Derivative [GIẢ ĐỊNH] propagation pattern repeated: 50% YoY growth in para 1 and Careers table still presented as clean fact despite the revenue base being flagged assumption immediately below. The R1 lesson was learned for KPI cards but not applied to prose and marketing-copy contexts. Lesson: apply assumption propagation check to ALL surfaces where the derived number appears — prose, table cells, brand positioning copy — not just KPI widgets.

## 2026-06-13 — HTI APAC audience research, currency error + Meta military job-title coverage

Currency code error caught: "RM700M" used for Thailand agricultural drone market — RM is Malaysian Ringgit, not Thai currency. Thailand uses THB. Pattern: when a multi-market document uses market-specific figures, always scan for currency code consistency. A RM figure in a Thailand section is a definitive error.
"nhắn mạnh" vs "nhấn mạnh" — two instances of the same diacritics substitution error (nhắn = message/text; nhấn = emphasize/press). Context makes the error obvious but tone marks alone don't catch it without reading the word semantically. Lesson: scan for nhắn/nhấn pairs when reviewing formal Vietnamese strategy documents.
Meta job-title targeting: military roles (Coast Guard Commander, Navy Officer) rely on self-reported data in Meta profiles — coverage is sparse and unreliable for government/military. LinkedIn has better self-reported professional data for these roles. Fix: add explicit coverage caveat to Meta military job-title recommendations.
Employer Targeting on Meta (Kementerian Pertahanan, TNI on Facebook) — this is a LinkedIn-strength feature. Meta employer targeting is unreliable for government bodies. Fix: note as "self-reported, low accuracy" to prevent practitioners from over-relying on it.

## 2026-06-12 — HTI audience deep-dive, platform taxonomy accuracy

Clean pass at R2. Key R1 catch: "Broad Match Modifier" in a Google Ads targeting guide — this match type was deprecated by Google in 2021 and no longer exists. Pattern: any document containing ad platform targeting instructions should be scanned for deprecated features (Broad Match Modifier, Expanded Text Ads, Similar Audiences) — these are AI-generated errors from training data predating feature deprecations. Add this to the accuracy scan checklist alongside API pricing and model IDs.

Behavior-category misuse: "Engaged shoppers" used as a proxy for high-income B2B professionals in a defence brand's Facebook targeting section. Engaged shoppers is an e-commerce behavior targeting consumer purchase intent — fundamentally misaligned with a defence/SOE awareness objective. Pattern: Facebook behavior categories named around consumer purchase behaviors (shoppers, travelers, commuters) should be flagged when applied to B2B or institutional brand targeting. Replace with admin/page-manager and B2B engagement behaviors.

Affinity segment mismatch: "Military Buffs" as a YouTube affinity for a defence procurement brand — this targets hobbyist enthusiasts, not institutional procurement officers. Lesson: consumer entertainment/hobby affinity labels (Military Buffs, Car Enthusiasts, Cooking Enthusiasts) are not equivalent to professional/institutional targeting. Always check that affinity segment names match the actual buyer persona, not a layperson with adjacent interests.

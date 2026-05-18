---
name: marketing-assessment-pipeline
description: >
  Full 8-step marketing assessment pipeline for TekkiSolutions — intake → research →
  analysis → brand extraction → Marp generation → 4-critic review → fix rounds →
  zero-flag verification → email delivery. Use as the DEFAULT for processing any
  pending assessment. Trigger: when batch checker finds pending rows, when user says
  "run the assessment pipeline", "process assessment", or "/marketing-assessment-pipeline".
  Also triggers on: "run pipeline for [client]", "generate assessment report".
---

# Marketing Assessment Pipeline

Full executable pipeline. Follow each step sequentially. Do NOT skip steps.

## Supabase Credentials

Read from `/Users/Tekki/projects/tekkisolutions-com/.env.local`:
```bash
eval $(grep -E "^(NEXT_PUBLIC_SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=" /Users/Tekki/projects/tekkisolutions-com/.env.local)
SB_URL="$NEXT_PUBLIC_SUPABASE_URL"
SB_KEY="$SUPABASE_SERVICE_ROLE_KEY"
```

## Step 0 — INTAKE (find pending assessments)

```bash
curl -s "$SB_URL/rest/v1/marketing_analyses?status=eq.pending&select=id,brief_id,locale,created_at" \
  -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY"
```

If empty → "No pending assessments" → STOP.

For each pending row, run Steps 1-8 sequentially.

## Step 1 — FETCH BRIEF

```bash
curl -s "$SB_URL/rest/v1/assessment_briefs?id=eq.{brief_id}&select=*" \
  -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY"
```

Extract: `contact_name`, `contact_email`, `contact_social`, `business_description`,
`target_customer`, `current_channels`, `main_challenge`, `goals`, `raw_transcript`, `locale`.

Set status to `analyzing`:
```bash
curl -s -X PATCH "$SB_URL/rest/v1/marketing_analyses?id=eq.{id}" \
  -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY" \
  -H "Content-Type: application/json" -d '{"status":"analyzing"}'
```

## Step 2 — RESEARCH (scrape client platforms)

Parse `contact_social` for URLs. For each URL found:

1. **Website** — Use WebFetch or Lightpanda to scrape: page title, meta description,
   tech stack hints, page speed indicators, mobile-friendliness, content freshness.
2. **Social profiles** — Facebook followers/posting frequency, Instagram followers/engagement,
   LinkedIn company page activity, Google Business reviews/rating.
3. **Brand extraction (MANDATORY — pitfall 21):**
   - CSS custom properties (`--brand-color`, `--primary`)
   - Header/nav background and link colors
   - OG `<meta name="theme-color">`
   - Logo download attempt
   - Fallback: use TekkiSolutions default colors (#1B1F3B, #3D4266, #F5A623)

4. **Competitor quick-scan** — Search for 2-3 competitors in the same space/city.
   Note: website quality, social following, content output, Google ranking position.

Store research results for use in Step 3. Save brand colors as JSON:
```json
{"primary": "#hex", "secondary": "#hex", "accent": "#hex"}
```

**Gate:** At least one data source scraped. If all fail, proceed with transcript-only analysis.

## Step 3 — ANALYSIS (marketing presence + transcript)

Using the brief data (Step 1) + research data (Step 2), run three analyses.
Route through the Marketing department — spawn Marketing Lead agent for 3a and 3b.

### 3a. Marketing Presence Analysis (via Marketing Lead → @marketing-lead)
Spawn Marketing Lead agent with the brief + research data. The Marketing Lead:
- Scores overall marketing presence (1-10) with justification
- Channel-by-channel assessment (Website, Social, SEO, Paid, Content, CRM)
- Each channel: current state, effectiveness rating, specific evidence from research
- Identifies top 3 quick wins with expected impact and estimated ROI
- Maps top 3 competitive gaps vs. scraped competitors
- Recommends channel priority order based on client's budget and maturity
- Assesses brand positioning strength (messaging clarity, differentiation, consistency)

### 3b. Marketing Strategy Analysis (via Marketing Lead → @marketing-lead)
The Marketing Lead also produces:
- GTM (Go-to-Market) assessment — is the current approach working? What's broken?
- Funnel analysis — where are leads dropping off? (awareness → interest → inquiry → close)
- Content-market fit — does existing content match target customer pain points?
- Channel-market fit — are they on the right platforms for their target?
- Budget allocation assessment — is the ad spend optimally distributed?
- Seasonal strategy — opportunities tied to business cycles (Tet, Q4, industry events)

### 3c. Transcript Analysis
- Owner-perceived problems vs. consultant-identified root causes
- Business maturity: L1 (Traditional) / L2 (Basic Digital) / L3 (Digitized)
- Pain point prioritization by severity and solvability
- Emotional signals (frustration, aspiration, fears)
- Gap between what client SAYS they want vs. what they actually NEED

Set status to `drafting`:
```bash
curl -s -X PATCH "$SB_URL/rest/v1/marketing_analyses?id=eq.{id}" \
  -H "apikey: $SB_KEY" -H "Authorization: Bearer $SB_KEY" \
  -H "Content-Type: application/json" -d '{"status":"drafting"}'
```

## Step 4 — MARP GENERATION (branded interactive report)

Generate a Marp markdown report using `theme: tekkisolutions-client`.

### Slide structure (14-16 slides minimum):

```
SECTION A — COVER (TekkiSolutions branded)
  1. [cover] "Marketing Assessment Report" / Client name + business / "Prepared by TekkiSolutions"

SECTION B — EXECUTIVE OVERVIEW
  2. Executive Summary — 3-4 key findings with SPECIFIC numbers from research
  3. Current State Scorecard — CHART: horizontal bar chart of channel scores (1-10)

SECTION C — CHANNEL ANALYSIS (use client brand colors)
  4. [section-title] "Channel-by-Channel Analysis" (or Vietnamese equivalent)
  5. Website & SEO — current state, ranking gaps, competitor comparison, recommendations
  6. Social Media — platform-by-platform analysis, posting frequency, engagement, recommendations
  7. Paid & Organic — ad spend ROI, keyword analysis, content strategy gaps
  8. CRM & Lead Management — lead flow, follow-up gaps, conversion bottlenecks

SECTION D — COMPETITIVE LANDSCAPE
  9. Competitive Gaps — CHART: radar chart comparing client vs 2-3 competitors across dimensions

SECTION E — FUNNEL & STRATEGY
  10. Funnel Analysis — CHART: funnel/bar chart showing drop-off at each stage with numbers

SECTION F — RECOMMENDATIONS
  11. Quick Wins — top 3 actions for next 30 days with expected impact
  12. 90-Day Roadmap — Month 1 / Month 2 / Month 3 with deliverables and KPIs
  13. Year 1 Investment Estimate — CHART: donut chart of budget allocation by category (pitfall 32)
  14. RACI Matrix — who does what (client vs TekkiSolutions) (pitfall 32)
  15. Risk Register — top 3 risks with severity + mitigations (pitfall 32)

SECTION G — CLOSING (TekkiSolutions branded)
  16. [cta] "Ready to implement?" / CTA to discovery call or Signal Sprint (pitfall 28)
```

### Charts (MANDATORY — at least 4 per report)

The rendered HTML includes Chart.js. Embed charts using `<canvas>` with `data-chart` JSON attribute.
Chart.js auto-initializes on page load.

**Chart syntax in Marp markdown:**

```html
<canvas data-chart='{"type":"bar","data":{"labels":["Website","Social","SEO","Ads","Content","CRM"],"datasets":[{"label":"Score","data":[2,2,3,3,1,1],"backgroundColor":"#2C1B6C"}]},"options":{"indexAxis":"y","scales":{"x":{"max":10}},"plugins":{"legend":{"display":false}}}}' style="max-width:100%;height:300px"></canvas>
```

**Required charts (minimum 4):**

1. **Channel Scorecard** (horizontal bar) — scores 1-10 for each channel
   - Type: `bar` with `indexAxis: "y"`
   - Colors: client primary for bars
   - X-axis max: 10

2. **Competitive Radar** — client vs 2-3 competitors across 5-6 dimensions
   - Type: `radar`
   - Colors: client primary (filled, alpha 0.3), competitor colors as outlines
   - Dimensions: Website, Content, Social, SEO, Brand, Digital Maturity

3. **Funnel Chart** (horizontal bar) — lead volume at each funnel stage
   - Type: `bar` with `indexAxis: "y"`
   - Stages: Awareness → Research → Inquiry → Qualification → Close → Lost
   - Colors: gradient from green (top) to red (lost)

4. **Budget Allocation** (doughnut) — Year 1 investment breakdown
   - Type: `doughnut`
   - Categories: Website, Content, Ads, CRM, TekkiSolutions Fee
   - Colors: palette from client primary

**Optional charts (add when data supports):**
5. Revenue projection (line) — current vs projected over 12 months
6. Posting frequency comparison (grouped bar) — client vs competitors by platform
7. ROI waterfall — cost vs return by channel

**Chart styling rules:**
- Use client brand primary as the main chart color
- TekkiSolutions amber (#F5A623) for highlights/accents
- Font family: Inter
- No 3D effects, no gradients on bars
- Always include axis labels and a clear title above the chart
- `max-width: 100%; height: 300px` on all canvases

### Content rules (from pitfalls):
- Use client's ACTUAL data — specific numbers, not generic advice
- Revenue projections must include channel attribution (pitfall 30)
- 90-day claims = paid/social only, not organic SEO (pitfall 31)
- CTA = implementation action, never "book assessment" (pitfall 28)
- No scarcity language for professional audiences (pitfall 29)
- Vietnamese: full diacritics, correct xưng hô (pitfall 1-3)
- Each recommendation: concrete action + expected outcome + timeline

### Language:
- `locale=vi` → write in Vietnamese
- `locale=en` → write in English

## Step 5 — 4-CRITIC REVIEW (parallel)

Spawn 4 critic agents IN PARALLEL. Each reviews the generated Marp markdown.

### Critic 1: Content Critique
Use the `/content-critique` skill or spawn a Content Editor agent.
Focus: narrative logic, evidence quality, client specificity, CTA correctness,
tone (consultant not salesy), language quality (diacritics if Vietnamese).
Score: 0-100. List issues with slide numbers and severity (critical/major/minor).

### Critic 2: Marketing Critique (via @marketing-lead)
Route through Marketing department — spawn Marketing Lead agent.
Focus: strategic coherence against 3a/3b analysis, revenue model credibility,
competitive positioning, CTA conversion design, channel strategy completeness,
90-day claim accuracy, funnel logic, budget allocation recommendations,
brand positioning consistency across slides.
Score: 0-100. List issues with slide numbers and severity (critical/major/minor).
The Marketing Lead has full context from Step 3 — they review whether the
report accurately reflects their analysis or lost nuance in translation.

### Critic 3: Design Critique (screenshot-based — NEVER review source only)
Render the Marp markdown to HTML, open it in the headless browser, and screenshot
EVERY slide. The design critic reviews the SCREENSHOTS, not the markdown source.

```bash
# 1. Render Marp to HTML file
npx tsx -e "
import { renderMarp } from '/Users/Tekki/projects/tekkisolutions-com/src/lib/marp-render';
import { generateMarpTheme } from '/Users/Tekki/projects/tekkisolutions-com/src/lib/marp-theme';
import { readFileSync, writeFileSync } from 'fs';
const md = readFileSync('/tmp/report.md', 'utf-8');
const theme = generateMarpTheme({primary:'CLIENT_PRIMARY',secondary:'CLIENT_SECONDARY',accent:'CLIENT_ACCENT'});
writeFileSync('/tmp/report.html', renderMarp(md, theme));
"

# 2. Open in headless browser and screenshot each slide
B="/Users/Tekki/.claude/skills/browse/dist/browse"
$B goto file:///tmp/report.html
$B screenshot /tmp/slide-1.png
# Click to advance, screenshot each slide
$B click body && $B screenshot /tmp/slide-2.png
# ... repeat for all slides
```

Then Read each screenshot PNG so the design critic SEES the visual output.

Focus areas (reviewed from screenshots, not source):
- Visual hierarchy — do headings stand out? Is there clear content flow?
- Typography — font rendering, size readability, line spacing
- Color contrast — client brand colors readable against backgrounds?
- Table rendering — aligned columns, readable cell sizes, proper borders
- Slide density — too much text per slide? Enough white space?
- Brand consistency — TekkiSolutions cover/CTA match brand guidelines?
- Section-title slides — client brand colors applied correctly?
- Mobile considerations — would this render on a phone screen?

Score: 0-100. List issues with slide number + screenshot evidence + severity.
**Any design issue claimed without a screenshot is not valid.**

### Critic 4: Operations Critique
Use the `/operations-critique` skill or spawn an Operations Lead agent.
Focus: implementation feasibility, cost transparency, RACI clarity,
risk management quality, measurement framework (KPIs).
Score: 0-100. List issues with slide numbers and severity (critical/major/minor).

### Scoring & Gate

All critics score on a **0-100 scale**. Each critic reports:
- Overall score (0-100)
- Sub-dimension scores (0-100 each)
- Issues list with slide numbers and severity (critical/major/minor)

**GATE — both conditions must be met:**
1. **Average of all 4 scores ≥ 80**
2. **No individual score below 70**

If both conditions met → skip to Step 7.
If either condition fails → proceed to Step 6.

## Step 6 — FIX ROUNDS (loop until gate passes)

1. Collect ALL issues from critics — prioritize by severity (critical → major → minor)
2. Also collect critical/major issues from passing critics (above 70 but with important fixes)
3. Fix the Marp markdown — edit specific slides, rewrite weak sections
4. Re-run ONLY the failing critics (score < 70) + any critic that had critical-severity issues
5. **LOOP:** Check gate again (avg ≥ 80, none < 70). If fails, fix and re-review.
6. **No max iterations — loop until gate passes.** The report does not ship until quality is met.
7. If stuck after 5 rounds on the same issue → escalate to Tekki for judgment call

### Fix priority:
1. Factual errors (wrong numbers, unsourced claims)
2. Missing mandatory content (no RACI, no cost estimate, no risk register)
3. Strategy gaps (unanchored revenue model, missing channel attribution)
4. Language/tone issues
5. Structure/flow issues

### Cross-slide verification after every fix:
- All numbers consistent across slides
- All math correct (averages, totals)
- No duplicate content between slides

## Step 7 — STORE + VERIFY

Store the final Marp markdown in Supabase:

```python
import json, subprocess

marp_md = open("report.md").read()
payload = json.dumps({
    "marp_markdown": marp_md,
    "client_brand_colors": {"primary": "#hex", "secondary": "#hex", "accent": "#hex"},
    "status": "review"
})

# Write payload to temp file to avoid shell escaping issues
with open("/tmp/patch.json", "w") as f:
    f.write(payload)

subprocess.run([
    "curl", "-s", "-X", "PATCH",
    f"{SB_URL}/rest/v1/marketing_analyses?id=eq.{id}",
    "-H", f"apikey: {SB_KEY}",
    "-H", f"Authorization: Bearer {SB_KEY}",
    "-H", "Content-Type: application/json",
    "-d", f"@/tmp/patch.json"
])
```

### Final checklist (from quality checklist):
- [ ] All critic scores 7.5+
- [ ] Client's actual data referenced (not generic)
- [ ] Vietnamese diacritics correct (if applicable)
- [ ] CTA points to implementation (not "book assessment")
- [ ] No scarcity language
- [ ] RACI, cost estimate, and risk slides present
- [ ] Revenue projections include channel attribution
- [ ] 90-day claims specify paid/social only
- [ ] Client brand colors injected
- [ ] Brand-database.md updated

## Step 8 — DELIVER

### 8a. Telegram notification to Tekki:
```bash
TG_API_BASE="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
curl -s -X POST "${TG_API_BASE}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"Assessment report ready for review\nClient: {contact_name}\nBusiness: {business_description}\nScores: Design {d}/10 Content {c}/10 Marketing {m}/10 Ops {o}/10\nView: https://tekkisolutions-com-tekkiiiiis-projects.vercel.app/{locale}/audit/report/{id}\"}"
```

### 8b. Email to customer (when RESEND_API_KEY is configured):
The email is sent via `src/lib/email.ts` sendAssessmentReadyEmail().
If RESEND_API_KEY is not set, skip email and log "Email skipped — no RESEND_API_KEY".

### 8c. Report summary:
```
PIPELINE COMPLETE — {contact_name} ({business_description})

  Scores: Design {d}/10 | Content {c}/10 | Marketing {m}/10 | Ops {o}/10
  Fix rounds: {n}
  Report: /audit/report/{id}
  Status: review
  Email: {sent|skipped}
```

---

## Learned Pitfalls (MANDATORY — read before every pipeline run)

### Vietnamese Text
1. **DIACRITICS ARE NON-NEGOTIABLE.** "Buc tranh hien tai" is WRONG. "Bức tranh hiện tại" is CORRECT.
2. **Vietnamese titles under 45 characters** to avoid wrapping.
3. **Correct xưng hô.** "chị [Name]" for female, "anh [Name]" for male. Never "bạn" in professional context.

### Client Brand Extraction
4. **Always extract in Step 2.** Priority: CSS custom properties > header colors > OG theme-color > social visuals.
5. **Client colors = secondary accent.** TekkiSolutions stays base. Client color on: section-title slides, tables, accents.
6. **Auto-populate brand-database.md** after every scrape (never skip — pitfall 24).

### Content Rules
7. **CTA = implementation action** (Signal Sprint / discovery call). Never "Book Your Marketing Assessment" (pitfall 28).
8. **No scarcity language** ("spots fill fast", "limited") for professional audiences (pitfall 29).
9. **Revenue projections must include channel attribution** footnote (pitfall 30).
10. **90-day claims = paid/social only.** Organic SEO takes 12-24 months (pitfall 31).

### Mandatory Slides
11. **RACI/ownership matrix** — who does what internally vs. TekkiSolutions.
12. **Year 1 cost estimate** — investment range by category.
13. **Risk register** — top 3 risks with mitigations.

### Pipeline Execution
14. **Use Python for JSON payloads** — shell escaping breaks Marp markdown with special chars.
15. **Telegram curl: pre-assign URL to variable** (TG_API_BASE) to avoid security pattern triggers.
16. **4-critic review is NOT optional.** Every assessment goes through all 4 critics before delivery.

---

## Quality Checklist (verify at Step 7)

- [ ] All 4 critic scores: average ≥ 80, none below 70
- [ ] Client's actual data referenced (not generic advice)
- [ ] Vietnamese diacritics correct (if applicable)
- [ ] Correct xưng hô (if Vietnamese)
- [ ] CTA = implementation action
- [ ] No scarcity language
- [ ] RACI matrix slide present
- [ ] Year 1 cost estimate slide present
- [ ] Risk register slide present
- [ ] Revenue projections include channel attribution
- [ ] 90-day claims specify paid/social only
- [ ] Client brand colors injected (section-title slides, tables, accents)
- [ ] Brand-database.md updated with client entry
- [ ] All numbers consistent across slides
- [ ] Supabase status updated to "review"
- [ ] Telegram notification sent

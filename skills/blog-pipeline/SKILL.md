---
name: blog-pipeline
version: 1.0.0
description: "TekkiSolutions blog pipeline — research Vietnamese SME pain points, write bilingual SEO/GEO/AEO blog post, polish, output. Invoke twice a week."
---

# Blog Pipeline: TekkiSolutions

You are producing a blog post for TekkiSolutions (`/insights/blog/`). The post targets Vietnamese SME owners and marketing managers. Every post drives readers toward requesting a free Marketing Assessment.

**Before starting, read the content strategy SSOT:**
`~/.claude/projects/tekki/memory/blog-content-strategy.md`

## Input Parameters

Collect via AskUserQuestion if not provided in the invocation:

- **topic** (optional): Pre-selected topic. If blank, Stage 1 finds one.
- **pillar** (optional): `1`–`5` (AI Tools | Diagnosis | Acquisition | Digital Transformation | Quick Wins). If blank, auto-assigned from research.
- **post_type** (optional): `standard` | `quick-win` | `authority` (default: `standard`)

## Pipeline Tracker

Create tracker at `~/.claude/projects/tekki/outputs/blog-pipeline/{date}-tracker.md`:

```markdown
## Blog Pipeline: {date}
Started: {timestamp}
Topic: {topic or "TBD — research phase"}
Pillar: {pillar}
Post type: {post_type}

| # | Stage | Status | Gate | Notes |
|---|-------|--------|------|-------|
| 1 | RESEARCH | pending | -- | -- |
| 2 | TOPIC SELECT | pending | -- | -- |
| 3 | WRITE EN | pending | -- | -- |
| 4 | WRITE VI | pending | -- | -- |
| 5 | CRITIQUE | pending | -- | -- |
| 6 | POLISH | pending | -- | -- |
| 7 | OUTPUT | pending | -- | -- |
```

---

## Stage 1: RESEARCH

Search for current Vietnamese SME pain points. Run these searches in parallel:

### 1a: Vietnamese forum/community research
Use WebSearch with queries like:
- `site:facebook.com "marketing" "doanh nghiệp nhỏ" {current_month} {current_year}`
- `site:tinhte.vn "marketing" OR "quảng cáo" {current_year}`
- `"SME Vietnam" marketing challenges {current_year}`
- `"doanh nghiệp nhỏ" "khó khăn" marketing {current_year}`
- `Vietnam SME digital marketing trends {current_year}`

### 1b: Trending topic research
Use WebSearch with queries like:
- `Google Trends Vietnam marketing {current_month}`
- `Meta Ads Vietnam updates {current_year}`
- `AI marketing tools {current_year} new`
- `Zalo business update {current_year}`

### 1c: Competitor content gap
Use WebSearch:
- `site:brandsvietnam.com marketing SME {current_year}`
- `site:cafef.vn "marketing" "doanh nghiệp" {current_month}`

Collect findings into a research brief: 5-10 pain points with source, frequency of mention, and urgency level.

**Gate:** At least 5 distinct pain points identified with sources.

---

## Stage 2: TOPIC SELECT

If a topic was provided as input, validate it against the scoring criteria below. If no topic was provided, select the best candidate from Stage 1 research.

### Scoring (from content strategy)

Score each candidate 1-10 across four dimensions:

| Dimension | Weight | Question |
|---|---|---|
| ICP Pain Intensity | 30% | How acute? Would a reader stop scrolling? |
| Search Intent Match | 25% | Actively searched in Vietnam? |
| Conversion Proximity | 25% | How close to requesting a Marketing Assessment? |
| Differentiation | 20% | Can TekkiSolutions provide a unique angle? |

**Minimum score to proceed:** 6.5/10 weighted average.

Auto-assign pillar based on topic if not provided. Check pillar balance: do NOT repeat Pillar 5 if the last post was also Pillar 5 (check `~/.claude/projects/tekki/outputs/blog-pipeline/` for recent posts).

Present selected topic + pillar + rationale to user via AskUserQuestion for approval.

**Gate:** User approves topic.

---

## Stage 3: WRITE EN (English version)

Write the English blog post following the framework from the content strategy:

### Structure
1. **H1** -- Keyword-led headline (answers the reader's question directly)
2. **Meta hook** (2-3 sentences) -- the one thing you will learn
3. **Key Takeaways** / TL;DR box (3-4 bullet points for GEO)
4. **Table of contents** (for posts > 1,000 words)
5. **Problem framing** (150-200 words) -- name the specific pain
6. **H2 sections** (3-5 sections) -- each answers one part of the problem
7. **Vietnamese-specific angle** (one H2 or callout) -- local context/example
8. **FAQ section** (4-6 questions matching voice search queries)
9. **CTA section** -- "DM 'MARKETING ASSESSMENT'" (NEVER "audit")

### Word count targets
- Quick win: 800-1,000 words
- Standard: 1,200-1,800 words
- Authority: 2,000-2,500 words

### Tone
- Smart-friend voice, not consultant-speak
- Lead with business outcomes (revenue, CAC, ROAS), never technology
- Short sentences where they land harder, longer where reasoning needs room
- Vietnamese cultural register: direct, respectful, practical

### SEO/GEO/AEO optimization (MANDATORY — apply during writing)

**SEO (Search Engine Optimization):**
- Primary keyword in H1, first 100 words, and 2+ H2 headings
- URL slug: transliterated, hyphenated, max 60 chars
- Meta description: 120-140 chars, ends with action verb
- **Internal links: 2-3 links to other TekkiSolutions pages** (services, case studies, other blog posts). Use markdown links: `[link text](/en/services/ai-websites)`. Map to real routes:
  - `/services` — services overview
  - `/services/ai-websites` — AI website modernization
  - `/services/custom-systems` — custom business systems
  - `/insights/case-studies/amani-crm` — Amani CRM case study
  - `/audit` — free Marketing Assessment
  - `/insights/blog/{slug}` — other blog posts
- **External links: 2-3 links to authoritative sources** cited in the research brief (government reports, industry publications, research papers). Use full URLs.

**GEO (Generative Engine Optimization — for AI citations):**
- Direct answer to the post's question in first 100 words (AI models extract opening answers)
- Featured snippet format in intro ("What is X? X is...")
- **Key Takeaways section MUST be the first section** (heading: "Key Takeaways" in EN, "Điểm chính" in VI) with 3-5 bullet points in complete sentences. This is the primary AI citation hook.
- Include factual statements with sources that can be cited ("According to [source], X% of Vietnamese SMEs...")
- Define key terms on first use (AI systems extract definitions for featured answers)

**AEO (Answer Engine Optimization — for voice/zero-click):**
- FAQ section with 4-6 natural-language questions matching voice search queries
- One definition box per post for the core term
- Step-by-step numbered lists where applicable (Google/Siri extract numbered steps)
- Include "in Vietnam" / "for Vietnamese businesses" in key headings where accurate

**Schema markup fields (populated in metadata.yaml for the site to render):**
- BlogPosting: headline, description, datePublished, author, publisher
- FAQPage: question/answer pairs from the FAQ section

### CTA rules
- Exactly one CTA per post -- always "MARKETING ASSESSMENT" (never "audit")
- Mid-post callout (posts > 1,500 words): tie to what reader just learned
- End-of-post CTA: soft close using recognition-to-resolution arc
- One FAQ answer naturally mentions the Marketing Assessment

### Output format

Write the post as a markdown file with YAML frontmatter:

```yaml
---
title: "Post Title Here"
slug: "post-slug-here"
description: "Meta description 120-140 chars"
pillar: 2
post_type: standard
funnel_stage: TOFU
target_keyword_en: "primary english keyword"
target_keyword_vi: "primary vietnamese keyword co dau"
publish_date: "YYYY-MM-DD"
author: "TekkiSolutions"
schema: ["BlogPosting", "FAQPage"]
---
```

**Gate:** Post meets word count target and includes all structural elements.

---

## Stage 4: WRITE VI (Vietnamese adaptation)

Adapt the English post for Vietnamese readers. This is a cultural adaptation, NOT a word-for-word translation.

### Adaptation rules
- Replace generic examples with local ones (HCM/Hanoi businesses, Shopee/Tiki, Zalo)
- Use Vietnamese-specific data where it exists
- Diacritic strategy: co dau in body, khong dau variants in meta description
- Use national vocabulary forms (both Northern/Southern) unless city-specific
- CTA in Vietnamese: "Nhan tin 'MARKETING ASSESSMENT'" or "Bat dau danh gia Marketing mien phi"
- Maintain the same structure, H2 headings, and FAQ section

Write as a separate markdown file with `-vi` suffix.

Load `~/.claude/skills/vietnamese-language/` reference files as needed for register, tone, and cultural accuracy.

**Gate:** Vietnamese version has adapted (not just translated) examples and local context.

---

## Stage 5: CRITIQUE

Invoke `/content-critique` on both EN and VI drafts.

Check specifically for:
- AI vocabulary / slop patterns (invoke `/stop-slop` check)
- CTA says "assessment" not "audit"
- Tone matches smart-friend voice (not consultant-speak, not AI-generic)
- Vietnamese version has genuinely adapted content (not machine translation)

**SEO/AEO/GEO compliance check (MANDATORY):**
- [ ] Key Takeaways is the FIRST section with 3-5 bullet points
- [ ] Primary keyword in H1, first 100 words, and 2+ H2 headings
- [ ] Direct answer to the post's question in first 100 words
- [ ] 2-3 internal links to other TekkiSolutions pages (verify routes exist)
- [ ] 2-3 external links to authoritative sources with full URLs
- [ ] FAQ section with 4-6 voice-search-style questions
- [ ] At least one factual statement with a cited source (for AI citation)
- [ ] Meta description: 120-140 chars, ends with action verb
- [ ] URL slug: ASCII, hyphenated, max 60 chars

If any SEO/AEO/GEO item fails, revise before grading. A post missing internal links or Key Takeaways cannot score above C.

**Gate:** Grade B or above on both versions. If C or below, revise and re-critique (max 2 cycles).

---

## Stage 6: POLISH

Invoke `/content-polish` on both EN and VI versions. This is MANDATORY per the Marketing→CCO content pipeline.

The content-polish skill runs:
1. Humanizer (format-calibrated)
2. Anti-fragmentation pass
3. Proofreader (post-humanizer mode)

**Gate:** Both versions pass humanizer self-audit, anti-fragmentation check, and proofreader review.

---

## Stage 7: OUTPUT

### File output
Save final files to:
```
~/.claude/projects/tekki/outputs/blog-pipeline/{YYYY-MM-DD}-{slug}/
  post-en.md        # English version
  post-vi.md        # Vietnamese version
  research-brief.md # Stage 1 research output
  tracker.md        # Pipeline tracker (move from earlier location)
  metadata.yaml     # Structured metadata for site integration
```

### metadata.yaml format
```yaml
title_en: "Post Title"
title_vi: "Tieu de bai viet"
slug: "post-slug"
pillar: 2
post_type: standard
funnel_stage: TOFU
target_keyword_en: "keyword"
target_keyword_vi: "tu khoa"
publish_date: "YYYY-MM-DD"
word_count_en: 1450
word_count_vi: 1520
schema: ["BlogPosting", "FAQPage"]
critique_grade_en: A
critique_grade_vi: B+
pipeline_run: "YYYY-MM-DD"

# SEO/AEO/GEO metadata (for site rendering and schema markup)
seo:
  canonical_slug: "post-slug"
  internal_links:
    - path: "/services/ai-websites"
      anchor_text_en: "AI website modernization"
      anchor_text_vi: "hiện đại hóa website bằng AI"
    - path: "/audit"
      anchor_text_en: "free Marketing Assessment"
      anchor_text_vi: "Đánh giá Marketing miễn phí"
  external_links:
    - url: "https://source.example.com/article"
      anchor_text: "Source Title (Year)"
  faq_schema:
    - q_en: "Question in English?"
      a_en: "Answer in English."
      q_vi: "Câu hỏi tiếng Việt?"
      a_vi: "Câu trả lời tiếng Việt."
  key_takeaways_en:
    - "Takeaway 1 in complete sentence."
    - "Takeaway 2 in complete sentence."
  key_takeaways_vi:
    - "Điểm chính 1."
    - "Điểm chính 2."
```

### Final report

```markdown
## Blog Pipeline Report
Date: {date}
Topic: {topic}
Pillar: {pillar} | Type: {post_type} | Funnel: {funnel_stage}

| # | Stage | Result | Gate | Notes |
|---|-------|--------|------|-------|
| 1 | RESEARCH | {result} | {N} pain points | {sources} |
| 2 | TOPIC SELECT | {result} | Score: {score}/10 | {rationale} |
| 3 | WRITE EN | {result} | {word_count} words | {keyword} |
| 4 | WRITE VI | {result} | {word_count} words | adapted |
| 5 | CRITIQUE | {result} | EN: {grade} / VI: {grade} | {revision_cycles} |
| 6 | POLISH | {result} | humanizer PASS | -- |
| 7 | OUTPUT | {result} | files saved | {output_path} |

Output: {output_path}
Next step: integrate into tekkisolutions-com site (manual or via tekki-pd)
```

---

## Notes

- The blog page at `/insights/blog/` currently shows an empty state. Posts from this pipeline are saved as markdown files for manual integration until the blog rendering infrastructure is built.
- When the site supports dynamic blog posts (MDX, CMS, or database), update Stage 7 to write directly to the content source.
- Every post must be reviewed by the user before publishing. This pipeline produces drafts, not auto-published content.

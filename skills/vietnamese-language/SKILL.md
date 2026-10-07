---
name: vietnamese-language
version: 1.0.0
description: >
  Vietnamese on-demand factual reference (formal documents, press releases, regional dialects, regulation, platform facts, SEO/diacritics). NOT a voice, hook, or template source; voice comes from exemplars (brand/voice-exemplars-vi, pending). Load only when a task needs factual Vietnamese context.
---

# Vietnamese Language Knowledge Base

On-demand factual reference (formal documents, press releases, dialects, regulation, platform facts). NOT a voice, hook, or template source. Voice comes from exemplars (brand/voice-exemplars-vi, pending). Do not copy phrasing from these files.

## Boundaries

**Already covered — do NOT load these reference files if what you need is:**
- Tone registers, diacritic/Unicode rules, regulatory constraints → `content-creator/languages/vi.md`
- Ad copy structure, funnel-stage specs, compliance checklist → `marketing/05-copy-quang-cao/`
- Email sequence strategy, automation, KPIs → `marketing/14-email-marketing/`
- Grammar rules, tone mark errors, code-switching → `proofreader/SKILL.md`
- Active VN editing (de-template prose, translationese cleanup, deep grammar check, style consistency) → `humanizer-vi`, `translationese-cleaner-vi`, `grammar-checker-vi`, `style-guide-vi`
- Platform format specs (character limits, aspect ratios, hashtag counts) → `content-creator/references/platforms.md`

**This skill fills the gap for:** platform facts, formal/legal/press Vietnamese, viral format background, SEO diacritic strategy, regional dialects, Gen Z slang formation patterns, advertising cultural values and regulatory facts, and email/messaging register conventions.

---

## Routing Table

Read this table to decide which reference file to load. Load only the file(s) needed for your current task.

### Platform Files (`references/platforms/`)

| Task signal | Load |
|---|---|
| Facebook age-segment register, Marketplace conventions | `references/platforms/facebook.md` |
| TikTok ad-disclosure hashtags (#quangcao, #hoptac) | `references/platforms/tiktok.md` |
| Instagram formats (Feed, Carousel, Reels, Stories, Collab) | `references/platforms/instagram.md` |
| LinkedIn VN register and honorifics, job posting structure | `references/platforms/linkedin.md` |
| Zalo OA/ZNS mechanics (unverified limit), CS register | `references/platforms/zalo.md` |
| YouTube description mechanics (visible lines, chapters, hashtags) | `references/platforms/youtube.md` |
| Twitter/X post limit, informal abbreviations | `references/platforms/twitter-x.md` |
| Threads VN (stub, no content yet) | `references/platforms/threads.md` |

### Topic Files (`references/`)

| Task signal | Load |
|---|---|
| Government document (Nghị định, Thông tư, Quyết định) | `references/formal-documents.md` |
| Business correspondence, memo, proposal | `references/formal-documents.md` |
| Academic or legal writing in Vietnamese | `references/formal-documents.md` |
| Press release / thông cáo báo chí | `references/press-releases.md` |
| Viral format list, meme conventions, slang lifecycle, seasonal calendar | `references/viral-content.md` |
| Educational content structure, e-learning platform language | `references/educational-content.md` |
| Ministry of Education language standards | `references/educational-content.md` |
| SEO Vietnamese keywords, diacritic strategy, CocCoc | `references/seo-content-marketing.md` |
| Content marketing structure, long-form blog | `references/seo-content-marketing.md` |
| Northern vs Southern vocabulary differences | `references/regional-dialects.md` |
| Diaspora Vietnamese (Việt kiều) | `references/regional-dialects.md` |
| Gen Z slang formation, internet language, teen code | `references/gen-z-slang.md` |
| Number substitution, English loanword integration | `references/gen-z-slang.md` |
| Advertising values framework (Confucian/Buddhist/Taoist) | `references/advertising-copywriting.md` |
| KOL/KOC tier conventions | `references/advertising-copywriting.md` |
| Seasonal campaign context (Tết, 8/3, 20/10) | `references/advertising-copywriting.md` |
| Regulatory language (Bộ Y Tế, health claims, Luật Quảng cáo) | `references/advertising-copywriting.md` |
| Business email register, customer service conventions | `references/email-messaging.md` |
| Newsletter conventions, SMS marketing | `references/email-messaging.md` |
| Zalo OA broadcast vs email | `references/email-messaging.md` |

---

## Integration Points

These existing skills should cross-reference this skill:

- **`content-creator`** with `language=vi`: supplements `vi.md` with platform facts (mechanics only) when the brief specifies Zalo OA, LinkedIn VN, YouTube VN, or Twitter/X VN (platforms not covered in vi.md)
- **`marketing/05-copy-quang-cao`**: load `advertising-copywriting.md` for Tết campaign context or health/beauty work requiring Bộ Y Tế compliance facts
- **`marketing/14-email-marketing`**: load `email-messaging.md` for Zalo OA vs email register and Vietnamese newsletter register
- **`marketing/04-script-video`**: load `gen-z-slang.md` when a brief requires slang meaning lookup
- **`proofreader`**: load `formal-documents.md` when proofreading government/legal documents; load `press-releases.md` when proofreading thông cáo báo chí

---

## Loading Protocol

1. Check the routing table above for your current task
2. Load only the matching reference file(s) — never load all 17
3. If your task spans multiple areas (e.g., Tết TikTok campaign for Gen Z), load the relevant files (tiktok.md + viral-content.md + gen-z-slang.md)
4. Cite which reference file(s) you loaded in your output so downstream agents know what was consulted
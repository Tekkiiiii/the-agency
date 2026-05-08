# SEO/GEO/AEO Integration Checklist

Quick-reference checklist combining all areas for content-critique SEO & Value dimension scoring. Load this file when scoring dimension 5 in `/content-critique` and the content type is blog/landing/docs.

---

## SEO & Value Dimension Scoring Rubric

| Score | Criteria |
|-------|----------|
| 9-10 | Primary keyword in H1 and first 100 words; meta description present and compelling (150-160 chars); FAQPage/Article schema present; content directly answers the searcher's question in the first paragraph; no keyword stuffing; value proposition clear within 30 seconds; internal links to 2-3 related pages; external links to 2+ authoritative sources; BLUF writing (answer first in each section); at least one quantitative claim with source; entity schema with `sameAs` |
| 7-8 | Keyword targeting evident; meta description present; content answers the question; some heading structure (H2s); value proposition reachable; no stuffing; at least one internal link; some data points present |
| 5-6 | Keywords present but unfocused; meta description missing or default; partial answer to searcher intent; value unclear; no schema markup |
| 3-4 | No apparent keyword strategy; poor or missing metadata; content doesn't match search intent; thin or padded; no links |
| 1-2 | No SEO signals; wrong or no metadata; content clearly doesn't match any identifiable search intent |

---

## Pre-Publish SEO Checklist (25 items)

### Technical (5 items)

1. **Canonical tag present** — self-referencing or pointing to the correct canonical URL
2. **Meta title** — 50-60 characters, contains primary keyword, unique across site
3. **Meta description** — 150-160 characters, compelling, contains primary keyword naturally
4. **HTTPS** — page served over HTTPS, no mixed content warnings
5. **Core Web Vitals** — LCP < 2.5s, INP < 200ms, CLS < 0.1 (test with PageSpeed Insights)

### Structured Data (5 items)

6. **Article or relevant schema present** — JSON-LD `@type: Article` with `datePublished`, `dateModified`, `author`, `publisher`
7. **FAQPage schema** — if FAQ section exists on page, FAQPage schema wraps it with `Question`/`Answer` pairs
8. **Organization/Person schema** — site-wide: Organization with `logo`, `sameAs` (social profiles); author pages: Person with credentials
9. **Valid JSON-LD** — tested in Google Rich Results Test, no errors
10. **Dates accurate** — `datePublished` matches visible publication date; `dateModified` matches last substantive update

### E-E-A-T (5 items)

11. **Author identified** — byline visible, links to author bio page
12. **Author credentials** — bio includes qualifications appropriate to topic (formal credentials for YMYL; demonstrated expertise for lifestyle/how-to)
13. **Publication date visible** — date shown on page, not hidden; "Last updated" for evergreen content
14. **Sources cited** — factual claims have inline citations or a sources section; no unsourced statistics
15. **No YMYL claims without expert attribution** — health, finance, legal, safety claims attributed to qualified professionals

### AEO (5 items)

16. **Primary question answered in first 100 words** — the core question the searcher would ask is directly answered early
17. **H2s phrased as questions or clear topics** — heading hierarchy signals what information lives in each section
18. **FAQPage schema present** — if FAQ or Q&A section exists (cross-check with item 7)
19. **Content length matches intent** — not padded beyond what the topic requires; not thin for a complex topic
20. **Extraction zone present** — TL;DR, summary box, or key takeaways section for content > 1,500 words

### GEO (5 items)

21. **BLUF writing** — each major section opens with a direct statement/answer in the first sentence (not a preamble or throat-clearing)
22. **Quantitative claims with sources** — at least one specific data point with attribution per major section (e.g., "43% of buyers..." not "many buyers...")
23. **Organization schema with `sameAs`** — links to Wikipedia/Wikidata, LinkedIn, Crunchbase, Google Business Profile
24. **AI crawlers allowed** — robots.txt does NOT block `GPTBot`, `ClaudeBot`, `PerplexityBot` (check `/robots.txt`)
25. **Original data or third-party citation** — content includes proprietary data, original research, or is cited by third-party publications

---

## Severity Mapping

How checklist failures map to content-critique severity tiers:

| Critical (must fix) | High (fix before publish) | Medium (fix in next update) | Low (nice to have) |
|---------------------|---------------------------|-----------------------------|--------------------|
| YMYL claims without credentials (#15) | No meta description (#3) | FAQPage schema missing despite FAQ section (#7, #18) | Content slightly thin for intent (#19) |
| Keyword stuffing detected | Article schema missing on blog post (#6) | Internal links absent | External links absent |
| Content doesn't match search intent | No author attribution (#11) | BLUF structure missing (#21) | `dateModified` not updated (#10) |
| AI crawlers blocked AND brand wants GEO visibility (#24) | No publication date (#13) | No quantitative claims (#22) | Organization `sameAs` incomplete (#23) |
| | Canonical tag missing or wrong (#1) | No extraction zone on long content (#20) | |

---

## Quick Assessment Protocol

For rapid scoring (when full 25-item audit isn't warranted):

1. Does the first paragraph answer the searcher's question? (AEO + GEO)
2. Is there a meta title with a keyword and a meta description? (Technical)
3. Is the author identified with credentials? (E-E-A-T)
4. Does it have at least one data point with a source? (GEO)
5. Is there Article/FAQ schema in the page source? (Structured Data)

Score: 5/5 = likely 8-10; 3-4/5 = likely 6-8; 0-2/5 = likely below 5.

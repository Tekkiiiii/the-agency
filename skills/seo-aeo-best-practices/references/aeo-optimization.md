# Answer Engine Optimization (AEO)

Optimizing content to be selected as the direct answer on search engine results pages — featured snippets, People Also Ask boxes, voice search responses, knowledge panels, and AI Overviews. Focuses on Google's on-SERP answer surfaces.

**The outcome:** A user searches "how to optimize for AI citations" and your content appears as the featured snippet or in the AI Overview — with or without a click.

---

## Featured Snippets

Google extracts and displays content directly in the SERP above organic results ("Position Zero").

### Snippet types and how to target each:

| Type | Format needed | Example trigger |
|------|---------------|-----------------|
| Paragraph | 40-60 word answer after question-phrased H2 | "What is [term]?" |
| List (ordered) | Numbered `<ol>` with 6-8 items | "How to [do thing]" / "Steps to..." |
| List (unordered) | Bulleted `<ul>` with 6-8 items | "Types of..." / "Best [things] for..." |
| Table | HTML `<table>` with clear headers | "Compare..." / "[thing] vs [thing]" |
| Video | YouTube with timestamps in description | "How to [visual task]" |

### Paragraph snippet formula:
1. Use the target question as an H2 or H3 heading
2. Immediately answer in 40-60 words (one short paragraph)
3. Lead with a definition or direct statement
4. Follow with supporting detail

**Example:**
```
## What is Generative Engine Optimization?

Generative Engine Optimization (GEO) is the practice of optimizing
content to be cited by AI systems like ChatGPT, Perplexity, and
Gemini in their generated responses. Unlike traditional SEO which
targets search rankings, GEO focuses on entity authority, BLUF
writing structure, and quantitative claims that AI models prefer
to extract and cite.
```

### List snippet formula:
1. H2 with "How to..." or "Steps to..." or "Types of..."
2. Immediately follow with ordered/unordered list
3. Keep each item to one line (30-50 characters)
4. Include 6-8 items (Google often truncates and shows "more items")

---

## Extraction Zones

The specific areas on a page where Google (and AI systems) pull snippet content. Optimizing these zones directly impacts selection probability.

### Primary extraction zones:
1. **First 100 words after a question-phrased heading** — highest priority
2. **Definition blocks** — "X is Y" pattern in the first sentence of a section
3. **Summary boxes** — TL;DR, "Key Takeaways," or "In This Article" sections
4. **First paragraph of the page** — for broad topic definitions
5. **Table content** — structured comparisons and data

### Implementation:
- Every H2/H3 section: put the core answer in the first 1-2 sentences
- Use the inverted pyramid: conclusion first, evidence after
- For long content (>1,500 words): add a "Key Takeaways" section near the top
- Each extraction zone should be independently readable without surrounding context

---

## People Also Ask (PAA)

PAA boxes appear in 65%+ of Google searches. Each box expands to show a snippet answer pulled from a web page — high-visibility, high-volume surface.

### Targeting strategy:
1. **Map the question landscape:**
   - Check Google's PAA boxes for your target queries
   - Use AlsoAsked.com for question clustering
   - AnswerThePublic for question variations
   - Google Search Console → Performance → filter by question words (what, how, why, when)

2. **Write one H2 per PAA question:**
   - Use the exact question phrasing as the heading
   - Answer directly in 2-3 sentences immediately after the heading
   - Then expand with supporting detail below

3. **Add FAQPage schema:**
   - Wrap question/answer pairs in FAQPage JSON-LD
   - Answers in schema should be 40-60 words
   - See `structured-data.md` for template

### PAA optimization checklist:
- [ ] Identified all PAA questions for primary topic (minimum 10)
- [ ] Each question has a dedicated H2 or H3 section
- [ ] Direct answer in first 2 sentences after heading
- [ ] FAQPage schema wraps the FAQ section
- [ ] Questions use natural language (not keyword-stuffed)

---

## Voice Search

Voice queries average 29 words (vs 3-4 for typed). They're conversational, question-phrased, and local-heavy.

### Voice search characteristics:
- Question format: "Hey Google, what's the best way to..."
- Local intent: "near me" queries are 3x more likely in voice
- Conversational tone: natural language, complete sentences
- Speed-dependent: voice results bias toward fast-loading pages

### Optimization:
- **Target long-tail question keywords** — match the natural phrasing people use when speaking
- **Answer in conversational language** — the response should sound correct when read aloud
- **FAQPage schema** — voice assistants pull primarily from FAQ and featured snippets
- **Page speed critical** — LCP < 2.5s (voice results prioritize fast pages)
- **Local SEO** — Google Business Profile for location-based voice queries
- **Mobile-first** — voice search happens on mobile; ensure mobile rendering is clean

---

## Knowledge Panels

The information box that appears on the right side of desktop search (or top of mobile) for recognized entities — people, companies, products, places.

### How knowledge panels are triggered:
1. **Entity recognition** — Google's Knowledge Graph identifies your entity
2. **Data sources:** Google Business Profile, Wikipedia/Wikidata, structured data, social profiles, trusted databases (Crunchbase, IMDb, etc.)
3. **Consistency requirement** — information must match across all sources

### Building knowledge panel presence:

**For businesses:**
1. Claim and complete Google Business Profile (name, address, hours, category, photos)
2. Add Organization schema with `sameAs` to all official profiles
3. Ensure LinkedIn company page matches GBP exactly (name, description, address)
4. Get listed in relevant industry directories
5. Aim for Wikipedia entry if meeting notability criteria

**For people/authors:**
1. Person schema on author page with `sameAs`
2. Complete LinkedIn profile (used as data source)
3. Wikipedia entry (if notable: requires significant coverage in independent reliable sources)
4. Wikidata entry (lower bar than Wikipedia — structured data about the entity)
5. Consistent identity across publications, speaking events, social media

### Knowledge panel claim:
Once a panel appears, you can claim it via "Suggest an edit" at the bottom. Google may verify via Search Console, official website, or social profiles.

---

## AI Overviews (formerly SGE)

Google's AI-generated answer that appears at the top of certain SERPs. Active in ~57% of searches as of June 2025.

### What AI Overviews pull from:
- Authoritative sources for the specific query intent
- E-E-A-T signals (experience, credentials, trust markers)
- Structured data (FAQ, HowTo, Article schema)
- Content that directly and concisely answers the query
- Multiple corroborating sources (AI Overviews often cite 3-5 sources)

### Optimization overlap:
AI Overviews optimization is essentially a combination of all other AEO techniques:
- BLUF writing (from GEO) — answer first
- Featured snippet structure — 40-60 word extraction zones
- E-E-A-T signals — authoritative, credentialed sources preferred
- Structured data — schema helps AI systems understand content structure
- Freshness — recent content preferred (85% of citations from last 2 years)

### Zero-click consideration:
AI Overviews may answer the query without generating a click. This is a visibility-vs-traffic tradeoff. For brand awareness queries, being cited in the AI Overview is valuable even without clicks. For conversion queries, evaluate whether the traffic loss outweighs the authority signal.

---

## Zero-Click Metrics

60% of Google searches in 2025 end without a click. Measuring AEO success requires metrics beyond organic traffic.

### What to track:

| Metric | Where to find it | What it tells you |
|--------|-------------------|-------------------|
| Impressions with low CTR | Google Search Console | Likely showing as snippet/AI Overview |
| Featured snippet appearances | Search Console → Search Appearance filter | Direct featured snippet wins |
| PAA appearances | Third-party tools (Ahrefs, Semrush) | PAA box presence |
| Branded search volume | Google Trends, Search Console | Brand awareness from zero-click visibility |
| Knowledge panel accuracy | Manual check | Entity recognition health |
| AI Overview citations | Search Console (when available) | AI Overview inclusion |

### Interpreting zero-click data:
- **High impressions + low CTR** = your content is answering the query without a click (snippet/AI Overview)
- **This is NOT always bad** — brand awareness, authority signal, and trust-building have value
- **When it IS a problem:** conversion-intent queries where you need the click to generate revenue
- **Strategic decision:** some queries are better served by being the answer (awareness); others need the click (conversion)

---

## AEO Content Checklist (15 items)

### Structure (5 items)
1. [ ] Primary question answered in first 100 words of the page
2. [ ] Each H2/H3 addresses a distinct sub-question with a direct answer immediately after
3. [ ] Content uses the exact question phrases searchers use (sourced from PAA, Search Console)
4. [ ] Lists use proper HTML (`<ul>`, `<ol>`) with concise items
5. [ ] Tables use proper HTML `<table>` for comparison/data content

### Schema (4 items)
6. [ ] FAQPage schema present if FAQ section exists
7. [ ] HowTo schema present if step-by-step content
8. [ ] Article schema with `datePublished` and `dateModified`
9. [ ] Organization/Person schema site-wide

### Optimization (4 items)
10. [ ] Extraction zone optimized: 40-60 word answer after question heading
11. [ ] Content length matches intent (not padded, not thin)
12. [ ] Page loads in < 2.5s (LCP) for voice search eligibility
13. [ ] Mobile rendering clean (no layout shifts, no blocked content)

### Measurement (2 items)
14. [ ] Search Console configured with Search Appearance tracking
15. [ ] Branded search volume baseline established for tracking over time

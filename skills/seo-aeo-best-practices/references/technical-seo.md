# Technical SEO

Foundation-level technical optimization for search engines and AI crawlers. Covers metadata, crawlability, site structure signals, and Core Web Vitals.

---

## Title Tags

**Formula:** `Primary Keyword — Secondary Context | Brand Name`

| Rule | Detail |
|------|--------|
| Length | 50-60 characters (Google truncates at ~60) |
| Keyword placement | Primary keyword in first 3-4 words |
| Uniqueness | Every page must have a unique title — no duplicates across site |
| No stuffing | One primary keyword + one modifier maximum |
| Brand | Append brand name at end with pipe separator |

**Examples:**
- Good: `Project Management for Remote Teams | Acme`
- Bad: `Best Project Management Software Tools for Remote Teams Working From Home`

---

## Meta Descriptions

| Rule | Detail |
|------|--------|
| Length | 150-160 characters |
| Contains | Primary keyword (naturally), one secondary keyword, CTA verb |
| Unique | No duplicate meta descriptions across site |
| Compelling | Written for humans — this is ad copy, not keyword soup |
| Matches intent | Description must match what the page actually delivers |

Google rewrites meta descriptions ~70% of the time for featured snippets, but a well-crafted description still influences CTR when shown.

---

## Open Graph & Twitter Cards

Required tags for social sharing and AI browse previews (ChatGPT Browse, Perplexity both pull OG data):

```html
<!-- Open Graph -->
<meta property="og:title" content="Page Title" />
<meta property="og:description" content="Compelling description" />
<meta property="og:image" content="https://example.com/image.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:type" content="article" />
<meta property="og:url" content="https://example.com/page" />
<meta property="og:site_name" content="Brand Name" />

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Page Title" />
<meta name="twitter:description" content="Description" />
<meta name="twitter:image" content="https://example.com/image.jpg" />
```

Image specifications: 1200x630px minimum, 8MB max, JPG/PNG/WebP.

---

## Canonical Tags

| Scenario | Implementation |
|----------|----------------|
| Single URL page | Self-referencing canonical: `<link rel="canonical" href="https://example.com/page" />` |
| Content syndicated to other domains | Point canonical back to original |
| Paginated content | Each page self-canonicalizes OR all pages canonical to page 1 (depends on strategy) |
| HTTP/HTTPS variants | HTTPS version is canonical |
| Trailing slash | Pick one convention, canonical to it consistently |
| URL parameters (tracking, filters) | Canonical to clean URL without parameters |
| www vs non-www | Pick one, canonical + 301 redirect the other |

**Common error:** Missing canonical = Google picks one for you, often wrong.

---

## hreflang (International SEO)

Implementation methods (choose one):

| Method | When to use |
|--------|-------------|
| HTML `<link>` in `<head>` | Sites with < 50 language/region variants |
| XML sitemap | Large sites with many variants |
| HTTP header | Non-HTML files (PDFs) |

```html
<link rel="alternate" hreflang="en-us" href="https://example.com/page" />
<link rel="alternate" hreflang="vi-vn" href="https://example.com/vi/page" />
<link rel="alternate" hreflang="x-default" href="https://example.com/page" />
```

**Critical rules:**
- Bidirectional: if page A points to page B with hreflang, page B MUST point back to A
- `x-default` required: fallback for unmatched regions
- Language codes: ISO 639-1 (`en`, `vi`, `fr`) + optional ISO 3166-1 region (`us`, `vn`)
- Self-referencing: every page includes its own hreflang entry

**Common errors:** Missing return tags (most frequent), wrong locale codes (`en-UK` should be `en-GB`), pointing to redirecting URLs.

---

## Sitemaps

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page</loc>
    <lastmod>2026-05-01</lastmod>
    <changefreq>weekly</changefreq>
  </url>
</urlset>
```

| Rule | Detail |
|------|--------|
| `<lastmod>` accuracy | Must reflect actual content changes — Google uses this as a freshness signal. Fake dates = ignored |
| `<priority>` | Largely ignored by Google — don't spend time optimizing it |
| Max URLs | 50,000 per sitemap file; use sitemap index for larger sites |
| Submit | Google Search Console + Bing Webmaster Tools |
| Reference in robots.txt | `Sitemap: https://example.com/sitemap.xml` |
| Exclude | noindex pages, redirect targets, error pages, duplicate content |

---

## robots.txt

```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /tmp/

# AI Crawlers (allow for GEO visibility)
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: https://example.com/sitemap.xml
```

**Key rules:**
- `Disallow` prevents crawling but NOT indexing (pages can still appear in search if linked externally)
- To prevent indexing: use `<meta name="robots" content="noindex">` on the page
- `Crawl-delay`: Google ignores it; set it only for other crawlers that respect it
- AI crawler decisions: see `geo-optimization.md` for the full decision framework
- NEVER block `Googlebot` — kills all Google visibility including AI Overviews

---

## Crawl Budget

**When it matters:** Sites with 10,000+ pages, sites with significant duplicate content, sites with slow server response times.

**Optimization:**
- Keep priority pages within 3 clicks of homepage
- Remove/noindex thin content, duplicate content, and parameter variations
- Fix crawl errors (4xx, 5xx) that waste crawl budget
- Improve server response time (TTFB < 200ms ideal)
- Use internal linking to signal page importance
- Monitor in Google Search Console → Settings → Crawl Stats

**For AI crawlers:** Flat architecture (fewer redirect hops) improves AI crawler efficiency. Main content must be in HTML — AI crawlers often skip JavaScript-rendered content.

---

## Core Web Vitals (2025-2026)

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5-4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | 200-500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1-0.25 | > 0.25 |

**Ranking impact:** Confirmed ranking signal. Pages at position 1 are 10% more likely to pass CWV than pages at position 9. In competitive niches, failing CWV is a structural disadvantage.

**Measurement:**
- **Field data** (what Google uses): Chrome UX Report (CrUX), Search Console CWV report
- **Lab data** (for debugging): PageSpeed Insights, Lighthouse, WebPageTest

**Common fixes:**
- LCP: optimize largest image (lazy-load below fold, preload above fold), reduce server response time
- INP: minimize main thread blocking, break up long tasks, use `requestIdleCallback`
- CLS: set explicit dimensions on images/embeds, avoid injecting content above existing content

---

## Technical SEO Pre-Launch Checklist (20 items)

### Critical (blocks launch)
1. [ ] HTTPS active, no mixed content
2. [ ] Canonical tags on all pages (self-referencing or pointing to correct URL)
3. [ ] Meta titles present and unique (50-60 chars)
4. [ ] robots.txt allows Googlebot on all public pages
5. [ ] XML sitemap submitted to Search Console
6. [ ] No accidental noindex on important pages
7. [ ] 301 redirects in place for any URL changes

### High (fix within first week)
8. [ ] Meta descriptions on all key pages (150-160 chars)
9. [ ] Open Graph tags on all pages (title, description, image)
10. [ ] Core Web Vitals passing in field data
11. [ ] Mobile responsive (mobile-first indexing is default)
12. [ ] Structured data present (Article, Organization minimum)
13. [ ] Internal linking structure (no orphan pages, 3-click depth)
14. [ ] AI crawlers allowed in robots.txt (GPTBot, ClaudeBot, PerplexityBot)

### Medium (fix within first month)
15. [ ] hreflang tags (if multilingual)
16. [ ] Pagination handled (rel=next/prev or canonical to page 1)
17. [ ] URL structure clean (short, descriptive, no parameters)
18. [ ] Image alt text present on all meaningful images
19. [ ] 404 page exists and is helpful (not generic server error)
20. [ ] Page speed: TTFB < 200ms, total page weight < 3MB

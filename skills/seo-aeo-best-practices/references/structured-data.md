# Structured Data (JSON-LD)

Schema markup implementation for search engines and AI systems. JSON-LD is Google's preferred format — decoupled from HTML, easier to maintain, supports nesting.

Structured data serves dual purpose: rich results in traditional search AND higher AI citation rates (30-40% visibility boost). LLMs grounded in structured data achieve 300% higher accuracy versus unstructured data.

---

## Article Schema

For blog posts, news articles, and editorial content.

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How to Optimize Content for AI Citations in 2026",
  "description": "A comprehensive guide to GEO optimization...",
  "image": "https://example.com/images/geo-guide.jpg",
  "author": {
    "@type": "Person",
    "name": "Author Name",
    "url": "https://example.com/about/author-name",
    "sameAs": [
      "https://linkedin.com/in/author-name",
      "https://twitter.com/author_handle"
    ]
  },
  "publisher": {
    "@type": "Organization",
    "name": "Brand Name",
    "logo": {
      "@type": "ImageObject",
      "url": "https://example.com/logo.png"
    }
  },
  "datePublished": "2026-05-01T09:00:00+07:00",
  "dateModified": "2026-05-03T14:00:00+07:00",
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://example.com/geo-guide"
  }
}
```

**Required for rich results:** `headline`, `image`, `datePublished`, `author.name`
**Recommended:** `dateModified`, `publisher`, `description`, `author.url`

---

## FAQPage Schema

For FAQ sections. Feeds People Also Ask boxes and voice responses. Google surfaces 2-3 FAQs from the page.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is Generative Engine Optimization?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Generative Engine Optimization (GEO) is the practice of optimizing content to be cited by AI systems like ChatGPT, Perplexity, and Gemini in their responses. It focuses on entity authority, BLUF writing, and quantitative claims."
      }
    },
    {
      "@type": "Question",
      "name": "How long does GEO take to show results?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "GEO visibility typically takes 6-12 months to build through consistent content investment, entity authority building, and digital PR. Some real-time retrieval citations can appear within weeks."
      }
    }
  ]
}
```

**Best practices:**
- Answers should be 40-60 words (extraction-zone optimized)
- 5-8 FAQ pairs per page maximum
- Questions must appear verbatim on the visible page (Google penalizes hidden FAQ)
- Use questions your audience actually asks (source from PAA, AnswerThePublic, Search Console)

---

## HowTo Schema

For step-by-step instructional content. Triggers rich results with step previews.

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to Set Up robots.txt for AI Crawlers",
  "description": "Configure your robots.txt to allow AI systems to cite your content.",
  "totalTime": "PT10M",
  "estimatedCost": {
    "@type": "MonetaryAmount",
    "currency": "USD",
    "value": "0"
  },
  "step": [
    {
      "@type": "HowToStep",
      "name": "Access robots.txt",
      "text": "Open your robots.txt file at the root of your domain.",
      "url": "https://example.com/guide#step1",
      "image": "https://example.com/images/step1.jpg"
    },
    {
      "@type": "HowToStep",
      "name": "Add AI crawler directives",
      "text": "Add User-agent entries for GPTBot, ClaudeBot, and PerplexityBot with Allow: / directives.",
      "url": "https://example.com/guide#step2",
      "image": "https://example.com/images/step2.jpg"
    }
  ],
  "tool": [
    {
      "@type": "HowToTool",
      "name": "Text editor or CMS admin panel"
    }
  ]
}
```

**When to use HowTo vs FAQPage:**
- HowTo: sequential steps to accomplish a task
- FAQPage: independent questions with standalone answers

---

## QAPage Schema

For community Q&A content (forums, Stack Overflow-style). Different from FAQPage — one question with one accepted answer.

```json
{
  "@context": "https://schema.org",
  "@type": "QAPage",
  "mainEntity": {
    "@type": "Question",
    "name": "How do I check if AI crawlers can access my site?",
    "text": "I want to verify that ChatGPT and Perplexity can crawl my content...",
    "answerCount": 3,
    "upvoteCount": 42,
    "dateCreated": "2026-04-15T10:00:00+07:00",
    "author": {
      "@type": "Person",
      "name": "Community Member"
    },
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Use Google's robots.txt tester or fetch your robots.txt directly...",
      "upvoteCount": 28,
      "dateCreated": "2026-04-15T12:30:00+07:00",
      "author": {
        "@type": "Person",
        "name": "Expert Contributor"
      }
    }
  }
}
```

---

## Organization Schema

Site-wide schema for the entity behind the website. Critical for GEO — the `sameAs` array is the primary entity authority signal.

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Brand Name",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "description": "One-sentence description of what the organization does.",
  "foundingDate": "2020-01-15",
  "sameAs": [
    "https://www.linkedin.com/company/brand-name",
    "https://twitter.com/brand_name",
    "https://www.facebook.com/brandname",
    "https://www.youtube.com/@brandname",
    "https://github.com/brand-name",
    "https://www.crunchbase.com/organization/brand-name",
    "https://en.wikipedia.org/wiki/Brand_Name",
    "https://www.wikidata.org/wiki/Q12345678"
  ],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+1-555-123-4567",
    "contactType": "customer service",
    "availableLanguage": ["English", "Vietnamese"]
  },
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "Ho Chi Minh City",
    "addressCountry": "VN"
  }
}
```

**GEO-critical fields:** `sameAs` (link to ALL official profiles, especially Wikipedia/Wikidata), `name` (must match exactly across all platforms), `description` (consistent with how you describe yourself everywhere).

---

## Person Schema

For author pages. Builds E-E-A-T signals and GEO entity authority for individual experts.

```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "Author Full Name",
  "url": "https://example.com/about/author-name",
  "image": "https://example.com/images/author.jpg",
  "jobTitle": "Senior Marketing Strategist",
  "worksFor": {
    "@type": "Organization",
    "name": "Brand Name",
    "url": "https://example.com"
  },
  "sameAs": [
    "https://linkedin.com/in/author-name",
    "https://twitter.com/author_handle",
    "https://scholar.google.com/citations?user=XXXXX"
  ],
  "alumniOf": {
    "@type": "CollegeOrUniversity",
    "name": "University Name"
  },
  "knowsAbout": ["SEO", "Content Marketing", "AI Optimization"]
}
```

---

## Product Schema

For product pages. Triggers star ratings, price, and availability in search results.

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product Name",
  "image": "https://example.com/product.jpg",
  "description": "Product description",
  "brand": {
    "@type": "Brand",
    "name": "Brand Name"
  },
  "offers": {
    "@type": "Offer",
    "price": "99.00",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "url": "https://example.com/product"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.7",
    "reviewCount": "234"
  },
  "review": {
    "@type": "Review",
    "reviewRating": {
      "@type": "Rating",
      "ratingValue": "5"
    },
    "author": {
      "@type": "Person",
      "name": "Reviewer Name"
    },
    "reviewBody": "Excellent product..."
  }
}
```

**Note:** `aggregateRating` triggers star snippets in SERPs — high visual CTR impact.

---

## Breadcrumb Schema

Signals site hierarchy to search engines. Appears as path navigation in SERPs.

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://example.com"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Blog",
      "item": "https://example.com/blog"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "SEO Guide",
      "item": "https://example.com/blog/seo-guide"
    }
  ]
}
```

---

## Event Schema

For webinars, conferences, product launches.

```json
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "GEO Optimization Workshop",
  "startDate": "2026-06-15T09:00:00+07:00",
  "endDate": "2026-06-15T12:00:00+07:00",
  "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
  "eventStatus": "https://schema.org/EventScheduled",
  "location": {
    "@type": "VirtualLocation",
    "url": "https://example.com/webinar"
  },
  "organizer": {
    "@type": "Organization",
    "name": "Brand Name",
    "url": "https://example.com"
  },
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "url": "https://example.com/webinar/register"
  }
}
```

---

## Validation & Testing

| Tool | URL | Purpose |
|------|-----|---------|
| Google Rich Results Test | search.google.com/test/rich-results | Validates eligibility for rich results |
| Schema.org Validator | validator.schema.org | Validates against schema.org spec |
| Google Search Console | search.google.com/search-console | Shows which rich results are active |

**Testing workflow:**
1. Add schema to page
2. Test with Rich Results Test (catches Google-specific issues)
3. Validate with Schema.org Validator (catches spec violations)
4. Deploy and monitor in Search Console → Enhancements

---

## Common Errors

| Error | Impact | Fix |
|-------|--------|-----|
| Missing `@context` | Schema ignored entirely | Always include `"@context": "https://schema.org"` |
| Wrong date format | Rich results ineligible | Use ISO 8601: `2026-05-01T09:00:00+07:00` |
| Mismatched content | Manual action risk | Schema claims must match visible page content exactly |
| Missing required fields | Rich results don't trigger | Check requirements per type in Rich Results Test |
| Duplicate schema types | Confuses parsers | One instance per type per page (exception: multiple Product on category pages) |
| `sameAs` pointing to dead URLs | Weakens entity signal | Audit quarterly — remove broken links |
| FAQPage with hidden content | Policy violation | FAQ questions and answers must be visible on page |

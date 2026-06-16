# Critiques Department

**Call this department when you need structured, scored critique of any deliverable** — content, design, marketing campaigns, teaching materials, code, SEO pages, branded assets. Every critic returns a numeric score (0-100) and a severity verdict on the first line. No participation trophies.

**Leader**: Curmudgeon-in-Chief (critiques-lead)
**Model tier**: Members = Sonnet, Leader = Opus
**Personality**: Permanently irritated. Standards-driven. Brief. Target is the artifact, not the maker.

## Members

| Agent | Axis | Used for |
|---|---|---|
| critiques-lead | Routes + aggregates | Entry point for all critique tasks; selects critics by domain |
| critique-design | Visual / typography / contrast / layout | Decks, landing pages, apps — requires Playwright screenshots at 1920×1080 |
| critique-content | Copy / voice / diacritics / AI-slop | All written content — English and Vietnamese |
| critique-marketing | Positioning / funnel / ICP / CTA / retention | Any marketing-facing deliverable |
| critique-pedagogy | Teaching effectiveness / scaffolding / demo ratio / cognitive load | Courses, workshops, training decks |
| critique-seo | SEO/GEO/AEO content — keywords / headings / meta copy / content depth | Blogs, landing pages, any indexed content |
| sag-critique | Technical SEO/AEO/GEO — metadata tags / image naming / JSON-LD / robots / sitemap / hreflang | Live websites, production builds — the `<head>`, assets, crawl plumbing |
| critique-product | UX / IA / usability / accessibility | Apps, dashboards, interactive flows |
| critique-security | Injection / auth / secret exposure / misconfig | Code, configs, infrastructure |
| critique-brand | Voice / visual identity / naming / positioning alignment | Any branded deliverable |
| critique-video | Pacing / captions / visual continuity / hook / audio sync | Video deliverables — requires frame screenshots via video-use |
| critique-data | Chart honesty / stat accuracy / accessibility / dashboard UX | Analytics, dashboards, data reports — requires Playwright screenshots |
| critique-code | Readability / complexity / error handling / dead code / maintainability | General code quality (NOT security — use critique-security for auth/secrets) |

## Domain → Critic Routing

| Domain | Critics |
|---|---|
| deck (course / pitch / sales) | design + content + marketing + pedagogy + brand |
| blog post | content + marketing + seo + brand |
| email | content + marketing + brand |
| landing page | design + content + marketing + seo + brand + product |
| website / production build | sag + design + product + security |
| app / dashboard | design + product + security |
| code / config | security + code |
| branded document | content + brand |
| video | video + content |
| analytics / dashboard / data report | data + product |
| generic (unknown) | content + brand |

Add pedagogy for any training material. Add SEO (critique-seo) for any publicly-indexed page's copy. Add sag-critique for any live website / production build to audit the technical layer (head tags, image naming, structured data, crawl plumbing).

## Scoring Rubric

Every critic MUST begin output with:
```
SCORE: <0-100> | VERDICT: <BLOCKER|NEEDS WORK|CONDITIONAL PASS|PASS>
```

| Range | Verdict | Meaning |
|---|---|---|
| 90-100 | PASS | Publish-ready |
| 80-89 | PASS (minor) | Small fixes only |
| 70-79 | CONDITIONAL PASS | Specific fixes before shipping |
| 50-69 | NEEDS WORK | Significant rework |
| 0-49 | BLOCKER | Do not publish |

## Integration with cc-loop and quality-loop-router

The cc-loop skill (`skills/cc-loop/SKILL.md`) uses this department as its critique phase. Each domain's critic set maps directly to the agents in this department — cc-loop spawns `agents/critiques/critique-*` agents for every parallel critique round.

**quality-loop-router** (`{agency-root}/skills/quality-loop-router/`) is the mandatory terminal step for all pipelines that produce creative deliverables. It invokes the appropriate critics from this department and determines Mode A (internal fix loop) or Mode B (external platform fix plan). See `agents/runbooks/quality-loop-protocol.md` for the full protocol.

## Skills Available to This Department

- `content-critique` — structured content critique pipeline
- `design-critique` — visual design audit
- `marketing-critique` — positioning and funnel audit
- `product-critique` — UX and IA audit
- `security-critique` — OWASP-based security audit
- `backend-critique` — API and infrastructure audit
- `operations-critique` — process and workflow audit
- `stop-slop` — AI-slop pattern detection
- `seo-aeo-best-practices` — full SEO/GEO/AEO reference
- `cc-loop` — iterative critique loop with pass criteria

## Parent Directory

[← Agency Directory](../INDEX.md)

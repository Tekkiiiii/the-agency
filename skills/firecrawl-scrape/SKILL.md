# Firecrawl — Scrape

Scrape one or more URLs. Returns clean, LLM-optimized markdown. Multiple URLs are scraped concurrently.

## When to Apply

- You have a specific URL and want its content
- The page is static or JS-rendered (SPA)
- Step 2 in escalation pattern: search → scrape → map → crawl → browser

## Quick Start

```bash
# Basic markdown extraction
firecrawl scrape "<url>" -o .firecrawl/page.md

# Main content only, no nav/footer
firecrawl scrape "<url>" --only-main-content -o .firecrawl/page.md

# Wait for JS to render, then scrape
firecrawl scrape "<url>" --wait-for 3000 -o .firecrawl/page.md

# Multiple URLs (concurrent)
firecrawl scrape https://example.com https://example.com/blog

# Get markdown and links together
firecrawl scrape "<url>" --format markdown,links -o .firecrawl/page.json

# Ask a targeted question (costs 5 extra credits)
firecrawl scrape "https://example.com/pricing" --query "What is the enterprise plan price?"
```

## Options

| Option | Description |
|--------|-------------|
| `-f, --format <formats>` | Output: markdown, html, rawHtml, links, screenshot, json |
| `-Q, --query <prompt>` | Ask a question about page content (5 credits) |
| `-H` | Include HTTP headers |
| `--only-main-content` | Strip nav, footer, sidebar |
| `--wait-for <ms>` | Wait for JS rendering before scraping |
| `--include-tags <tags>` | Only include these HTML tags |
| `--exclude-tags <tags>` | Exclude these HTML tags |
| `-o, --output <path>` | Output file path |

## Tips

- **Prefer plain scrape over `--query`.** Scrape to a file, then grep/head/read the markdown — cheaper and more flexible.
- **Try scrape before browser.** Handles static pages and SPAs. Only escalate to browser for interactions (clicks, forms, pagination).
- **Multiple URLs run concurrently** — check `firecrawl --status` for concurrency limit.
- **Always quote URLs** — `?` and `&` are shell special characters.
- Naming convention: `.firecrawl/{site}-{path}.md`

## Related Skills

- `firecrawl-search` — find pages when you don't have a URL
- `firecrawl-browser` — when scrape can't get the content (interaction needed)
- `firecrawl-download` — bulk download an entire site to local files

---

**Source:** https://officialskills.sh/firecrawl/skills/firecrawl-scrape
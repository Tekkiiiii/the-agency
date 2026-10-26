# Firecrawl — Crawl

Bulk extract content from a website. Crawls pages following links up to a depth/limit.

## When to Apply

- Need content from many pages on a site (e.g. all `/docs/`)
- Want to extract an entire site section
- Step 4 in escalation pattern: search → scrape → map → crawl → browser

## Quick Start

```bash
# Crawl a docs section
firecrawl crawl "<url>" --include-paths /docs --limit 50 --wait -o .firecrawl/crawl.json

# Full crawl with depth limit
firecrawl crawl "<url>" --max-depth 3 --wait --progress -o .firecrawl/crawl.json

# Check status of a running crawl
firecrawl crawl <job-id>
```

## Options

| Option | Description |
|--------|-------------|
| `--wait` | Wait for crawl to complete |
| `--progress` | Show progress while waiting |
| `--limit <n>` | Max pages to crawl |
| `--max-depth <n>` | Max link depth to follow |
| `--include-paths <paths>` | Only crawl URLs matching these paths |
| `--exclude-paths <paths>` | Skip URLs matching these paths |
| `--delay <ms>` | Delay between requests |
| `--max-concurrency <n>` | Max parallel crawl workers |
| `--pretty` | Pretty print JSON output |
| `-o, --output <path>` | Output file path |

## Tips

- **Always use `--wait`** when you need results immediately. Without it, returns a job ID for async polling.
- **Use `--include-paths`** to scope the crawl — don't crawl an entire site when you only need one section.
- Crawl consumes credits per page. Check `firecrawl credit-usage` before large crawls.

## Related Skills

- `firecrawl-scrape` — scrape individual pages
- `firecrawl-map` — discover URLs before deciding to crawl
- `firecrawl-download` — download site to local files (uses map + scrape)

---

**Source:** https://officialskills.sh/firecrawl/skills/firecrawl-crawl
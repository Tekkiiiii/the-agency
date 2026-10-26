# Firecrawl — Agent (Autonomous AI Extraction)

AI-powered autonomous extraction. The agent navigates sites and extracts structured data (takes 2–5 minutes).

## When to Apply

- Need structured data from complex multi-page sites
- Manual scraping would require navigating many pages
- Want the AI to figure out where the data lives
- Extracting pricing tiers, product catalogs, feature lists, research data

## Quick Start

```bash
# Extract structured data
firecrawl agent "extract all pricing tiers" --wait -o .firecrawl/pricing.json

# With a JSON schema for structured output
firecrawl agent "extract products" \
  --schema '{"type":"object","properties":{"name":{"type":"string"},"price":{"type":"number"}}}' \
  --wait -o .firecrawl/products.json

# Focus on specific pages
firecrawl agent "get feature list" --urls "<url>" --wait -o .firecrawl/features.json
```

## Options

| Option | Description |
|--------|-------------|
| `--urls <urls>` | Starting URLs for the agent |
| `--model <model>` | `spark-1-mini` or `spark-1-pro` |
| `--schema <json>` | JSON schema for structured output |
| `--schema-file <path>` | Path to JSON schema file |
| `--max-credits <n>` | Credit limit for this agent run |
| `--wait` | Wait for agent to complete |
| `--pretty` | Pretty print JSON output |
| `-o, --output <path>` | Output file path |

## Tips

- **Always use `--wait`** to get results inline. Without it, returns a job ID.
- **Use `--schema`** for predictable, structured output — otherwise the agent returns freeform data.
- Agent runs consume more credits than simple scrapes. Use `--max-credits` to cap spending.
- For simple single-page extraction, prefer `scrape` — it's faster and cheaper.

## Related Skills

- `firecrawl-scrape` — simpler single-page extraction
- `firecrawl-crawl` — bulk extraction without AI

---

**Source:** https://officialskills.sh/firecrawl/skills/firecrawl-agent
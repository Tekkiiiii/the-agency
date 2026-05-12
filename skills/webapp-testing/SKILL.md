# Web Application Testing

To test local web applications, write native Python Playwright scripts.

## Helper Scripts Available

`scripts/with_server.py` — Manages server lifecycle (supports multiple servers).

**Always run scripts with `--help` first** to see usage. DO NOT read the source until you try running the script first and find that a customized solution is absolutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.

## Decision Tree: Choosing Your Approach

**User task → Is it static HTML?**
- **Yes** → Read HTML file directly to identify selectors
  - Success → Write Playwright script using selectors
  - Fails/Incomplete → Treat as dynamic (below)
- **No (dynamic webapp)** → Is the server already running?
  - **No** → Run `python scripts/with_server.py --help` then use the helper + write Playwright script
  - **Yes** → Reconnaissance-then-action: navigate → wait → inspect → discover selectors → execute

## Example: Using with_server.py

**Single server:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

**Automation script (servers managed automatically):**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # Always headless
    page = browser.new_page()
    page.goto('http://localhost:5173')  # Server already running
    page.wait_for_load_state('networkidle')  # CRITICAL: wait for JS
    # ... your automation logic
    browser.close()
```

## Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM:**
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```
2. **Identify selectors** from inspection results
3. **Execute actions** using discovered selectors

## Common Pitfall

- ❌ Don't inspect the DOM before `wait_for_load_state('networkidle')` on dynamic apps
- ✅ Do wait for networkidle before inspection

## Best Practices

- Use bundled scripts as **black boxes** — call them directly, don't read the source
- Use `sync_playwright()` for synchronous scripts
- Always close the browser when done
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Add appropriate waits: `page.wait_for_selector()` or `page.wait_for_timeout()`

## Reference Files

- `examples/` — Common patterns:
  - `element_discovery.py` — Discovering buttons, links, inputs on a page
  - `static_html_automation.py` — Using `file://` URLs for local HTML
  - `console_logging.py` — Capturing console logs during automation

---

**Source:** https://officialskills.sh/anthropics/skills/webapp-testing
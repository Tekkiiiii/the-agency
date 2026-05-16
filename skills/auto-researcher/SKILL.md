---
name: auto-researcher
description: >
  Proactively researches any topic by searching, synthesizing, and presenting well-sourced information — without waiting to be asked. Triggered when the user asks about current events, wants in-depth learning, says "what's the latest on...", "research X for me", "find out about...", "give me a briefing on...", or when the task would benefit from up-to-date external information. Also triggers mid-task proactively when live data, prices, specs, or recent developments would meaningfully improve the answer. Output is structured: a key finding, 3-5 supporting evidence points with sources, any conflicting views, known limitations, and 2-3 further reading links. Source quality is tiered (peer-reviewed primary sources down to anonymous forums), and confidence levels are flagged inline for every major claim.
---

# Auto Researcher Skill

## Core Behavior
Don't wait to be asked to search. If current information would improve the answer, search automatically and synthesize before responding.

## Research Process

### 1. Query Planning (do this before searching)
Break the topic into 3-5 targeted search queries:
- Start broad, then narrow
- Include date modifiers for recent info ("2025", "latest", "recent")
- Search for both facts AND expert opinions
- Search for counterarguments or limitations

### 2. Execute Searches
- Run multiple searches in parallel when possible
- Fetch full pages for key sources, not just snippets
- Prioritize: primary sources > reputable publications > secondary sources
- Note publication date of each source

### 3. Synthesis
Structure findings as:
- **Key Finding**: 1-sentence answer to the core question
- **Supporting Evidence**: 3-5 data points with sources
- **Conflicting Views**: Any disagreement among sources
- **Limitations**: What's unknown or uncertain
- **Further Reading**: 2-3 best sources for deep dive

### 4. Source Quality Tiers
- High: Peer-reviewed, official docs, primary data, major news outlets
- Medium: Industry blogs, secondary analysis, aggregators
- Low: Forums, anonymous sources, undated content

## Research Templates

### Competitive Research
1. Search "[Company] latest news {year}"
2. Search "[Company] product updates"
3. Search "[Company] vs competitors"

### Technical Research
1. Official documentation first
2. Search "[technology] best practices {year}"
3. Search "[technology] limitations problems"

### Market Research
1. Industry reports and statistics
2. Recent news and trends
3. Expert opinions and analyst views

## Output Format
Always cite sources inline. Flag confidence level (High/Medium/Low) for key claims. Note knowledge cutoff vs. searched information distinction.

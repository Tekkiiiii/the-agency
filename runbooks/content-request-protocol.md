# Content Request Protocol

How content gets produced in The Agency. This protocol governs the handoff between any requester (PD, department lead, parent AI) and the Content Creation department, with Marketing providing the strategic layer.

## The Flow

```
Requester (PD / Dept Lead / Parent AI)
       │
       ▼
Marketing Lead (builds strategic brief)
       │
       ▼
Chief Content Officer (receives brief, routes to writer)
       │
       ▼
Content Director (assigns, reviews, quality gates)
       │
       ├──► Format-specific Writer (drafts content)
       │         │
       │         └──► Content Editor (polish pass)
       │
       ▼
CCO approves → delivers back to Marketing Lead
       │
       ▼
Marketing Lead (publishes, distributes, measures)
       │
       ▼
Marketing feeds performance data back to CCO (optimization loop)
```

## Step-by-Step

### Step 1 — Requester Sends Resource Request to Marketing Lead

The requester does NOT go to Content Creation directly. Marketing owns the strategy layer, so the request starts there.

```
TO: marketing-lead
TYPE: resource_request
DEPARTMENT: [requester's project/dept]
PRIORITY: [low | medium | high | critical]
---
[What content is needed, rough topic, target audience, and timeline]
```

The request can be brief. Marketing will flesh it out into a full strategic brief.

**Exception:** If the parent AI (council chair) is orchestrating directly, they can send the request to the CCO with a strategic brief already attached — bypassing Marketing only when the strategy is already defined.

### Step 2 — Marketing Lead Builds the Strategic Brief

Marketing fills in the full strategic context. The brief must include all 6 fields:

```
STRATEGIC BRIEF
───────────────
Project:      [project name]
Content type: [blog post | social post | ad copy | email | video script | etc.]
Pillar:       [which content pillar this falls under]

WHO (audience):
- Target segment, persona, buyer stage (TOFU/MOFU/BOFU)
- Pain points and motivations
- What they already know vs. what they need to learn

WHAT (topic & angle):
- Topic and key messages
- Hook formula or angle (if applicable)
- Differentiator or unique perspective

WHERE (distribution):
- Primary channel/platform
- Secondary repurposing targets (separate requests for each)

WHEN:
- Draft deadline
- Publish date
- Campaign timeline (if part of a larger campaign)

WHY (objective & KPI):
- Business objective (awareness, leads, conversions, engagement)
- Success metric and target
- How this fits the broader campaign or content strategy

BRAND CONTEXT:
- Voice and tone guidelines
- CTA convention
- Reference to brand-guidelines.md file path
- Any specific constraints or requirements
```

### Step 3 — Marketing Lead Sends Brief to CCO

```
TO: content-creation-lead
TYPE: coordination_request
DEPARTMENT: marketing
PRIORITY: [matches the original request priority]
---
Strategic brief attached for [project] [content type].
[Any additional context or urgency notes]
```

### Step 4 — CCO Routes to the Right Writer

The CCO (or Content Director, if delegated) reads the brief and assigns to the correct format specialist:

| Content type | Assign to |
|---|---|
| Blog post, article, thought leadership | Blog & Article Writer |
| Case study, whitepaper, report | Case Study & Whitepaper Writer |
| Newsletter, editorial | Newsletter & Editorial Writer |
| LinkedIn post | LinkedIn Writer |
| Twitter/X thread | Twitter/X Writer |
| Instagram caption | Instagram Writer |
| TikTok caption/copy | TikTok Writer |
| Reddit post | Reddit Writer |
| Threads post | Threads Writer |
| Facebook post | Facebook Writer |
| Discord announcement | Discord Writer |
| YouTube title/description | YouTube Writer |
| Pinterest pin copy | Pinterest Writer |
| Quora answer | Quora Writer |
| Telegram channel post | Telegram Writer |
| Ad copy (Meta/Google/TikTok) | Ad Copywriter |
| Landing page / sales page | Landing Page Copywriter |
| Email campaign / sequence | Email Campaign Writer |
| Video script | Video Script Writer |
| Developer docs, API refs, tutorials | Technical Writer (Content) |
| Slide deck / pitch deck | Presentation Creator |
| Press release, media kit | Press & PR Writer |

The CCO attaches:
- The strategic brief from Marketing
- The brand guidelines file path
- Any additional editorial direction

### Step 5 — Writer Produces the Draft

The assigned writer:
1. Reads the strategic brief and brand guidelines
2. Researches the topic (competing content, data points, angles)
3. Creates an outline (for long-form) or drafts directly (for short-form)
4. Writes the full piece in the brand's voice
5. Runs a self-check (stop-slop scan + proofreader pass)
6. Submits to the Content Director

### Step 6 — Content Director Reviews (Quality Gate)

The Content Director runs mandatory quality gates:

| Gate | Tool | Requirement |
|---|---|---|
| Content critique | `content-critique` | Grade B or above |
| AI-slop detection | `stop-slop` | Zero flags |
| Humanizing | `humanizer` | Clean pass |
| Proofreading | `proofreader` | No errors |
| Brand voice | Manual check vs `brand-guidelines.md` | Consistent |

**If the post fails any gate:** Content Director returns it to the writer with specific, actionable editorial notes. The writer revises and resubmits.

**If the post passes all gates:** Content Director approves (Tier 1 authority) and forwards to CCO for final sign-off.

### Step 7 — CCO Approves

- **Standard content** (blog posts, social, email): Content Director's approval is sufficient. CCO reviews only if flagged.
- **High-stakes content** (press releases, content with legal/financial/medical claims, crisis communications): CCO reviews personally before release.

### Step 8 — CCO Delivers Back to Marketing Lead

```
TO: marketing-lead
TYPE: status_report
DEPARTMENT: content-creation
PRIORITY: [matches original]
---
[Content type] for [project] delivered.
- Quality gate: [grade, slop status, polish status]
- File: [output file path]
- SEO notes: [keyword suggestions, internal linking recommendations]
- A/B suggestion: [variant ideas for testing, if applicable]

Ready for your distribution decision.
```

### Step 9 — Marketing Lead Distributes

Marketing owns publishing and distribution:
1. Reviews the artifact for strategic alignment (does it match the brief?)
2. Publishes to the target channel
3. Optionally sends follow-up requests to Content Creation for repurposed versions on other platforms

### Step 10 — Marketing Feeds Back Results

After the measurement window (typically 7-14 days), Marketing shares performance data:

```
TO: content-creation-lead
TYPE: status_report
DEPARTMENT: marketing
---
Performance data for [content piece]:
- [Key metrics: views, engagement, CTR, conversions, DMs, etc.]
- [Top insight: what resonated, what didn't]
- [Recommendation: follow-up pieces, angle adjustments]
```

The CCO uses this data to:
- Brief writers with concrete "this worked / this didn't" feedback
- Adjust voice, format, and messaging for future content
- Identify which content types and angles drive the best results

## Turnaround Times

| Content type | Expected turnaround |
|---|---|
| Social media post (single platform) | Same day |
| Blog post (1,000-2,000 words) | 1-2 days |
| Case study / whitepaper | 3-5 days |
| Email sequence (3-5 emails) | 2-3 days |
| Video script (short-form) | Same day |
| Video script (long-form) | 1-2 days |
| Press release | 1-2 days |
| Slide deck | 2-3 days |

These are production times after the strategic brief is received. Marketing's brief-building time is additional.

## Repurposing Requests

When Marketing wants the same content adapted for multiple platforms, they send separate requests for each platform — not one request for "all platforms." Each platform writer needs their own brief because format, voice, and constraints differ.

Example: A blog post gets published. Marketing then sends:
- Brief to LinkedIn Writer: "Adapt the blog's key insight into a thought leadership post"
- Brief to Twitter/X Writer: "Create a thread summarizing the 3 points"
- Brief to TikTok Writer: "Write hook + caption for a short video on point #1"

Each is a separate production cycle through the Content Director's quality gate.

## Escalation

| Situation | Escalation path |
|---|---|
| Writer disagrees with strategic brief | Writer → Content Director → CCO → Marketing Lead |
| Quality gate fails 3+ times on same piece | Content Director → CCO (may reassign to different writer) |
| Marketing and Content Creation disagree on voice/approach | CCO → parent AI (council chair arbitrates) |
| Content involves legal/financial/medical claims | CCO → parent AI → human (Tier 3) |
| Urgent request (same-day turnaround) | Requester marks PRIORITY: critical; CCO may assign directly, skip full gate |

## What This Protocol Does NOT Cover

- **Content strategy creation** (editorial calendars, pillar planning) — that's Marketing's domain, handled internally
- **Content distribution and engagement** — Marketing owns publishing, community management, and audience engagement
- **Visual content** (images, videos, design assets) — Design department handles visual production; Content Creation handles the written component only

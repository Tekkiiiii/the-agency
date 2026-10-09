---
name: content-request-protocol
description: The single content-production pipeline. PD -> Coord -> general-purpose writer -> /content-polish -> critics via /cc-loop. Brief format, writer routing table, quality gate, turnaround, repurposing, escalation.
type: runbook
owner: system-improvement
lastUpdated: 2026-10-08
version: 2.0.0
---

# Content Request Protocol

How written content gets produced. This is the ONE content pipeline doc. There is no department layer and no content head: the 2026-10-08 dept sunset folded `agents/content-creation/protocols/content-request.md` and `agents/content-creation/pipelines/content-production/` into this file (originals archived under `{agency-root}/agents-archive/dept-sunset-2026-10-08/content-creation/`).

## The Flow

```
Requester (operator / main session / PD; owns strategy, builds the strategic brief)
       |
       v
PD  (validates brief completeness, hands the production task to a Coord)
       |
       v
Coord  (spawns the writer, runs the quality gate, owns delivery)
       |
       +--> Writer: general-purpose + skills (drafts)
       |         |
       |         +--> /content-polish   (humanizer + proofreader pass; EN or VI chain)
       |               |
       |               +--> /cc-loop    (critics in parallel; pass avg >= 80, min >= 70, max 3 rounds)
       v
Coord delivers the approved artifact + quality evidence to the PD
       |
       v
PD / requester publishes, distributes, measures
       |
       v
Requester feeds performance data back to the PD (next briefs cite what worked / did not)
```

Spawn rules: writers are `general-purpose` Execs with 1-3 skills, spawned by the Coord (or by the PD directly when the delegation test in `pd-coordinator.md` says no Coord is needed). Critics are `critique-*` agents (`agents/critiques/`), spawned by `/cc-loop`. Role files for each writer type are listed in `{agency-root}/agents-archive/ROLE-MAP.md`.

## Step-by-Step

### Step 1 - Requester states the request

The request can be short: what content, rough topic, target audience, timeline, priority (`low | medium | high | critical`). The PD (or a `general-purpose` Exec with `/content-strategy` on its behalf) expands it into the strategic brief in Step 2. The PD hands the brief to a Coord as a normal task (task file with the brief inline or linked).

### Step 2 - Strategic brief (6 fields, all mandatory)

```
STRATEGIC BRIEF
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
- Path to {project}/memory/brand-guidelines.md
- Any specific constraints or requirements
```

**Completeness check (PD, before handing to the Coord).** If any of the six fields is missing, the PD returns the brief to the requester with the exact list of gaps. Do not start production on an incomplete brief.

### Step 3 - Coord routes to the right writer

The Coord reads the brief and spawns the writer as `general-purpose` with the skills below. Spawn prompt: "Role: read the role file for this writer listed in `{agency-root}/agents-archive/ROLE-MAP.md` first. Skills: ... Task: ..." The Coord attaches the strategic brief, the brand-guidelines path and any extra editorial direction.

| Content type | Spawn as `general-purpose` + skills |
|---|---|
| Blog post, article, thought leadership | /blog-pipeline, /content-creator, /seo-aeo-best-practices |
| Case study, whitepaper, report | /content-creator, /content-polish |
| Newsletter, editorial | /content-creator, /content-polish |
| LinkedIn post | /content-creator, /copywriting, /content-polish |
| Twitter/X thread | /content-creator, /copywriting, /content-polish |
| Instagram caption | /content-creator, /copywriting, /content-polish |
| TikTok caption/copy | /content-creator, /copywriting, /content-polish |
| Reddit post | /content-creator, /copywriting, /content-polish |
| Threads post | /content-creator, /copywriting, /content-polish |
| Facebook post | /content-creator, /copywriting, /content-polish |
| Discord announcement | /content-creator, /copywriting, /content-polish |
| YouTube title/description | /content-creator, /seo-aeo-best-practices |
| Pinterest pin copy | /content-creator, /copywriting, /content-polish |
| Quora answer | /content-creator, /copywriting, /content-polish |
| Telegram channel post | /content-creator, /copywriting, /content-polish |
| Ad copy (Meta/Google/TikTok) | /copywriting, /content-polish |
| Landing page / sales page | /copywriting, /seo-aeo-best-practices |
| Email campaign / sequence | /copywriting, /content-polish |
| Video script | /youtube-narration, /video-prompt-director (then `content-to-video-protocol.md` for production) |
| Developer docs, API refs, tutorials | /tech-writer, /document-release |
| Slide deck / pitch deck | /deck-narrative, /marp |
| Press release, media kit | /content-creator, /content-polish |

Capacity: if one writer type already has more than 3 active tasks in the same Coord, the Coord queues, reassigns or expedites; it never silently stacks.

### Step 4 - Writer produces the draft

The writer:
1. Reads the strategic brief and brand guidelines.
2. Researches the topic (competing content, data points, angles).
3. Outlines (long-form) or drafts directly (short-form).
4. Writes the full piece in the brand's voice.
5. Self-check: stop-slop scan, then submits the draft to the Coord. The full polish happens in Step 5, not here.

### Step 5 - Quality gate: /content-polish, then /cc-loop

The Coord runs the gate (or spawns a `general-purpose` Exec with `/cc-loop` to run it):

1. **`/content-polish`** on the draft. English runs `humanizer` + `proofreader`; Vietnamese runs `humanizer-vi` + `grammar-checker-vi` (optional `translationese-cleaner-vi` first). AI-slop check via `stop-slop`.
2. **`/cc-loop`** with the domain that matches the content (`blog`, `email`, `brief`, `script`, `deck`, or `custom` with `--critics`). Critics run in parallel (default for written content: `critique-content`, plus marketing / SEO / brand critics per the cc-loop critic matrix; `critique-social`, `critique-seo`, `critique-video` where the format calls for them).
3. **Pass bar:** average score across critics >= 80 AND lowest single score >= 70. Max 3 rounds. Brand voice is checked against `brand-guidelines.md` by `critique-brand`.

If the loop ends below the bar after 3 rounds, the Coord does NOT ship: it escalates (see Escalation). The Coord attaches the cc-loop score table and the log path to the delivery.

**Critical priority.** For `PRIORITY: critical` the PD may approve a condensed gate: `/content-polish` only (proofreader pass), skipping `/cc-loop`. Used only when the brief explicitly marks `critical`; the delivery must say the loop was skipped.

### Step 6 - Sign-off

- **Standard content** (blog posts, social posts, emails, video scripts): a passing `/cc-loop` result is sufficient.
- **High-stakes content** (press releases, legal/financial/medical claims, crisis communications): the PD reviews personally and, for legal/financial/medical claims, escalates to the operator before release (Tier 3).

### Step 7 - Delivery

The Coord delivers to the PD as a normal Exec/Coord completion report (the final result, not a SendMessage):

```
[Content type] for [project] delivered.
- Quality gate: [cc-loop avg / min / rounds, polish status]
- File: [output file path]
- SEO notes: [keyword suggestions, internal linking recommendations]
- A/B suggestion: [variant ideas for testing, if applicable]
Ready for your distribution decision.
```

Output location follows the standard rule: `{project}/outputs/{skill}/{YYYY-MM-DD}-{descriptor}/`.

### Step 8 - Distribution and feedback

The requester owns publishing and distribution: review against the brief, publish, optionally request repurposed versions. After the measurement window (typically 7-14 days) the requester records performance data (key metrics, what resonated, recommended follow-ups) in the project's memory/lessons so future briefs cite concrete "this worked / this did not" evidence.

## Turnaround

Measured from the moment the Coord receives a COMPLETE brief. Brief-building time is additional.

| Content type | Standard | Critical |
|---|---|---|
| Social media post (single platform) | Same day | 2 hours |
| Blog post (1,000-2,000 words) | 1-2 days | Same day |
| Case study / whitepaper | 3-5 days | 2 days |
| Email sequence (3-5 emails) | 2-3 days | 1 day |
| Video script (short-form) | Same day | 2 hours |
| Video script (long-form) | 1-2 days | Same day |
| Press release | 1-2 days | Same day |
| Slide deck | 2-3 days | 1 day |
| Whitepaper (5,000+ words) | 5-10 days | 3 days |

`critical` may reduce gate depth (Step 5, critical priority).

## Repurposing Requests

Request each platform separately, not "all platforms": every platform writer needs its own brief because format, voice and constraints differ. Example after a blog post ships:
- LinkedIn writer (general-purpose + skills): "Adapt the blog's key insight into a thought leadership post"
- Twitter/X writer: "Create a thread summarizing the 3 points"
- TikTok writer: "Write hook + caption for a short video on point #1"

Each is a separate production cycle through the Step 5 gate.

## Escalation

| Situation | Escalation path |
|---|---|
| Writer disagrees with the strategic brief | Writer -> Coord -> PD -> requester |
| `/cc-loop` below bar after 3 rounds | Coord -> PD (may reassign to a fresh writer with the critic fix list) |
| Requester and PD disagree on voice/approach | PD -> operator arbitrates |
| Legal/financial/medical claims | PD -> operator (Tier 3) |
| Urgent same-day request | Requester marks `PRIORITY: critical`; Step 5 critical rule applies |

Upward escalation travels as the final Exec/Coord report (never upward SendMessage; see `checkpoint-handshake-protocol.md`).

## What This Protocol Does NOT Cover

- Content strategy creation (editorial calendars, pillar planning): the requester / PD, with `/content-strategy`.
- Distribution and community engagement: the requester.
- Visual content (images, video, design assets): see `content-to-video-protocol.md` for video; design work routes to a `general-purpose` Exec with design skills (`/design-router`).

## Improving This Protocol

Propose changes as a PD task file in `{project}/memory/tasks/`; edit this file and bump `version` + add a Version History row on approval.

## Version History

| Version | Date | Change | Approved by |
|---|---|---|---|
| 1.0 | 2026-05-13 | Initial formalization (multi-layer department flow) | System initialization |
| 2.0 | 2026-10-08 | Dept sunset (D8): single doc; PD -> Coord -> general-purpose writer -> /content-polish -> /cc-loop critics; folded the content-production pipeline and agents/content-creation protocol; removed the department-head, dept-coordinator and department state-file machinery | Maintainers (dept sunset) |

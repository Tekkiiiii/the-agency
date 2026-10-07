---
name: inbound-sales
description: "Use for inbound lead handling and outbound sequences: review the lead queue, set up lead routing, score leads (BANT), define the ICP, write cold email/LinkedIn sequences, MQL>SQL funnel analysis, CRM hygiene, SDR onboarding. Includes scoring tiers, routing rules, disqualification criteria."
---

# Inbound Sales Skill

## When to Activate

Trigger when the user asks to:
- Qualify or score inbound leads
- Build or audit lead routing rules
- Write outbound email or LinkedIn sequences
- Define or refine an ICP (Ideal Customer Profile)
- Analyze lead source attribution or funnel conversion
- Set up CRM lead stage progression criteria
- Build a lead follow-up cadence

## ICP Definition Framework

### Firmographics
- **Company size**: revenue range, employee count
- **Industry**: vertical, sub-vertical
- **Geography**: target markets
- **Stage**: startup, growth, enterprise
- **Tech stack**: tools they currently use

### Technographics
- Current tools for each problem you solve
- Technology maturity level
- Integration ecosystem they live in

### Behavioral Signals
- Pricing page visits (high intent)
- Demo requests (very high intent)
- Content downloads by type
- Feature page engagement depth
- Email reply rates and patterns

### Disqualifying Criteria
- No budget authority identified
- Outside target geography
- Competitor is a key stakeholder
- No expressed pain around your solution

## Lead Scoring Model

Score each lead 0–100. Tiers:

| Score | Tier | Action |
|---|---|---|
| 80–100 | A (Hot) | Immediate outreach, schedule demo |
| 50–79 | B (Warm) | Nurture sequence, try to book call |
| 20–49 | C (Cool) | Long nurture, content cadence |
| 0–19 | D (Cold) | Re-engagement campaign or suppress |

**Scoring dimensions:**

BANT:
- **Budget**: Has budget authority / allocated (0–25)
- **Authority**: Knows who decides (0–25)
- **Need**: Has a stated problem you solve (0–25)
- **Timeline**: Ready within your sales cycle (0–25)

Plus engagement multiplier:
- Demo request: ×1.5
- Multiple pricing page visits: ×1.3
- Email reply: ×1.2
- Content download only: ×1.0

## Lead Routing Rules

Route leads based on:
1. **Territory** — geography, industry vertical
2. **Rep capacity** — max active opportunities per rep
3. **Lead score tier** — A goes to top performer, D goes to nurture queue
4. **Product line** — specialized rep for specific products

Rule of thumb: A leads must be routed within 15 minutes.

## Outbound Sequence Structure

Research before every sequence:
1. Find the prospect's recent blog posts, tweets, press releases
2. Identify a specific pain point they mentioned
3. Find a mutual connection or shared interest

### Email Sequence Template (4-touch)

```
DAY 1 — Email
Subject: Quick question about [specific pain point]
Body:
Hi [Name],

I noticed [specific observation about their company/product/pain].

Most [their role] I talk to struggle with [their pain]. We help [similar company] [specific outcome].

Do you have 15 minutes this week?

[Your name]

DAY 3 — LinkedIn (if no reply)
Connection note: "Hi [Name], I'd love to connect — I follow [their company's] work in [area]."
Follow-up message (after connect): "Thanks for connecting! Quick question: is [pain] something your team is focused on right now?"

DAY 7 — Email #2
Subject: Re: Quick question about [pain]
Body:
Hi [Name],

Just circling back on my note from [date].

If [pain] isn't a priority right now, no worries — I'll check back in [quarter]. But if it is, I'd love to show you how [specific company] reduced [metric] by [X%] in 90 days.

[Your name]

DAY 14 — Breakup email
Subject: One last thing
Body:
Hi [Name],

I tried! Sending my last note — happy to close the loop if this is relevant, or I'll leave you alone.

Either way, best of luck with [their initiative].

[Your name]
```

## Follow-Up Cadence

| Scenario | Response |
|---|---|
| First reply | Respond immediately, try to book meeting |
| No reply by day 7 | Send follow-up |
| Bounce | Mark as bounce, remove from sequence |
| Meeting booked | Log to CRM, stop sequence |
| Demo completed | Move to demo follow-up sequence |
| Closed won | Stop all sequences, trigger onboarding handoff |
| Closed lost | Archive, note reason in CRM |

## CRM Hygiene Standards

Required fields for every lead:
- Company name, size, industry
- Contact name, title, email, phone
- Lead source (how they found you)
- Lead score (with date scored)
- Next action / next step date
- Owner (assigned rep)

Stage progression criteria:
- MQL → SAL: responded to outbound, or visited pricing page
- SAL → SQL: had a discovery call or replied to sequence
- SQL → Opportunity: budget + authority confirmed
- Opportunity → Closed: signed contract

Never advance a stage without evidence.

## Disqualification Criteria

Stop pursuing when:
- No budget signal after 3 outreach attempts
- ICP criteria not met (company size, industry, tech stack)
- No authority identified and cannot find it
- Wrong timing (too early in buying cycle, company in crisis)
- Competitor already sold in
- Gatekeeper blocks all access

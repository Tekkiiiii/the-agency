---
name: office-hours
description: >
  YC-style Office Hours — startup diagnostic and builder brainstorm for solo
  founders and small teams. Diagnoses: what is the company actually building,
  who is the customer, what is the biggest problem right now, and what should
  the next 30 days look like. Two modes: startup (product-strategy focus)
  and builder (technical execution focus). Triggers when: "office hours",
  "diagnose my startup", "what should I be working on", "help me figure out
  strategy", or when a founder feels stuck. Key capabilities: 6 forcing
  questions that cut through noise, a clarity score that quantifies how
  well-defined the current direction is, and a 30-day action plan. Also for:
  new cofounder onboarding, preparing for real investor office hours, and
  mid-quarter planning sessions.
---

# /office-hours — YC-Style Startup Diagnostic

Structured office hours for founders and builders.

## When to Activate

Trigger `/office-hours` when:
- "office hours" or "diagnose my startup"
- "what should I be working on?"
- Founder feels stuck
- Pre-investor-meeting prep
- Mid-quarter planning

## Two Modes

| Mode | Best For | Tone |
|------|----------|------|
| **Startup** | Pre-product-market fit, strategic decisions | Diagnostic, Socratic |
| **Builder** | Post-product-market fit, execution challenges | Tactical, direct |

Ask: "Are we in startup mode (product/strategy) or builder mode (technical execution)?"

## The 6 Forcing Questions

These questions cut through noise. Do not skip any.

### Q1: What does your company do? (in one sentence)

**Red flags:**
- "We use AI/LLM/blockchain/web3" as a description (that's a technology, not a product)
- "We help businesses..." without specifying which businesses and how
- Lists of features instead of outcomes

**Strong answer:**
"We help [specific customer] do [specific job] by [specific mechanism]."

### Q2: Who is your customer? (specific person, not a persona)

**Red flags:**
- "Enterprise companies" (too broad)
- "People who want to be productive" (too broad)
- Multiple customer types equally weighted

**Strong answer:**
"[Name/job title] at [specific company type/size], who is currently doing [specific workaround or struggling with specific problem]."

### Q3: What is the biggest problem right now? (one problem)

**Red flags:**
- "Everything" or "product-market fit"
- Technical debt as the biggest problem (usually a symptom)
- Too many equally-ranked problems

**Strong answer:**
"The #1 blocker is [specific problem], which prevents us from [specific outcome]."

### Q4: What have you tried in the last 30 days? (not plans)

**Red flags:**
- "We were going to..." or "We planned to..."
- Long list of features shipped without customer validation
- No experiments run

**Strong answer:**
"We ran [experiment] with [customer segment] and learned [specific finding]."

### Q5: What would the next 30 days look like if they went perfectly?

**Red flags:**
- Building features without customer touchpoints
- "Scale" as the goal before product-market fit
- No definition of success

**Strong answer:**
"In 30 days: [specific metric] moved from [X] to [Y], evidenced by [customer feedback/data]."

### Q6: What are you not doing that you should be?

**Red flags:**
- "I don't know" (common but a red flag)
- Defensive answers that justify current priorities
- Strategic blind spots unacknowledged

**Strong answer:**
"We're not doing [specific thing] because [acknowledged gap], and it matters because [consequence]."

## Clarity Score

After the 6 questions, score the clarity:

| Score | Label | Description |
|-------|-------|-------------|
| 9-10 | Crystal clear | Founder has specific answers, can articulate clearly |
| 7-8 | Direction clear | Big picture clear, execution gaps |
| 5-6 | Partially defined | Some clarity, significant gaps in customer/problem |
| 3-4 | Foggy | Vague answers, defensiveness, confused priorities |
| 1-2 | Stuck | Founder is lost, too many competing priorities |

## Diagnostic Output

```
OFFICE HOURS — {company/project name}
══════════════════════════════════════

CLARITY SCORE: {N}/10 — {label}

THE COMPANY:
{one-sentence description}
Customer: {customer}
Biggest problem: {problem}

WHAT'S WORKING:
- {win 1}
- {win 2}

WHAT'S NOT WORKING:
- {problem 1}
- {problem 2}

THE CONFUSION (if score < 7):
- {specific unclear area}
- {specific unclear area}

30-DAY PLAN:
1. [specific action] — by [date]
2. [specific action] — by [date]
3. [specific action] — by [date]

NEXT OFFICE HOURS: {date in 4 weeks}

RECOMMENDATION: {what the founder should focus on}
```

## Startup Mode: Deep Diagnosis

If startup mode and clarity score < 7, dig deeper:

**Problem-solution fit:**
- Is this a problem that customers pay to solve?
- What's the current workaround?
- Why hasn't this been solved already?

**Customer understanding:**
- Have you talked to 10 customers this week?
- What's the most recent thing a customer told you?
- Where do customers churn or not convert?

**Progress since last office hours:**
- What changed? Did metrics move?
- Did the strategy change? Why?

## Builder Mode: Tactical Diagnosis

If builder mode, focus on execution:

**What are you building this week?**
- Specific deliverables, not vague roadmap items

**What's blocking you?**
- Technical debt, unclear requirements, missing decisions?

**What should you stop doing?**
- Perfectionism, over-engineering, building in isolation?

## Important Rules

- **The 6 questions are non-negotiable.** Don't skip any.
- **Push on vague answers.** "We're helping businesses be more productive" is not a product. Push until the answer is specific.
- **No defensiveness.** The goal is clarity, not validation.
- **Clarity score is honest.** Don't inflate to spare feelings — founders need an accurate read.
- **30-day plan is specific.** Not "ship more features" — "A/B test pricing page by March 15."
- **This is Socratic, not advisory.** You ask questions. The founder finds the answers.

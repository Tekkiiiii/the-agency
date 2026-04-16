---
name: codex
description: >
  OpenAI Codex CLI wrapper — reviews code, challenges AI-generated output,
  provides second opinions, and runs model-vs-model comparisons. Triggers when:
  reviewing AI-generated code, validating Codex output, running AI agents in
  parallel, or any time you want a second set of eyes on generated code.
  Key capability: structured model-vs-model debate that surfaces hidden
  assumptions. Also for: evaluating code quality, explaining AI decisions,
  and benchmark comparisons between models.
---

# /codex — OpenAI Codex CLI Wrapper

Structured review, challenge, and consultation using OpenAI Codex CLI.

## When to Activate

Trigger `/codex` when:
- Reviewing AI-generated code
- Validating Codex output
- Running AI-vs-AI comparisons
- Getting a second opinion on a decision
- Evaluating code quality from generated output

## Modes

| Mode | Use |
|------|-----|
| `review` | Review code and provide structured critique |
| `challenge` | Challenge assumptions in existing code or decisions |
| `consult` | Explain a system, approach, or decision |
| `compare` | Model-vs-model comparison |

**Syntax:** `/codex {mode} {target}`

## Review Mode

### Syntax
```
/codex review {file or code snippet}
```

### Process

**Step 1: Run Codex review**

```bash
# Single file
codex --model gpt-4o \
  --prompt "Review {target} for correctness, security, performance, and maintainability. Rate each category 1-10. List specific issues with line references. Suggest fixes." \
  2>&1 | tee /tmp/codex-review-output.txt

# Multiple files
codex --model gpt-4o \
  --files "src/auth/login.ts src/auth/token.ts src/auth/middleware.ts" \
  --prompt "Review for auth correctness, token handling, session management. Rate each category 1-10." \
  2>&1
```

**Step 2: Extract findings**

```
CODEX REVIEW OUTPUT — {target}
════════════════════════════════

CORRECTNESS:      {N}/10
  Issues: {list with line refs}
  Fix:   {suggestion}

SECURITY:         {N}/10
  Issues: {list with line refs}
  Fix:   {suggestion}

PERFORMANCE:      {N}/10
  Issues: {list with line refs}
  Fix:   {suggestion}

MAINTAINABILITY:  {N}/10
  Issues: {list with line refs}
  Fix:   {suggestion}

OVERALL:          {N}/10
RECOMMENDATION:   APPROVE | REVISE | REJECT
```

**Step 3: Present to user**

Present findings structured as:
- What Codex got right
- What Codex may have missed
- Specific issues to address
- Verdict

### Review criteria

```
CODEX REVIEW RUBRIC
════════════════════════════════

Correctness (non-negotiable):
□ Logic errors present?
□ Edge cases handled?
□ Error handling correct?
□ Type safety adequate?

Security:
□ Auth/authz correct?
□ Input sanitized?
□ Secrets handled?
□ SQL injection possible?

Performance:
□ N+1 queries?
□ Unnecessary allocations?
□ Sync blocking?

Maintainability:
□ Naming clear?
□ Functions do one thing?
□ Dependencies reasonable?
□ Tests cover critical paths?
```

## Challenge Mode

### Syntax
```
/codex challenge {assumption or decision}
```

### Process

**Step 1: State the assumption**

```
CODEX CHALLENGE — {assumption}
════════════════════════════════
Claimed by:  {source}
Evidence:   {evidence cited}

What could make this wrong?
```

**Step 2: Run challenge**

```bash
codex --model gpt-4o \
  --prompt "Challenge this assumption: {assumption}. Find 5 reasons it might be wrong. Be specific. Consider: edge cases, counterexamples, hidden costs, second-order effects, alternative explanations. Format: each challenge with a brief rebuttal." \
  2>&1
```

**Step 3: Run defense**

```bash
codex --model o3 \
  --prompt "Defend this assumption against challenges: {assumption}. For each challenge, provide a counter-argument or acknowledge the valid concern. Be honest about weaknesses." \
  2>&1
```

**Step 4: Present debate**

```
CODEX CHALLENGE — {assumption}
════════════════════════════════

CHALLENGES (from gpt-4o):
1. {challenge 1}
2. {challenge 2}
3. {challenge 3}
4. {challenge 4}
5. {challenge 5}

DEFENSE (from o3):
1. {response 1}
2. {response 2}
3. {acknowledged weakness 3}
4. {response 4}
5. {response 5}

VERDICT: ASSUMPTION HOLDS | ASSUMPTION WEAK | ASSUMPTION REJECTED
REASONING: {one-line summary}
```

## Consult Mode

### Syntax
```
/codex consult {question about codebase}
```

### Process

```bash
codex --model gpt-4o \
  --files "src/{relevant-files}..." \
  --prompt "Explain how {system} works. Focus on: data flow, key components, entry points, edge cases, and implicit assumptions. Use simple language. After explanation, list what is NOT obvious from reading the code." \
  2>&1
```

### Consult output

```
CODEX CONSULT — {system}
════════════════════════════════

HOW IT WORKS:
{plain-language explanation}

KEY COMPONENTS:
- {component}: {role}
- {component}: {role}

DATA FLOW:
1. {step}
2. {step}
3. {step}

ENTRY POINTS:
- {endpoint or function}

EDGE CASES:
- {case}: {behavior}
- {case}: {behavior}

HIDDEN ASSUMPTIONS:
1. {assumption}
2. {assumption}

WHAT'S NOT OBVIOUS:
- {observation}
```

## Compare Mode

### Syntax
```
/codex compare {file} {model-a} {model-b}
```

### Process

**Step 1: Run both models**

```bash
# Model A review
echo "MODEL A: gpt-4o"
codex --model gpt-4o \
  --files "{target}" \
  --prompt "Review this code. Rate: correctness, security, performance, maintainability (1-10 each). List top 3 issues with fixes." \
  2>&1 | tee /tmp/codex-compare-a.txt

# Model B review
echo "MODEL B: o3"
codex --model o3 \
  --files "{target}" \
  --prompt "Review this code. Rate: correctness, security, performance, maintainability (1-10 each). List top 3 issues with fixes." \
  2>&1 | tee /tmp/codex-compare-b.txt
```

**Step 2: Judge comparison**

```bash
codex --model gpt-4o \
  --prompt "Compare these two code reviews. Focus on: where they agree, where they disagree, which issues are most critical, and which model's recommendations are more actionable. File A: {cat /tmp/codex-compare-a.txt} File B: {cat /tmp/codex-compare-b.txt}" \
  2>&1
```

### Compare output

```
CODEX COMPARE — {target}
════════════════════════════════

MODEL A (gpt-4o):
Correctness:    {N}/10
Security:        {N}/10
Performance:     {N}/10
Maintainability: {N}/10
Top issue:       {issue}

MODEL B (o3):
Correctness:    {N}/10
Security:        {N}/10
Performance:     {N}/10
Maintainability: {N}/10
Top issue:       {issue}

AGREEMENTS:
- {point of agreement 1}
- {point of agreement 2}

DISAGREEMENTS:
- {point of disagreement 1} — Model A: {view}, Model B: {view}
- {point of disagreement 2}

RECOMMENDATION: {which model's critique to prioritize and why}
```

## JSONL Streaming

```bash
# Stream responses to JSONL for processing
codex --model gpt-4o \
  --files "{target}" \
  --prompt "Review code quality" \
  --stream \
  --output /tmp/codex-stream.jsonl

# Process streaming output
tail -f /tmp/codex-stream.jsonl | jq '.choices[0].delta.content'
```

## Important Rules

- **Second opinion, not final word.** Codex is a tool — use its output critically.
- **Challenge mode is for assumptions, not code.** For code issues, use review mode.
- **Compare mode surfaces blind spots.** When models disagree, that's interesting.
- **JSONL for automation.** Stream to file for programmatic processing.
- **Consult mode explains, not decides.** The human makes the call.

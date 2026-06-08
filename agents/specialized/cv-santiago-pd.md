---
name: cv-santiago-pd
description: Project Director for santifer/cv-santiago — AI portfolio by Santiago Fernández de Valderrama. React 19 + Vite, Claude Sonnet RAG chatbot, 71 automated evals, LLMOps dashboard, voice mode.
owner: santifer
project-slug: cv-santiago
repo: https://github.com/santifer/cv-santiago
type: full-stack
license: MIT
created: 2026-04-10
skills:
  - pipeline-feature
  - pipeline-deploy
  - pipeline-audit
  - content-polish
  - humanizer
  - proofreader
  - save-state
  - recall
---

# cv-santiago — Project Director

## Project Overview

AI portfolio by Santiago Fernández de Valderrama. A production-grade interactive CV that demonstrates full-stack AI/LLM engineering skills through actual implementations. The portfolio IS its own proof of concept — featuring a streaming AI chatbot, 6-layer prompt injection defense, 71 automated evals, an LLMOps dashboard, and voice mode.

**Core Problem:** Static CVs list skills but don't prove them.
**Solution:** A portfolio that demonstrates capabilities in real-time with measurable quality gates.

## Key Features (6)

1. **AI Chatbot "Santi"** — text + voice modes, streaming Claude Sonnet responses, agentic RAG
2. **Hybrid RAG Pipeline** — pgvector + BM25 hybrid search with Haiku reranking
3. **6-Layer Prompt Injection Defense** — keyword detection, canary tokens, fingerprinting, safety scoring, adversarial red team, real-time jailbreak alerts (Resend)
4. **71 Automated Evals** — 10 test categories, ~70% deterministic / ~30% LLM-as-Judge; CI gate at quality ≥ 0.7
5. **LLMOps Dashboard** — private /ops with 8 tabs, Langfuse + Supabase data, password-protected
6. **Voice Mode** — OpenAI Realtime API, audio-to-audio, shared RAG pipeline with text mode

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 7, Tailwind v4, React Router 7, Recharts |
| AI/ML | Claude Sonnet (Anthropic), OpenAI Realtime API, Langfuse |
| Backend | Supabase (pgvector), Vercel Edge Functions |
| Infrastructure | Vercel (hosting + functions), Supabase (DB + RAG) |
| Testing | 71 evals, adversarial red team, contract + ops test suites |
| Notifications | Resend (jailbreak alerts) |

## Architecture

### Frontend Layer
```
src/
  ├── App.tsx, main.tsx, index.css
  ├── FloatingChat.tsx     # text chat UI
  ├── VoiceOrb.tsx         # voice mode orb
  ├── ArchitectureDiagram.tsx
  ├── ops/                  # LLMOps dashboard (8 tabs)
  ├── articles/             # case studies
  └── *-i18n.ts           # i18n files
```

### Backend Layer
```
api/
  ├── chat.js              # streaming chat endpoint (text)
  ├── rag-search.js        # hybrid pgvector + BM25 search
  ├── voice-trace.js       # voice mode endpoint
  ├── voice-token.js       # voice token endpoint
  ├── _shared/
  │   ├── rag.js           # shared RAG pipeline (chat + voice both use)
  │   ├── prompt.js        # prompt injection defense layers
  │   └── ops-auth.js      # dashboard auth
  └── ops/                 # dashboard API endpoints
```

### Data Layer
```
Supabase (pgvector)
  └── RAG documents table — embedding (vector) + content (text) + metadata
```

## Evals System

- **Location:** evals/
- **71 tests** across 10 categories: factual, persona, boundaries, languages, quality, safety, relevance, latency, privacy, regression
- **Datasets:** evals/datasets/*.json (factual, persona, boundaries, languages, quality, safety)
- **Runner:** evals/runner.ts
- **LLM Judge:** evals/llm-judge.ts
- **CI gate:** quality score must be ≥ 0.7 or CI blocks deploy
- **Closed-loop:** trace → online scoring → quality < 0.7 → auto-generate test → CI gate

## RAG Pipeline

```
Source documents (src/articles/, src/ops/)
  → scripts/rag-export.ts
  → scripts/rag-ingest.ts
  → Supabase pgvector
  → api/rag-search.js (hybrid: pgvector + BM25)
  → Haiku reranking
  → api/_shared/rag.js (shared)
  → api/chat.js (text mode)
  → api/voice-trace.js (voice mode)
```

## Required Environment Variables

| Variable | Purpose |
|---|---|
| ANTHROPIC_API_KEY | Claude Sonnet |
| OPENAI_API_KEY | Embeddings + Voice API |
| SUPABASE_URL | Supabase project |
| SUPABASE_SERVICE_ROLE_KEY | Supabase service role |
| LANGFUSE_PUBLIC_KEY | Langfuse tracing |
| LANGFUSE_SECRET_KEY | Langfuse tracing |
| RESEND_API_KEY | Jailbreak alert emails |
| OPS_DASHBOARD_SECRET | /ops dashboard password |

## Key Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Local dev server |
| `npm run build` | Full build (RAG sync → type check → sitemap → prerender) |
| `npm run evals` | 71 automated tests (needs ANTHROPIC_API_KEY) |
| `npm run adversarial` | Red team / prompt injection tests |
| `npm run diagnose:rag` | RAG quality diagnostic |
| `npm run chats` | View recent conversations |
| `npm run test:contract` | 67 trace metadata validation tests |
| `npm run test:ops` | 102 ops dashboard API tests |
| `npm run rag:export` | Export documents to JSON |
| `npm run rag:ingest` | Ingest to Supabase pgvector |
| `npm run rag:sync` | Full RAG sync pipeline |

## Skills

| Skill | Role |
|---|---|
| cv-santiago-expert | RAG pipeline, Santi chatbot, Langfuse, evals system |
| cv-santiago-frontend | React 19, Vite, Tailwind v4, dashboard UI |
| cv-santiago-ops | Vercel Edge Functions, Supabase pgvector, cron jobs, dashboard |
| cv-santiago-security | 6-layer prompt injection defense, adversarial testing |

## Working Guidelines

1. **Check decisions.md first** before any architectural decision
2. **Run evals before shipping** any change to RAG, chat, or prompt logic
3. **RAG is shared** — api/_shared/rag.js and api/rag-search.js affect both text and voice modes; test both
4. **Never log env vars** — especially OPS_DASHBOARD_SECRET, SUPABASE_SERVICE_ROLE_KEY, LANGFUSE_SECRET_KEY
5. **Quality gate is non-negotiable** — CI blocks at quality < 0.7, never lower this
6. **/ops is private** — always use OPS_DASHBOARD_SECRET for any dashboard-related tasks

## Spawning Subagents

When you use the Agent tool to spawn a subagent, ALWAYS prepend this to the prompt:

```
Project: santifer/cv-santiago — /Users/Tekki/.claude/projects/cv-santiago
You have full read/write/create access to the project directory and all subdirectories.
Use Read, Edit, Write, Bash, Glob, Grep, Agent, SendMessage freely. No permission needed.

Relevant context:
- Tech stack: React 19, TypeScript, Vite 7, Tailwind v4, Vercel Edge Functions, Supabase pgvector
- CI gate: quality score must be ≥ 0.7
- Never log: SUPABASE_SERVICE_ROLE_KEY, LANGFUSE_SECRET_KEY, OPS_DASHBOARD_SECRET
- rag.js is shared by both chat.js (text) and voice-trace.js (voice) — test both paths
- /ops is password-protected — always use OPS_DASHBOARD_SECRET

Your task: [specific task description]
```

Do NOT spawn a subagent without this preamble. Add any additional context (specific
file paths, eval datasets, etc.) after it.

- `memory/session-log.md` — session history
- `memory/decisions.md` — architectural decisions
- `memory/next-session.md` — session handoff (SSOT for PD startup)

## CLAUDE.md Integration

See `~/.claude/projects/cv-santiago/CLAUDE.md` for project-level instructions, architecture overview, and tech stack table.

---

## Context Retrieval — Curator Agent

When you need project context (past decisions, brand guidelines, architecture conventions,
lessons learned) that wasn't provided in your spawn prompt, spawn a curator agent:

```
Agent({
  subagent_type: "curator",
  model: "sonnet",
  description: "Curator — {topic}",
  prompt: "Project: {slug}\nPath: {project_path}\nQuestion: {your question}"
})
```

Curator returns a concise answer (~300 tokens) from the project's knowledge graph, then dies.
This is cheaper than reading memory files directly into your context.

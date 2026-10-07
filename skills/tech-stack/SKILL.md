---
name: tech-stack
description: "Use on \"what tech should I use\", \"which framework\", \"should I use X or Y\", \"help me pick a database\", \"recommend a stack\", or when starting a project or reviewing an existing stack. Clarifies team, scale, budget first; returns recommendation, alternatives, trade-offs and migration path."
---

# Tech Stack Advisor Skill

## Process

1. **Clarify requirements first** — before recommending, ask about:
   - Team size and existing expertise
   - Scale expectations (users, data volume)
   - Budget constraints (open source vs paid)
   - Deployment environment (cloud, on-prem, edge)
   - Timeline and MVP vs long-term

2. **Structure recommendations** using this format:
   - **Recommended Stack** with brief rationale
   - **Alternatives Considered** and why not chosen
   - **Trade-offs** honestly stated
   - **Migration path** if they're switching from something existing

## Common Stack Patterns

### Web App (Full Stack)
- Modern: Next.js + TypeScript + PostgreSQL + Prisma + Vercel
- Enterprise: Java Spring Boot / .NET + React + Oracle/MSSQL
- Rapid MVP: Supabase + Next.js or Firebase + React

### Mobile
- Cross-platform: React Native or Flutter
- Native performance critical: Swift (iOS), Kotlin (Android)

### Data / AI
- Python stack: FastAPI + SQLAlchemy + Pandas/Polars + PostgreSQL
- ML serving: FastAPI + PyTorch/TensorFlow + Redis cache

### Microservices
- Node.js or Go for high-throughput services
- Kafka or RabbitMQ for event streaming
- Docker + Kubernetes for orchestration

## Principles
- Prefer boring, proven technology for core infrastructure
- Match stack to team's existing knowledge when possible
- Avoid over-engineering for early-stage projects
- Always consider operational complexity, not just development speed
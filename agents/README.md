# 🎭 The Agency: AI Specialists Ready to Transform Your Workflow

> **A complete AI agency at your fingertips** - From frontend wizards to Reddit community ninjas, from whimsy injectors to reality checkers. Each agent is a specialized expert with personality, processes, and proven deliverables.

[![GitHub stars](https://img.shields.io/github/stars/msitarzewski/agency-agents?style=social)](https://github.com/msitarzewski/agency-agents)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?logo=github)](https://github.com/sponsors/msitarzewski)

---

## 🚀 What Is This?

Born from a Reddit thread and months of iteration, **The Agency** is a growing collection of meticulously crafted AI agent personalities. Each agent is:

- **🎯 Specialized**: Deep expertise in their domain (not generic prompt templates)
- **🧠 Personality-Driven**: Unique voice, communication style, and approach
- **📋 Deliverable-Focused**: Real code, processes, and measurable outcomes
- **✅ Production-Ready**: Battle-tested workflows and success metrics

**Think of it as**: Assembling your dream team, except they're AI specialists who never sleep, never complain, and always deliver.

---

## ⚡ Quick Start

### Option 1: Use with Claude Code (Recommended)

```bash
# Copy agents to your Claude Code directory
cp -r agency-agents/* ~/.claude/agents/

# Now activate any agent in your Claude Code sessions:
# "Hey Claude, use general-purpose + /frontend, /tailwind and help me build a React component"
```

### Option 2: Use as Reference

Each agent file contains:
- Identity & personality traits
- Core mission & workflows
- Technical deliverables with code examples
- Success metrics & communication style

Browse the agents below and copy/adapt the ones you need!

### Option 3: Use with Other Tools (Cursor, Aider, Windsurf, Gemini CLI, OpenCode)

```bash
# Step 1 -- generate integration files for all supported tools
./scripts/convert.sh

# Step 2 -- install interactively (auto-detects what you have installed)
./scripts/install.sh

# Or target a specific tool directly
./scripts/install.sh --tool cursor
./scripts/install.sh --tool copilot
./scripts/install.sh --tool aider
./scripts/install.sh --tool windsurf
```

See the [Multi-Tool Integrations](#-multi-tool-integrations) section below for full details.

---

## 🏛️ Org Structure

The Agency operates as a three-layer organization: the **Agency Council** (4 independent model-tier seats plus an optional Codex seat, see `{agency-root}/core/memory/agency-council.md`), **Project Directors** (one per project, PD -> Coord -> general-purpose Exec), and **Critics** (`critique-*`, spawned directly by the PD or Coord). The department-head and department-coordinator layer was sunset 2026-10-08 (`agents-archive/dept-sunset-2026-10-08/`).

See [ORG.md](ORG.md) for the org chart, council seats, and routing.

The org operates on a 3-tier approval model: **Tier 1** (PD approves immediately within project scope — small edits, research, code review), **Tier 2** (escalates to parent AI — new files, config changes, code modifications), **Tier 3** (surfaces to human — destructive ops, deployments, financial transactions).

## 🎨 The Agency Roster

### 💻 Engineering Division

Building the future, one commit at a time.

> Specialist roles are archived; spawn general-purpose + skills — see `{agency-root}/agents-archive/ROLE-MAP.md`.

### 🎨 Design Division

Making it beautiful, usable, and delightful.

> Specialist roles are archived; spawn general-purpose + skills — see `{agency-root}/agents-archive/ROLE-MAP.md`.

### 🎬 Project Management Division

Keeping the trains running on time (and under budget).

> Specialist roles are archived; spawn general-purpose + skills — see `{agency-root}/agents-archive/ROLE-MAP.md`.

### 🧪 Testing Division

Breaking things so users don't have to.

> Specialist roles are archived; spawn general-purpose + skills — see `{agency-root}/agents-archive/ROLE-MAP.md`.

### 🎯 Specialized Division

The unique specialists who don't fit in a box.

> Specialist roles are archived; spawn general-purpose + skills — see `{agency-root}/agents-archive/ROLE-MAP.md`.

---

## 🎯 Real-World Use Cases

### Scenario 1: Building a Startup MVP

**Your Team**:
1. 🎨 **general-purpose + /frontend, /tailwind** - Build the React app
2. 🏗️ **general-purpose + /backend, /postgresql-schema** - Design the API and database
3. 🚀 **general-purpose + /content-strategy, /copywriting** - Plan user acquisition
4. ⚡ **general-purpose + /mattpocock-skills:prototype** - Fast iteration cycles
5. 🔍 **general-purpose + /qa-only, /run-acceptance-tests** - Ensure quality before launch

**Result**: Ship faster with specialized expertise at every stage.

---

### Scenario 2: Marketing Campaign Launch

**Your Team**:
1. 📝 **general-purpose + /content-creator, /content-polish** - Develop campaign content across formats
2. 🎬 **general-purpose + /video-use, /ffmpeg** - Short-form video and distribution
3. 🔍 **critique-brand, critique-content, critique-seo** - Spawn the critics directly (see `critiques/INDEX.md`)
4. 📊 **general-purpose + /chart-viz** - Track and optimize performance

**Result**: Multi-channel coordinated campaign with platform-specific expertise.

---

### Scenario 3: Enterprise Feature Development

**Your Team**:
1. 👔 **general-purpose + /superpowers-writing-plans** - Scope and task planning
2. 💎 **general-purpose + /laravel-builder, /review** - Complex implementation
3. 🎨 **general-purpose + /ui-ux-pro-max** - Design system and components
4. 🧪 **general-purpose + /content-experimentation-best-practices** - A/B test planning
5. 📸 **general-purpose + /qa-only, /browse** - Quality verification
6. 🔍 **general-purpose + /qa-only, /run-acceptance-tests** - Production readiness

**Result**: Enterprise-grade delivery with quality gates and documentation.

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Add a New Agent

1. Fork the repository
2. Create a new agent file in the appropriate category
3. Follow the agent template structure:
   - Frontmatter with name, description, color
   - Identity & Memory section
   - Core Mission
   - Critical Rules (domain-specific)
   - Technical Deliverables with examples
   - Workflow Process
   - Success Metrics
4. Submit a PR with your agent

### Improve Existing Agents

- Add real-world examples
- Enhance code samples
- Update success metrics
- Improve workflows

### Share Your Success Stories

Have you used these agents successfully? Share your story in the [Discussions](https://github.com/msitarzewski/agency-agents/discussions)!

---

## 📖 Agent Design Philosophy

Each agent is designed with:

1. **🎭 Strong Personality**: Not generic templates - real character and voice
2. **📋 Clear Deliverables**: Concrete outputs, not vague guidance
3. **✅ Success Metrics**: Measurable outcomes and quality standards
4. **🔄 Proven Workflows**: Step-by-step processes that work
5. **💡 Learning Memory**: Pattern recognition and continuous improvement

---

## 🎁 What Makes This Special?

### Unlike Generic AI Prompts:
- ❌ Generic "Act as a developer" prompts
- ✅ Deep specialization with personality and process

### Unlike Prompt Libraries:
- ❌ One-off prompt collections
- ✅ Comprehensive agent systems with workflows and deliverables

### Unlike AI Tools:
- ❌ Black box tools you can't customize
- ✅ Transparent, forkable, adaptable agent personalities

---

## 🎨 Agent Personality Highlights

> "I don't just test your code - I default to finding 3-5 issues and require visual proof for everything."
>
> -- an archived Testing role (now /qa-only + /browse)

> "Every playful element must serve a functional or emotional purpose. Design delight that enhances rather than distracts."
>
> -- an archived Design role (now /emil-design-eng)

> "Let me add a celebration animation that reduces task completion anxiety by 40%"
>
> -- the same archived Design role, during a UX review

---

## 📊 Stats

- 🎭 Specialist roles archived 2026-10-06 (see ROLE-MAP); registered agents are PDs, coords, critiques, council seats, and service agents (department layer archived 2026-10-08)
- 📝 **46,000+ lines** of personality, process, and code examples
- ⏱️ **Months of iteration** from real-world usage
- 🌟 **Battle-tested** in production environments
- 💬 **50+ requests** in first 12 hours on Reddit

---

## 🔌 Multi-Tool Integrations

The Agency works natively with Claude Code, and ships conversion + install scripts so you can use the same agents across every major agentic coding tool.

### Supported Tools

- **[Claude Code](https://claude.ai/code)** — native `.md` agents, no conversion needed → `~/.claude/agents/`
- **[GitHub Copilot](https://github.com/copilot)** — native `.md` agents, no conversion needed → `~/.github/agents/`
- **[Antigravity](https://github.com/google-gemini/antigravity)** — `SKILL.md` per agent → `~/.gemini/antigravity/skills/`
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)** — extension + `SKILL.md` files → `~/.gemini/extensions/agency-agents/`
- **[OpenCode](https://opencode.ai)** — `.md` agent files → `.opencode/agents/`
- **[Cursor](https://cursor.sh)** — `.mdc` rule files → `.cursor/rules/`
- **[Aider](https://aider.chat)** — single `CONVENTIONS.md` → `./CONVENTIONS.md`
- **[Windsurf](https://codeium.com/windsurf)** — single `.windsurfrules` → `./.windsurfrules`
- **[OpenClaw](https://github.com/openclaw/openclaw)** — `SOUL.md` + `AGENTS.md` + `IDENTITY.md` per agent

---

### ⚡ Quick Install

**Step 1 -- Generate integration files:**
```bash
./scripts/convert.sh
```

**Step 2 -- Install (interactive, auto-detects your tools):**
```bash
./scripts/install.sh
```

The installer scans your system for installed tools, shows a checkbox UI, and lets you pick exactly what to install:

```
  +------------------------------------------------+
  |   The Agency -- Tool Installer                 |
  +------------------------------------------------+

  System scan: [*] = detected on this machine

  [x]  1)  [*]  Claude Code     (claude.ai/code)
  [x]  2)  [*]  Copilot         (~/.github/agents)
  [x]  3)  [*]  Antigravity     (~/.gemini/antigravity)
  [ ]  4)  [ ]  Gemini CLI      (gemini extension)
  [ ]  5)  [ ]  OpenCode        (opencode.ai)
  [ ]  6)  [ ]  OpenClaw        (~/.openclaw)
  [x]  7)  [*]  Cursor          (.cursor/rules)
  [ ]  8)  [ ]  Aider           (CONVENTIONS.md)
  [ ]  9)  [ ]  Windsurf        (.windsurfrules)

  [1-9] toggle   [a] all   [n] none   [d] detected
  [Enter] install   [q] quit
```

**Or install a specific tool directly:**
```bash
./scripts/install.sh --tool cursor
./scripts/install.sh --tool opencode
./scripts/install.sh --tool openclaw
./scripts/install.sh --tool antigravity
```

**Non-interactive (CI/scripts):**
```bash
./scripts/install.sh --no-interactive --tool all
```

---

### Tool-Specific Instructions

<details>
<summary><strong>Claude Code</strong></summary>

Agents are copied directly from the repo into `~/.claude/agents/` -- no conversion needed.

```bash
./scripts/install.sh --tool claude-code
```

Then activate in Claude Code:
```
Use the general-purpose agent with /frontend to review this component.
```

See [integrations/claude-code/README.md](integrations/claude-code/README.md) for details.
</details>

<details>
<summary><strong>GitHub Copilot</strong></summary>

Agents are copied directly from the repo into `~/.github/agents/` -- no conversion needed.

```bash
./scripts/install.sh --tool copilot
```

Then activate in GitHub Copilot:
```
Use the general-purpose agent with /frontend to review this component.
```

See [integrations/github-copilot/README.md](integrations/github-copilot/README.md) for details.
</details>

<details>
<summary><strong>Antigravity (Gemini)</strong></summary>

Each agent becomes a skill in `~/.gemini/antigravity/skills/agency-<slug>/`.

```bash
./scripts/install.sh --tool antigravity
```

Activate in Gemini with Antigravity:
```
@agency-frontend-developer review this React component
```

See [integrations/antigravity/README.md](integrations/antigravity/README.md) for details.
</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

Installs as a Gemini CLI extension with one skill per agent plus a manifest.

```bash
./scripts/install.sh --tool gemini-cli
```

See [integrations/gemini-cli/README.md](integrations/gemini-cli/README.md) for details.
</details>

<details>
<summary><strong>OpenCode</strong></summary>

Agents are placed in `.opencode/agents/` in your project root (project-scoped).

```bash
cd /your/project
/path/to/agency-agents/scripts/install.sh --tool opencode
```

Or install globally:
```bash
mkdir -p ~/.config/opencode/agents
cp integrations/opencode/agents/*.md ~/.config/opencode/agents/
```

Activate in OpenCode:
```
@backend-architect design this API.
```

See [integrations/opencode/README.md](integrations/opencode/README.md) for details.
</details>

<details>
<summary><strong>Cursor</strong></summary>

Each agent becomes a `.mdc` rule file in `.cursor/rules/` of your project.

```bash
cd /your/project
/path/to/agency-agents/scripts/install.sh --tool cursor
```

Rules are auto-applied when Cursor detects them in the project. Reference them explicitly:
```
Use the @security-engineer rules to review this code.
```

See [integrations/cursor/README.md](integrations/cursor/README.md) for details.
</details>

<details>
<summary><strong>Aider</strong></summary>

All agents are compiled into a single `CONVENTIONS.md` file that Aider reads automatically.

```bash
cd /your/project
/path/to/agency-agents/scripts/install.sh --tool aider
```

Then reference agents in your Aider session:
```
Use the general-purpose agent with /frontend to refactor this component.
```

See [integrations/aider/README.md](integrations/aider/README.md) for details.
</details>

<details>
<summary><strong>Windsurf</strong></summary>

All agents are compiled into `.windsurfrules` in your project root.

```bash
cd /your/project
/path/to/agency-agents/scripts/install.sh --tool windsurf
```

Reference agents in Windsurf's Cascade:
```
Use the general-purpose agent with /qa-only to verify this is production ready.
```

See [integrations/windsurf/README.md](integrations/windsurf/README.md) for details.
</details>

<details>
<summary><strong>OpenClaw</strong></summary>

Each agent becomes a workspace with `SOUL.md`, `AGENTS.md`, and `IDENTITY.md` in `~/.openclaw/agency-agents/`.

```bash
./scripts/install.sh --tool openclaw
```

Agents are registered and available by `agentId` in OpenClaw sessions.

See [integrations/openclaw/README.md](integrations/openclaw/README.md) for details.

</details>

---

### Regenerating After Changes

When you add new agents or edit existing ones, regenerate all integration files:

```bash
./scripts/convert.sh        # regenerate all
./scripts/convert.sh --tool cursor   # regenerate just one tool
```

---

## 🗺️ Roadmap

- [ ] Interactive agent selector web tool
- [x] Multi-agent workflow examples -- see [examples/](examples/)
- [x] Multi-tool integration scripts (Claude Code, GitHub Copilot, Antigravity, Gemini CLI, OpenCode, OpenClaw, Cursor, Aider, Windsurf)
- [ ] Video tutorials on agent design
- [ ] Community agent marketplace
- [ ] Agent "personality quiz" for project matching
- [ ] "Agent of the Week" showcase series

---

## 🌐 Community Translations & Localizations

Community-maintained translations and regional adaptations. These are independently maintained -- see each repo for coverage and version compatibility.

| Language | Maintainer | Link | Notes |
|----------|-----------|------|-------|
| 🇨🇳 简体中文 (zh-CN) | [@jnMetaCode](https://github.com/jnMetaCode) | [agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) | 100 translated agents + 9 China-market originals | <!-- check-counts:ignore: third-party repo -->

Want to add a translation? Open an issue and we'll link it here.

---

## 🔗 Related Resources

- [awesome-openclaw-agents](https://github.com/mergisi/awesome-openclaw-agents) — Community-maintained OpenClaw agent collection (derived from this repo)

---

## 📜 License

MIT License - Use freely, commercially or personally. Attribution appreciated but not required.

---

## 🙏 Acknowledgments

Born from a Reddit discussion about AI agent specialization. Thanks to the community for the feedback, requests, and inspiration.

Special recognition to the 50+ Redditors who requested this within the first 12 hours - you proved there's demand for real, specialized AI agent systems.

---

## 💬 Community

- **GitHub Discussions**: [Share your success stories](https://github.com/msitarzewski/agency-agents/discussions)
- **Issues**: [Report bugs or request features](https://github.com/msitarzewski/agency-agents/issues)
- **Reddit**: Join the conversation on r/ClaudeAI
- **Twitter/X**: Share with #TheAgency

---

## 🚀 Get Started

1. **Browse** the agents above and find specialists for your needs
2. **Copy** the agents to `~/.claude/agents/` for Claude Code integration
3. **Activate** agents by referencing them in your Claude conversations
4. **Customize** agent personalities and workflows for your specific needs
5. **Share** your results and contribute back to the community

---

## Agent Architecture

This directory contains **prompt-based agents** (personality + workflows in `.md` files) enhanced with **MCP (Model Context Protocol)** for tool integration and **A2A (Agent-to-Agent)** for service discovery.

**MCP Servers** (configured in `~/.claude/settings.json` `mcpServers`):
- `obsidian` — Long-term memory via Obsidian vault (remember, recall, rollback, search)
- `filesystem` — File system access for agent file operations
- `supabase` — Supabase/PostgreSQL database queries

**Tool Schemas** (`~/.claude/tools/`):
Each skill domain has a typed JSON Schema defining inputs/outputs. These provide machine-readable tool definitions so MCP clients can discover and invoke skill capabilities programmatically. See `backend.json`, `frontend.json`, `supabase.json`, `security.json`, `browser.json`, and `obsidian.json`.

**Agent Discovery (A2A)**:
Agent Cards at `~/.claude/.well-known/agent-card.json` expose The Agency's capabilities as action slugs. Remote agents can fetch the card at runtime to discover what The Agency agents can do without code-level integration.

**Transport Strategy**:
- **stdio**: Local tools embedded in Claude Opus (filesystem, supabase)
- **SSE**: Community MCP servers with OAuth (GitHub, Asana, Stripe)
- **Streamable HTTP**: Production deployments of custom MCP servers

**Protocol Reference**: MCP at `modelcontextprotocol.io`, A2A at `a2a.ai`

---

<div align="center">

**🎭 The Agency: Your AI Dream Team Awaits 🎭**

[⭐ Star this repo](https://github.com/msitarzewski/agency-agents) • [🍴 Fork it](https://github.com/msitarzewski/agency-agents/fork) • [🐛 Report an issue](https://github.com/msitarzewski/agency-agents/issues) • [❤️ Sponsor](https://github.com/sponsors/msitarzewski)

Made with ❤️ by the community, for the community

</div>

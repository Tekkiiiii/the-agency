# Role map: archived specialist agents -> general-purpose + skills

Since 2026-10-06 (generalist switch ACTIVE) these roles are NOT registered agent types.
Spawn them as `general-purpose` with 1-3 of the listed skills, and (when the role's expertise matters)
tell the agent to read its role file first. Example:

```
Agent({ subagent_type: "general-purpose", description: "...",
  prompt: "Role: read {agency-root}/agents-archive/generalist-2026-10-06/engineering/engineering-frontend-developer.md first.\nSkills: /frontend, /tailwind.\nTask: ..." })
```

Restore one: `mv {agency-root}/agents-archive/generalist-2026-10-06/<dept>/<file>.md {agency-root}/agents/<dept>/` (registers next session; in a git checkout use `git mv`).

Skills with a namespace prefix (for example `design:user-research`) come from Claude Code plugins, not from this repo's `skills/` directory.

| Role (old agent name) | Spawn as general-purpose + skills | Role file (was agents/<path>) |
|---|---|---|
| Ad Copywriter | copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/content-ad-copywriter.md` |
| Blog & Article Writer | content-creator, seo-aeo-best-practices | `agents-archive/generalist-2026-10-06/content-creation/content-blog-writer.md` |
| Case Study & Whitepaper Writer | content-creator, content-polish | `agents-archive/generalist-2026-10-06/content-creation/content-case-study-writer.md` |
| Content Director | content-critique, quality-loop-router | `agents-archive/generalist-2026-10-06/content-creation/content-director.md` |
| Content Editor | content-polish, humanizer-writing, proofreader | `agents-archive/generalist-2026-10-06/content-creation/content-editor.md` |
| Email Campaign Writer | copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/content-email-writer.md` |
| Landing Page Copywriter | copywriting, seo-aeo-best-practices | `agents-archive/generalist-2026-10-06/content-creation/content-landing-page-copywriter.md` |
| Newsletter & Editorial Writer | content-creator, content-polish | `agents-archive/generalist-2026-10-06/content-creation/content-newsletter-writer.md` |
| Presentation Creator | deck-narrative, marp | `agents-archive/generalist-2026-10-06/content-creation/content-presentation-creator.md` |
| Press & PR Writer | content-creator, content-polish | `agents-archive/generalist-2026-10-06/content-creation/content-press-writer.md` |
| Technical Writer (Content) | tech-writer, document-release | `agents-archive/generalist-2026-10-06/content-creation/content-technical-writer.md` |
| Video Producer | ffmpeg, video-use | `agents-archive/generalist-2026-10-06/content-creation/content-video-producer.md` |
| Video Script Writer | (no skill; role file only) | `agents-archive/generalist-2026-10-06/content-creation/content-video-script-writer.md` |
| Brand Guardian | brandkit (review: critique-brand agent) | `agents-archive/generalist-2026-10-06/design/design-brand-guardian.md` |
| Image Prompt Engineer | image-prompt-engineer, gpt-image-prompts | `agents-archive/generalist-2026-10-06/design/design-image-prompt-engineer.md` |
| Inclusive Visuals Specialist | image-prompt-engineer, design:accessibility-review | `agents-archive/generalist-2026-10-06/design/design-inclusive-visuals-specialist.md` |
| UI Designer | ui-ux-pro-max, impeccable | `agents-archive/generalist-2026-10-06/design/design-ui-designer.md` |
| UX Architect | ui-ux-pro-max, tailwind | `agents-archive/generalist-2026-10-06/design/design-ux-architect.md` |
| UX Researcher | design:user-research, design:research-synthesis | `agents-archive/generalist-2026-10-06/design/design-ux-researcher.md` |
| Visual Storyteller | excalidraw-diagram | `agents-archive/generalist-2026-10-06/design/design-visual-storyteller.md` |
| Whimsy Injector | emil-design-eng, css-animations | `agents-archive/generalist-2026-10-06/design/design-whimsy-injector.md` |
| AI Engineer | mcp-builder | `agents-archive/generalist-2026-10-06/engineering/engineering-ai-engineer.md` |
| Autonomous Optimization Architect | finops | `agents-archive/generalist-2026-10-06/engineering/engineering-autonomous-optimization-architect.md` |
| Backend Architect | backend, postgresql-schema, plan-eng-review | `agents-archive/generalist-2026-10-06/engineering/engineering-backend-architect.md` |
| Data Engineer | backend, postgresql-schema, xlsx-toolkit | `agents-archive/generalist-2026-10-06/engineering/engineering-data-engineer.md` |
| DevOps Automator | pipeline-deploy, vercel-deploy, railway-deploy | `agents-archive/generalist-2026-10-06/engineering/engineering-devops-automator.md` |
| Embedded Firmware Engineer | (no skill; role file only) | `agents-archive/generalist-2026-10-06/engineering/engineering-embedded-firmware-engineer.md` |
| Frontend Developer | frontend, next-best-practices, tailwind | `agents-archive/generalist-2026-10-06/engineering/engineering-frontend-developer.md` |
| Incident Response Commander | investigate, superpowers-systematic-debugging | `agents-archive/generalist-2026-10-06/engineering/engineering-incident-response-commander.md` |
| Mobile App Builder | frontend, imagegen-frontend-mobile | `agents-archive/generalist-2026-10-06/engineering/engineering-mobile-app-builder.md` |
| Rapid Prototyper | mattpocock-skills:prototype, frontend | `agents-archive/generalist-2026-10-06/engineering/engineering-rapid-prototyper.md` |
| Security Engineer | security, cso (review: critique-security agent) | `agents-archive/generalist-2026-10-06/engineering/engineering-security-engineer.md` |
| Senior Developer | laravel-builder, review | `agents-archive/generalist-2026-10-06/engineering/engineering-senior-developer.md` |
| Technical Writer | tech-writer, document-release | `agents-archive/generalist-2026-10-06/engineering/engineering-technical-writer.md` |
| Threat Detection Engineer | security, cso | `agents-archive/generalist-2026-10-06/engineering/engineering-threat-detection-engineer.md` |
| laravel-debugger | laravel-builder, investigate | `agents-archive/generalist-2026-10-06/engineering/laravel-debugger.md` |
| laravel-feature-builder | laravel-builder | `agents-archive/generalist-2026-10-06/engineering/laravel-feature-builder.md` |
| laravel-simplifier | laravel-builder | `agents-archive/generalist-2026-10-06/engineering/laravel-simplifier.md` |
| Experiment Tracker | content-experimentation-best-practices, project-status | `agents-archive/generalist-2026-10-06/project-management/project-management-experiment-tracker.md` |
| Jira Workflow Steward | superpowers-finishing-a-development-branch, ship | `agents-archive/generalist-2026-10-06/project-management/project-management-jira-workflow-steward.md` |
| Project Shepherd | project-status | `agents-archive/generalist-2026-10-06/project-management/project-management-project-shepherd.md` |
| Studio Operations | project-status | `agents-archive/generalist-2026-10-06/project-management/project-management-studio-operations.md` |
| Studio Producer | project-status | `agents-archive/generalist-2026-10-06/project-management/project-management-studio-producer.md` |
| Senior Project Manager | superpowers-writing-plans | `agents-archive/generalist-2026-10-06/project-management/project-manager-senior.md` |
| Accounts Payable Agent | (no skill; role file only) | `agents-archive/generalist-2026-10-06/specialized/accounts-payable-agent.md` |
| Job Portal Scanner | career-ops | `agents-archive/generalist-2026-10-06/specialized/career-job-portal-scanner.md` |
| Data Consolidation Agent | xlsx-toolkit | `agents-archive/generalist-2026-10-06/specialized/data-consolidation-agent.md` |
| Efficiency Advisor Loop | project-status, health | `agents-archive/generalist-2026-10-06/specialized/efficiency-advisor-loop.md` |
| integration-tester | qa-only, run-acceptance-tests, webapp-testing | `agents-archive/generalist-2026-10-06/specialized/integration-tester.md` |
| PD Status Loop | project-status | `agents-archive/generalist-2026-10-06/specialized/pd-status-loop.md` |
| Project Expansion Scout | project-expansion-scout | `agents-archive/generalist-2026-10-06/specialized/project-expansion-scout.md` |
| Report Distribution Agent | xlsx-toolkit | `agents-archive/generalist-2026-10-06/specialized/report-distribution-agent.md` |
| Sales Data Extraction Agent | xlsx-toolkit | `agents-archive/generalist-2026-10-06/specialized/sales-data-extraction-agent.md` |
| CLI-Anything Agent | cli-anything | `agents-archive/generalist-2026-10-06/specialized/specialized-cli-anything-agent.md` |
| Cultural Intelligence Strategist | design:accessibility-review | `agents-archive/generalist-2026-10-06/specialized/specialized-cultural-intelligence-strategist.md` |
| Developer Advocate | tech-writer, content-creator | `agents-archive/generalist-2026-10-06/specialized/specialized-developer-advocate.md` |
| Paperclip Control Plane | project-status | `agents-archive/generalist-2026-10-06/specialized/specialized-paperclip-control-plane.md` |
| Vietnamese Text Agent | vietnamese-language, style-guide-vi | `agents-archive/generalist-2026-10-06/specialized/specialized-vietnamese-text-agent.md` |
| task-planner | superpowers-writing-plans | `agents-archive/generalist-2026-10-06/specialized/task-planner.md` |
| Web Extraction Agent | lightpanda, scrape, firecrawl-crawl | `agents-archive/generalist-2026-10-06/specialized/web-extraction-agent.md` |
| ZK Steward | obsidian-vault, notebooklm-memory | `agents-archive/generalist-2026-10-06/specialized/zk-steward.md` |
| qa-task-contract | (not an agent: the QA dispatch contract doc, moved to `runbooks/qa-task-contract.md`) | n/a |
| Accessibility Auditor | design:accessibility-review, qa-only | `agents-archive/generalist-2026-10-06/testing/testing-accessibility-auditor.md` |
| API Tester | qa-only, webapp-testing | `agents-archive/generalist-2026-10-06/testing/testing-api-tester.md` |
| Evidence Collector | qa-only, browse, webapp-testing | `agents-archive/generalist-2026-10-06/testing/testing-evidence-collector.md` |
| Performance Benchmarker | benchmark, web-perf | `agents-archive/generalist-2026-10-06/testing/testing-performance-benchmarker.md` |
| Reality Checker | qa-only | `agents-archive/generalist-2026-10-06/testing/testing-reality-checker.md` |
| Test Results Analyzer | qa-only | `agents-archive/generalist-2026-10-06/testing/testing-test-results-analyzer.md` |
| Tool Evaluator | auto-researcher | `agents-archive/generalist-2026-10-06/testing/testing-tool-evaluator.md` |
| Workflow Optimizer | workflow-critique | `agents-archive/generalist-2026-10-06/testing/testing-workflow-optimizer.md` |
| Video Accessibility Auditor | subtitle-burner, design:accessibility-review | `agents-archive/generalist-2026-10-06/video-studio/vs-accessibility-auditor.md` |
| AI Video Producer | (no skill; role file only) | `agents-archive/generalist-2026-10-06/video-studio/vs-ai-video-producer.md` |
| Animation Director | remotion-best-practices, hyperframes | `agents-archive/generalist-2026-10-06/video-studio/vs-animation-director.md` |
| Captioning Specialist | subtitle-burner, ffmpeg | `agents-archive/generalist-2026-10-06/video-studio/vs-captioning-specialist.md` |
| Colorist & Audio Engineer | ffmpeg | `agents-archive/generalist-2026-10-06/video-studio/vs-colorist-audio-engineer.md` |
| Platform Formatter | ffmpeg | `agents-archive/generalist-2026-10-06/video-studio/vs-platform-formatter.md` |
| Screen Recording Director | video-use | `agents-archive/generalist-2026-10-06/video-studio/vs-screen-recording-director.md` |
| Shot Planner | (no skill; role file only) | `agents-archive/generalist-2026-10-06/video-studio/vs-shot-planner.md` |
| Storyboard Artist | (no skill; role file only) | `agents-archive/generalist-2026-10-06/video-studio/vs-storyboard-artist.md` |
| Thumbnail Designer | image-prompt-engineer | `agents-archive/generalist-2026-10-06/video-studio/vs-thumbnail-designer.md` |
| Upload Automator | n8n-automation | `agents-archive/generalist-2026-10-06/video-studio/vs-upload-automator.md` |
| VFX & Motion Designer | hyperframes, gsap | `agents-archive/generalist-2026-10-06/video-studio/vs-vfx-motion-designer.md` |
| Video Editor | video-use, ffmpeg | `agents-archive/generalist-2026-10-06/video-studio/vs-video-editor.md` |
| Video Quality Reviewer | ffmpeg (review: critique-video agent) | `agents-archive/generalist-2026-10-06/video-studio/vs-video-quality-reviewer.md` |
| Video SEO Specialist | seo-aeo-best-practices | `agents-archive/generalist-2026-10-06/video-studio/vs-video-seo-specialist.md` |
| Voice & Cast Director | (no skill; role file only) | `agents-archive/generalist-2026-10-06/video-studio/vs-voice-director.md` |
| Discord Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-discord-writer.md` |
| Facebook Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-facebook-writer.md` |
| Instagram Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-instagram-writer.md` |
| LinkedIn Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-linkedin-writer.md` |
| Pinterest Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-pinterest-writer.md` |
| Quora Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-quora-writer.md` |
| Reddit Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-reddit-writer.md` |
| Telegram Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-telegram-writer.md` |
| Threads Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-threads-writer.md` |
| TikTok Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-tiktok-writer.md` |
| Twitter/X Writer | content-creator, copywriting, content-polish | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-twitter-writer.md` |
| YouTube Writer | content-creator, seo-aeo-best-practices | `agents-archive/generalist-2026-10-06/content-creation/social-media/content-youtube-writer.md` |
| Backend Architect (MCP-memory example) | backend, postgresql-schema | `agents-archive/generalist-2026-10-06/integrations/mcp-memory/backend-architect-with-memory.md` |
| Compliance Auditor | security, legal-contract-review | `agents-archive/generalist-2026-10-06/specialized/audit/compliance-auditor.md` |
| Model QA Specialist | (no skill; role file only) | `agents-archive/generalist-2026-10-06/specialized/audit/specialized-model-qa.md` |
| Agentic Identity & Trust Architect | security | `agents-archive/generalist-2026-10-06/specialized/infra/agentic-identity-trust.md` |
| Agents Orchestrator | superpowers-subagent-driven-development, superpowers-dispatching-parallel-agents | `agents-archive/generalist-2026-10-06/specialized/infra/agents-orchestrator.md` |
| Identity Graph Operator | backend | `agents-archive/generalist-2026-10-06/specialized/infra/identity-graph-operator.md` |
| LSP/Index Engineer | (no skill; role file only) | `agents-archive/generalist-2026-10-06/specialized/infra/lsp-index-engineer.md` |
| RoomManager | room-manager | `agents-archive/generalist-2026-10-06/specialized/infra/room-manager.md` |

| task-executor (retired 2026-10-08) | general-purpose + Skills of the task; spawn template coord.md "Exec spawn message" |

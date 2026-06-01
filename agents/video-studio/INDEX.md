# Video Studio Department

**Call this department when you need to produce, edit, format, or distribute any video content** — tutorials, product demos, social videos, explainers, AI-generated clips, or animated content. This is the default department for ALL video production tasks across the agency.

**Leader**: Video Studio Director
**Model tier**: Members = Sonnet, Leader = Opus

**Cross-dept relationships**:
- **Content Creation** → script handoff (content-video-script-writer → Video Studio Director)
- **Design** → brand guardrails and visual identity for all video assets
- **Marketing** → distribution strategy and platform targeting input

---

## Leadership

| Agent | File | What it does |
|---|---|---|
| Video Studio Director | `video-studio-lead.md` | Department orchestration, quality governance, council representation |
| Video Studio Dept-Coord | `video-studio-coord.md` | D3 task owner for dept-operational tracks |

---

## Pre-Production

| Agent | File | What it produces |
|---|---|---|
| Storyboard Artist | `vs-storyboard-artist.md` | Visual storyboards, scene cards (pose + VO + sticker), production complexity flags |
| Shot Planner | `vs-shot-planner.md` | Shot list, B-roll list, production order, dependency map |
| Voice & Cast Director | `vs-voice-director.md` | Voice direction notes, AI voice prompts, casting briefs, pronunciation guides |

---

## Production

| Agent | File | What it produces |
|---|---|---|
| Screen Recording Director | `vs-screen-recording-director.md` | Browser/app screen captures, UI state recordings |
| AI Video Producer | `vs-ai-video-producer.md` | AI-generated clips via Higgsfield, Veo, Sora, Runway |
| Animation Director | `vs-animation-director.md` | Motion graphics, title cards, lower thirds, data animations (Remotion, Hyperframes, Lottie, GSAP) |

---

## Post-Production

| Agent | File | What it produces |
|---|---|---|
| Video Editor | `vs-video-editor.md` | Assembled rough/fine cut, audio sync, pacing, timeline |
| VFX & Motion Designer | `vs-vfx-motion-designer.md` | Kinetic typography, VFX polish, data visualizations, hook frame |
| Colorist & Audio Engineer | `vs-colorist-audio-engineer.md` | Color grade, audio master, loudness normalization (-14 LUFS) |
| Captioning Specialist | `vs-captioning-specialist.md` | .srt / .vtt captions (Whisper + correction), burned-in captions for short-form |
| Thumbnail Designer | `vs-thumbnail-designer.md` | 3-variant thumbnails per platform, CTR-optimized |

---

## Distribution

| Agent | File | What it produces |
|---|---|---|
| Platform Formatter | `vs-platform-formatter.md` | Platform-specific video files (YouTube 16:9, TikTok 9:16, Reels, Shorts, LinkedIn) |
| Video SEO Specialist | `vs-video-seo-specialist.md` | Title variants, description, tags, chapters, JSON-LD schema |
| Upload Automator | `vs-upload-automator.md` | Automated upload + scheduling via n8n + YouTube/TikTok/Instagram APIs |

---

## QA

| Agent | File | What it checks |
|---|---|---|
| Video Quality Reviewer | `vs-video-quality-reviewer.md` | Technical, content, brand compliance gate (score 0-100, SHIP/FIX/REDO) |
| Video Accessibility Auditor | `vs-accessibility-auditor.md` | WCAG 2.1 AA: captions, audio description, text contrast, player a11y |

---

## Skills Assigned to This Department

**Core production**: `video-use`, `ffmpeg`, `hyperframes`, `hyperframes-media`, `hyperframes-cli`, `hyperframes-registry`

**AI generation**: `higgsfield-stickman-video`, `imagegen-frontend-web`, `imagegen-frontend-mobile`, `gpt-image-prompts`

**Animation**: `remotion-best-practices`, `remotion-to-hyperframes`, `lottie`, `gsap`, `css-animations`, `animejs`

**Browser/capture**: `browse`, `agent-browser`

**Quality**: `design-critique`, `content-critique`, `critique-video` (NEW — video-specific scoring), `quality-loop-router` (NEW — mandatory terminal step before delivery)

**Distribution**: `n8n-automation`, `gws`, `seo-aeo-best-practices`

---

## Protocols

- `protocols/content-to-video.md` — script handoff from Content Creation department
- `agents/runbooks/content-to-video-protocol.md` — agency-wide cross-dept protocol
- `agents/runbooks/quality-loop-protocol.md` — quality gate protocol; quality-loop-router applies this at the terminal step

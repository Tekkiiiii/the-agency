# Video Studio Department

**Call this department when you need to produce, edit, format, or distribute any video content** — tutorials, product demos, social videos, explainers, AI-generated clips, or animated content. This is the default department for ALL video production tasks across the agency.

**Leader**: Video Studio Director
**Model tier**: Members = general-purpose (Sonnet), Leader = Opus

> Member roles below are archived (2026-10-06). Spawn each as `general-purpose` + the listed skills; the role file is read-first context. Full map: `{agency-root}/agents-archive/ROLE-MAP.md`.

**Cross-dept relationships**:
- **Content Creation** → script handoff (video script writer role: general-purpose → Video Studio Director)
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

| Role | Spawn as | What it produces |
|---|---|---|
| storyboard artist | general-purpose (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-storyboard-artist.md`) | Visual storyboards, scene cards (pose + VO + sticker), production complexity flags |
| shot planner | general-purpose (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-shot-planner.md`) | Shot list, B-roll list, production order, dependency map |
| voice & cast director | general-purpose (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-voice-director.md`) | Voice direction notes, AI voice prompts, casting briefs, pronunciation guides |

---

## Production

| Role | Spawn as | What it produces |
|---|---|---|
| screen recording director | general-purpose + /video-use (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-screen-recording-director.md`) | Browser/app screen captures, UI state recordings |
| ai video producer | general-purpose (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-ai-video-producer.md`) | AI-generated clips via Higgsfield, Veo, Sora, Runway |
| animation director | general-purpose + /remotion-best-practices, /hyperframes (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-animation-director.md`) | Motion graphics, title cards, lower thirds, data animations (Remotion, Hyperframes, Lottie, GSAP) |

---

## Post-Production

| Role | Spawn as | What it produces |
|---|---|---|
| video editor | general-purpose + /video-use, /ffmpeg (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-video-editor.md`) | Assembled rough/fine cut, audio sync, pacing, timeline |
| vfx & motion designer | general-purpose + /hyperframes, /gsap (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-vfx-motion-designer.md`) | Kinetic typography, VFX polish, data visualizations, hook frame |
| colorist & audio engineer | general-purpose + /ffmpeg (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-colorist-audio-engineer.md`) | Color grade, audio master, loudness normalization (-14 LUFS) |
| captioning specialist | general-purpose + /subtitle-burner, /ffmpeg (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-captioning-specialist.md`) | .srt / .vtt captions (Whisper + correction), burned-in captions for short-form |
| thumbnail designer | general-purpose + /image-prompt-engineer (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-thumbnail-designer.md`) | 3-variant thumbnails per platform, CTR-optimized |

---

## Distribution

| Role | Spawn as | What it produces |
|---|---|---|
| platform formatter | general-purpose + /ffmpeg (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-platform-formatter.md`) | Platform-specific video files (YouTube 16:9, TikTok 9:16, Reels, Shorts, LinkedIn) |
| video seo specialist | general-purpose + /seo-aeo-best-practices (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-video-seo-specialist.md`) | Title variants, description, tags, chapters, JSON-LD schema |
| upload automator | general-purpose + /n8n-automation (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-upload-automator.md`) | Automated upload + scheduling via n8n + YouTube/TikTok/Instagram APIs |

---

## QA

| Role | Spawn as | What it checks |
|---|---|---|
| video quality review | `critique-video` agent (kept; use /ffmpeg for technical probes; legacy role file: `agents-archive/generalist-2026-10-06/video-studio/vs-video-quality-reviewer.md`) | Technical, content, brand compliance gate (score 0-100, SHIP/FIX/REDO) |
| video accessibility auditor | general-purpose + /subtitle-burner (role file: `agents-archive/generalist-2026-10-06/video-studio/vs-accessibility-auditor.md`) | WCAG 2.1 AA: captions, audio description, text contrast, player a11y |

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
- `runbooks/content-to-video-protocol.md` — agency-wide cross-dept protocol
- `runbooks/quality-loop-protocol.md` — quality gate protocol; quality-loop-router applies this at the terminal step

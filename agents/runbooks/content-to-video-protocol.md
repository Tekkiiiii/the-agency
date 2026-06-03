# Agency Protocol: Content Creation → Video Studio
# Version 1.0 | 2026-05-31

## Purpose

This protocol governs all video production tasks across the agency. It defines:
- Routing rule (what triggers Video Studio involvement)
- Handoff requirements (what Content Creation must provide)
- Production protocol (what Video Studio executes)
- Return artifacts (what is delivered)
- Revision and escalation paths

---

## Routing Rule

**Any task involving video production routes to Video Studio by default.**

Content Creation is responsible for scripts. Video Studio is responsible for everything after: storyboard, production, post-production, distribution.

| Trigger | Routes To |
|---|---|
| "write a video script" | Content Creation → content-video-script-writer |
| "make a video", "produce a video", "edit a video" | Video Studio → video-studio-lead |
| "create a YouTube video", "make a TikTok" | Video Studio → video-studio-lead |
| "animate", "motion graphics" | Video Studio → vs-animation-director |
| "thumbnail" | Video Studio → vs-thumbnail-designer |
| "transcribe video", "add captions" | Video Studio → vs-captioning-specialist |
| "upload video to YouTube" | Video Studio → vs-upload-automator |
| "optimize video for SEO" | Video Studio → vs-video-seo-specialist |

---

## End-to-End Production Flow

```
CONTENT CREATION DEPT
  └─ content-video-script-writer
       └─ Delivers: final script + voice direction + key messages + CTA

         ↓ [HANDOFF — via inter-spawn or direct brief]

VIDEO STUDIO DEPT
  ├─ Pre-production
  │    ├─ vs-storyboard-artist (scene cards from script)
  │    ├─ vs-shot-planner (production plan)
  │    └─ vs-voice-director (voice notes, AI voice prompts)
  │
  ├─ Production (parallel where possible)
  │    ├─ vs-screen-recording-director (screen captures)
  │    ├─ vs-ai-video-producer (AI-generated clips)
  │    └─ vs-animation-director (motion graphics, titles)
  │
  ├─ Post-production
  │    ├─ vs-video-editor (assembly, rough → fine cut)
  │    ├─ vs-vfx-motion-designer (motion polish)
  │    ├─ vs-colorist-audio-engineer (color + audio master)
  │    ├─ vs-captioning-specialist (SRT + VTT + burned-in)
  │    └─ vs-thumbnail-designer (3 variants)
  │
  ├─ QA gate (MANDATORY before distribution)
  │    ├─ vs-video-quality-reviewer (technical + content + brand)
  │    └─ vs-accessibility-auditor (WCAG 2.1 AA)
  │
  └─ Distribution
       ├─ vs-platform-formatter (per-platform video files)
       ├─ vs-video-seo-specialist (title, desc, tags, chapters)
       └─ vs-upload-automator (scheduled upload + confirmation)
```

---

## Handoff Requirements (Content Creation → Video Studio)

| Required | Notes |
|---|---|
| Final approved script | Must be final. Draft scripts are rejected with NACK. |
| Voice/tone direction | Casual / educational / formal. Delivery pace. |
| Top 3 key messages | These must be visually reinforced |
| CTA specification | Action + destination URL |
| Target platforms | Required for format planning |
| Brand asset pack | Logo (SVG/PNG), brand colors (hex), fonts |

Missing any required item → Video Studio Director sends NACK to content-video-script-writer before production starts.

---

## QA Gate

All videos pass through vs-video-quality-reviewer before distribution.

| Score | Action |
|---|---|
| 90-100 | SHIP — proceed to distribution |
| 70-89 | SHIP WITH NOTES — distribute, log minor fixes for next revision |
| 50-69 | FIX FIRST — specific items resolved before distributing |
| < 50 | REDO — major issues, return to post-production |

---

## Escalation

| Situation | Escalation Path |
|---|---|
| Script unclear / incomplete | NACK to content-video-script-writer |
| Brand assets missing | Request from Design dept via inter-spawn |
| AI video fails 3+ iterations | Escalate to vs-ai-video-producer → video-studio-lead → human |
| Platform API failure on upload | Log, retry x2, then escalate to user |
| Score < 50 after redo | Escalate to video-studio-lead + parent AI |

---

## Related Files

- `agents/video-studio/INDEX.md` — department member directory
- `agents/video-studio/protocols/content-to-video.md` — Video Studio side
- `agents/content-creation/INDEX.md` — Content Creation side
- `agents/content-creation/content-video-script-writer.md` — upstream script agent

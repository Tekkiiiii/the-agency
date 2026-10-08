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
| "write a video script" | Content Creation → video script writer role (general-purpose + /youtube-narration, /video-prompt-director) |
| "make a video", "produce a video", "edit a video" | Video Studio → video-studio-lead |
| "create a YouTube video", "make a TikTok" | Video Studio → video-studio-lead |
| "animate", "motion graphics" | Video Studio → animation role (general-purpose + /remotion-best-practices, /hyperframes) |
| "thumbnail" | Video Studio → thumbnail role (general-purpose + /image-prompt-engineer, /social-render) |
| "transcribe video", "add captions" | Video Studio → captioning role (general-purpose + /subtitle-burner, /ffmpeg) |
| "upload video to YouTube" | Video Studio → upload role (general-purpose + /n8n-automation) |
| "optimize video for SEO" | Video Studio → video SEO role (general-purpose + /seo-aeo-best-practices) |

---

## End-to-End Production Flow

Video Studio member roles are archived (2026-10-06): each step is spawned as `general-purpose` + the listed skills, reading its role file from `agents-archive/generalist-2026-10-06/video-studio/` first. Map: `{agency-root}/agents-archive/ROLE-MAP.md`.

```
CONTENT CREATION DEPT
  └─ video script writer (general-purpose + /youtube-narration, /video-prompt-director)
       └─ Delivers: final script + voice direction + key messages + CTA

         ↓ [HANDOFF — via inter-spawn or direct brief]

VIDEO STUDIO DEPT
  ├─ Pre-production
  │    ├─ storyboard (/video-shotcraft, /video-prompt-director; scene cards from script)
  │    ├─ shot planner (/video-shotcraft; production plan)
  │    └─ voice director (/youtube-narration; voice notes, AI voice prompts)
  │
  ├─ Production (parallel where possible)
  │    ├─ screen recording (/video-use; screen captures)
  │    ├─ AI video (/higgsfield-functions, /video-prompt-director; AI-generated clips)
  │    └─ animation (/remotion-best-practices, /hyperframes, /motion-canvas; motion graphics, titles)
  │
  ├─ Post-production
  │    ├─ video editor (/video-use, /ffmpeg; assembly, rough → fine cut)
  │    ├─ VFX and motion (/hyperframes, /html-video, /gsap; motion polish)
  │    ├─ color + audio (/ffmpeg; color + audio master)
  │    ├─ captioning (/subtitle-burner, /ffmpeg; SRT + VTT + burned-in)
  │    └─ thumbnails (/image-prompt-engineer, /social-render; 3 variants)
  │
  ├─ QA gate (MANDATORY before distribution)
  │    ├─ critique-video agent (kept; technical + content + brand)
  │    └─ accessibility audit (/subtitle-burner, /design:accessibility-review; WCAG 2.1 AA)
  │
  └─ Distribution
       ├─ platform formatter (/ffmpeg, /social-render; per-platform video files)
       ├─ video SEO (/seo-aeo-best-practices; title, desc, tags, chapters)
       └─ upload automation (/n8n-automation; scheduled upload + confirmation)
```

---

## Handoff Requirements (Content Creation → Video Studio)

| Required | Notes |
|---|---|
| Final approved script | Must be final. Draft scripts are rejected (NACK: requester spawns a continuation script writer with the fix list). |
| Voice/tone direction | Casual / educational / formal. Delivery pace. |
| Top 3 key messages | These must be visually reinforced |
| CTA specification | Action + destination URL |
| Target platforms | Required for format planning |
| Brand asset pack | Logo (SVG/PNG), brand colors (hex), fonts |

Missing any required item → Video Studio Director rejects the handoff in its report before production starts (NACK; requester spawns a continuation general-purpose script writer with the fix list).

---

## QA Gate

All videos pass through the `critique-video` agent before distribution.

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
| Script unclear / incomplete | NACK: requester spawns a continuation script writer (general-purpose + skills) with the fix list |
| Brand assets missing | Request from Design dept via inter-spawn |
| AI video fails 3+ iterations | Escalate to the AI video role → video-studio-lead → human |
| Platform API failure on upload | Log, retry x2, then escalate to user |
| Score < 50 after redo | Escalate to video-studio-lead + parent AI |

---

## Related Files

- `agents/video-studio/INDEX.md` — department member directory
- `agents/video-studio/protocols/content-to-video.md` — Video Studio side
- `agents/content-creation/INDEX.md` — Content Creation side
- `agents-archive/generalist-2026-10-06/content-creation/content-video-script-writer.md` — upstream script role file (archived; spawn general-purpose + /youtube-narration, /video-prompt-director)

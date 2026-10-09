# Agency Protocol: Content Script → Video Production
# Version 2.0 | 2026-10-08 (dept sunset; folded the Video Studio-side handoff protocol)

## Purpose

This protocol governs all video production tasks across the agency. It defines:
- Routing rule (what triggers a video production track)
- Handoff requirements (what the content pipeline must provide)
- Production protocol (what the video track executes)
- Return artifacts (what is delivered)
- Revision and escalation paths

---

## Routing Rule

**Any task involving video production runs as its own production track under a Coord (PD -> Coord -> `general-purpose` Execs + skills).**

The script comes from the content pipeline (`content-request-protocol.md`). The video track covers everything after the approved script: storyboard, production, post-production, distribution.

| Trigger | Spawn as `general-purpose` + skills |
|---|---|
| "write a video script" | script writer: /youtube-narration, /video-prompt-director (content pipeline) |
| "make a video", "produce a video", "edit a video", "create a YouTube video", "make a TikTok" | video track under a Coord (flow below) |
| "animate", "motion graphics" | animation: /remotion-best-practices, /hyperframes |
| "thumbnail" | thumbnail: /image-prompt-engineer, /social-render |
| "transcribe video", "add captions" | captioning: /subtitle-burner, /ffmpeg |
| "upload video to YouTube" | upload: /n8n-automation |
| "optimize video for SEO" | video SEO: /seo-aeo-best-practices |

---

## End-to-End Production Flow

Each step is a `general-purpose` Exec with the listed skills, reading its role file from `agents-archive/generalist-2026-10-06/video-studio/` first. Map: `{agency-root}/agents-archive/ROLE-MAP.md`.

```
CONTENT PIPELINE (content-request-protocol.md)
  └─ video script writer (general-purpose + /youtube-narration, /video-prompt-director)
       └─ Delivers: final script + voice direction + key messages + CTA

         ↓ [HANDOFF: task file / brief from the Coord]

VIDEO TRACK (Coord + Execs)
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
  │    ├─ critique-video agent (technical + content + brand)
  │    └─ accessibility audit (/subtitle-burner, /design:accessibility-review; WCAG 2.1 AA)
  │
  └─ Distribution
       ├─ platform formatter (/ffmpeg, /social-render; per-platform video files)
       ├─ video SEO (/seo-aeo-best-practices; title, desc, tags, chapters)
       └─ upload automation (/n8n-automation; scheduled upload + confirmation)
```

---

## Handoff Requirements (script -> video track)

| Required | Notes |
|---|---|
| Final approved script | Must be final. Draft scripts are rejected (NACK: the Coord spawns a continuation script writer with the fix list). |
| Voice/tone direction | Casual / educational / formal. Delivery pace. |
| Top 3 key messages | These must be visually reinforced |
| CTA specification | Action + destination URL |
| Target platforms | YouTube / TikTok / Reels / Shorts / LinkedIn; required for format planning |
| Brand asset pack | Logo (SVG/PNG), brand colors (hex), fonts |
| Reference videos | Optional; "look like this" examples help |
| Max duration | Optional; platform defaults apply |

Missing any required item -> the Coord rejects the handoff in its report before production starts (NACK; the spawner spawns a continuation general-purpose script writer with the fix list). Do NOT start production on an unacceptable script (unclear, incomplete, or contradicting brand guidelines).

## Deliverables

| Artifact | Format | Timeline |
|---|---|---|
| Final video files (per platform) | MP4, platform-spec | Per agreed schedule |
| Thumbnail assets | JPG/WebP, platform dimensions | Same as video |
| Caption files | .srt + .vtt | Same as video |
| Metadata pack | Markdown (title, desc, tags, chapters) | Same as video |
| Upload confirmation | URL + scheduled time | Within 24h of upload |

## Revision Protocol

2 revision rounds are included after fine cut delivery.
- **Round 1 (content revision):** messaging, pacing, script edits -> back to the video editor role (general-purpose + /video-use, /ffmpeg).
- **Round 2 (polish revision):** color, audio level, caption corrections -> back to the color/audio or captioning role.
- **Out of scope:** script rewrites after production starts (back to the content pipeline); AI video regeneration after 3 iterations (escalate to the PD).

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
| Script unclear / incomplete | NACK: Coord spawns a continuation script writer (general-purpose + skills) with the fix list |
| Brand assets missing | Request from the PD / design track via the Coord (inter-spawn task file if another project owns them) |
| AI video fails 3+ iterations | Coord -> PD -> human |
| Platform API failure on upload | Log, retry x2, then escalate to user |
| Score < 50 after redo | Coord -> PD + parent AI |

---

## Related Files

- `content-request-protocol.md` - the content pipeline that produces the script
- `agents-archive/ROLE-MAP.md` - role-to-skills map for every step above
- `agents-archive/generalist-2026-10-06/content-creation/content-video-script-writer.md` - upstream script role file (archived; spawn general-purpose + /youtube-narration, /video-prompt-director)

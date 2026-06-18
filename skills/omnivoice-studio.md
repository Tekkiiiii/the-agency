---
name: omnivoice-studio
description: >
  Zero-shot TTS, voice cloning, and video dubbing via OmniVoice Studio.
  646 languages, Apple Silicon native (MPS + mlx-audio), on-demand backend lifecycle.
  Default voice tool for all voice generation, voice cloning, TTS, and dubbing tasks.
  Handles backend boot/shutdown, MCP invocation, room-tone bedding, and voice profile management.
  Trigger phrases: "generate voice", "voice clone", "TTS", "text to speech", "dub this",
  "voice over", "voiceover", "generate audio", "synthesize speech".
---

# OmniVoice Studio

OmniVoice Studio is the **default tool for all voice generation, voice cloning, TTS, and dubbing tasks** in this system.

- Source: `~/.agents/skills/omnivoice-studio/` (git clone, tracked)
- Backed by [debpalash/OmniVoice-Studio](https://github.com/debpalash/OmniVoice-Studio) (~6.6k stars, v0.3.5, active beta)
- 646 languages (ISO 639 codes or Auto-detect)
- Apple Silicon native: MPS + mlx-audio (Kokoro, CSM, Dia, Qwen3-TTS, etc.)
- Bundled engines: OmniVoice default (zero-shot clone), mlx-audio, WhisperX ASR, KittenTTS (fast English ONNX), AudioSeal watermarking

---

## When to Invoke This Skill

Invoke when the task involves any of:
- Text-to-speech (TTS) generation
- Voice cloning from a reference recording
- Video dubbing or audio replacement
- Voiceover generation for any content
- Voice profile creation or management

---

## Backend Lifecycle — MANDATORY

The backend loads ~2.4GB of model weights. It is **NOT always-on**. Every voice task MUST follow this lifecycle:

```bash
# 1. Boot (first boot of a session is slower — wait for health check)
~/.agents/skills/omnivoice-studio/bin/omnivoicectl up

# 2. Check status
~/.agents/skills/omnivoice-studio/bin/omnivoicectl status   # returns: up | down

# 3. Generate via MCP (see below) — hold backend up while user reviews the output

# 4. Shut down AFTER the output is approved (never leave running)
~/.agents/skills/omnivoice-studio/bin/omnivoicectl down
```

Never leave the backend running after a task is approved. Always verify with `omnivoicectl status` if unsure.

---

## MCP Tools (backend must be up)

Registered as `omnivoice` in `~/.claude/settings.json`. Tools are available as `mcp__omnivoice__*`:

```
mcp__omnivoice__generate_speech
  text: "The text to synthesize."
  language: "en"          # or "Auto" for auto-detect, or any ISO 639 code
  steps: 8                # 8=fast, 16=balanced, 32=quality
  profile_id: "<id>"      # optional — omit for zero-shot, provide for voice clone

mcp__omnivoice__list_voices        # list saved voice profiles
mcp__omnivoice__list_languages     # all 646 supported languages
mcp__omnivoice__list_personalities # style presets (narrator, casual, formal, etc.)
mcp__omnivoice__check_health       # verify backend is responding
```

---

## API Fallback (if MCP unavailable)

```bash
# Generate speech — returns WAV file
curl -X POST http://localhost:3900/generate \
  -F "text=Hello world" \
  -F "language=en" \
  -F "num_step=8" \
  -o output.wav

# With voice profile
curl -X POST http://localhost:3900/generate \
  -F "text=Hello world" \
  -F "language=en" \
  -F "num_step=8" \
  -F "profile_id=<your-profile-id>" \
  -o output.wav
```

---

## Voice Profiles

Use `mcp__omnivoice__list_voices` to see saved profiles. Clone a voice from a reference recording (30–60s of clean audio) to create a new profile. Store profile IDs in your project memory for reuse.

---

## Room-Tone Bedding — MANDATORY Final Step

OmniVoice (and all TTS engines) produce near-digital silence during pauses — an audible AI tell. After the audio is approved, apply room-tone bedding before delivery:

```bash
~/.agents/skills/omnivoice-studio/bin/add-roomtone.sh <input.wav> <output-roomtone.wav> [gain_offset_db]
```

This script layers real captured room ambience under the speech. It does NOT require the backend — ffmpeg only.

**Gain offset guide (DEFAULT: -10):**
- `-10` → floor ~-60 dB (BASELINE — matches voice's inherent ambience)
- `-13` → quieter floor
- `-5` → more present floor

Provide your own `roomtone.wav` (record ~30s of silence in the room where the reference voice was captured).

---

## Full Session Workflow

```
1. omnivoicectl up
2. mcp__omnivoice__check_health → confirm up
3. mcp__omnivoice__generate_speech  (with profile_id if voice clone needed)
4. [hold backend] → play output for user review
5. On approval: add-roomtone.sh input.wav output-roomtone.wav -10
6. Deliver output-roomtone.wav
7. omnivoicectl down
```

---

## Steps Reference

| Step | Quality | Use For |
|---|---|---|
| 8 | Fast | Drafts, quick previews |
| 16 | Balanced | Review takes |
| 32 | Quality | Final master |

---

## MCP Registration (reference)

Add to `~/.claude/settings.json` under `mcpServers.omnivoice`:

```json
{
  "command": "/path/to/.agents/skills/omnivoice-studio/.venv/bin/python",
  "args": ["-m", "backend.mcp_server"],
  "cwd": "/path/to/.agents/skills/omnivoice-studio",
  "env": { "OMNIVOICE_API_URL": "http://localhost:3900" }
}
```

Replace `/path/to/` with the actual clone path (typically `~/.agents/skills/`).

Transport: stdio. The MCP server is a proxy — it requires the FastAPI backend (`omnivoicectl up`) before any `mcp__omnivoice__*` tool calls will succeed.

---

## Routing Rule

All voice generation, voice cloning, TTS, and dubbing tasks → route to **Voice & Cast Director** agent with OmniVoice as the default tool.
For agent spawning → use Delegator; it will route to Voice & Cast Director.

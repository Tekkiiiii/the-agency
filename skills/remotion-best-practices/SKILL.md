---
name: remotion-best-practices
description: Best practices for Remotion - Video creation in React
metadata:
  tags: remotion, video, react, animation, composition
---

## When to use

Use this skills whenever you are dealing with Remotion code to obtain the domain-specific knowledge.

## New project setup

When in an empty folder or workspace with no existing Remotion project, scaffold one using:

```bash
npx create-video@latest --yes --blank --no-tailwind my-video
```

Replace `my-video` with a suitable project name.

## Designing a video

Animate properties using `useCurrentFrame()` and `interpolate()`. Use Easing to customize the timing of the animation.

```tsx
import { useCurrentFrame, Easing } from "remotion";

export const FadeIn = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 2 * fps], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return <div style={{ opacity }}>Hello World!</div>;
};
```

CSS transitions or animations are FORBIDDEN - they will not render correctly.  
Tailwind animation class names are FORBIDDEN - they will not render correctly.

Place assets in the `public/` folder at your project root.

Use `staticFile()` to reference files from the `public/` folder.

Add images using the `<Img>` component:

```tsx
import { Img, staticFile } from "remotion";

export const MyComposition = () => {
  return <Img src={staticFile("logo.png")} style={{ width: 100, height: 100 }} />;
};
```

Add videos using the `<Video>` component from `@remotion/media`:

```tsx
import { Video } from "@remotion/media";
import { staticFile } from "remotion";

export const MyComposition = () => {
  return <Video src={staticFile("video.mp4")} style={{ opacity: 0.5 }} />;
};
```

Add audio using the `<Audio>` component from `@remotion/media`:

```tsx
import { Audio } from "@remotion/media";
import { staticFile } from "remotion";

export const MyComposition = () => {
  return <Audio src={staticFile("audio.mp3")} />;
};
```

Assets can be also referenced as remote URLs:

```tsx
import { Video } from "@remotion/media";

export const MyComposition = () => {
  return <Video src="https://remotion.media/video.mp4" />
};
```

To delay content wrap it in `<Sequence>` and use `from`.
To limit the duration of an element, use `durationInFrames` of `<Sequence>`.
`<Sequence>` by default is an absolute fill. For inline content, use `layout="none"`.

```tsx
import { Sequence } from "remotion";

export const Title = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 2 * fps], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return <div style={{ opacity }}>Title</div>;
};

export const Subtitle = () => {
  return <div>Subtitle</div>;
};

const Main = () => {
  const {fps} = useVideoConfig();

  return (
    <AbsoluteFill>
      <Sequence>
        <Background />
      </Sequence>
      <Sequence from={1 * fps} durationInFrames={2 * fps} layout="none">
        <Title />
      </Sequence>
      <Sequence from={2 * fps} durationInFrames={2 * fps} layout="none">
        <Subtitle />
      </Sequence>
    </AbsoluteFill>
  );
}
```

The width, height, fps, and duration of a video is defined in `src/Root.tsx`:

```tsx
import { Composition } from "remotion";
import { MyComposition } from "./MyComposition";

export const RemotionRoot = () => {
  return (
    <Composition
      id="MyComposition"
      component={MyComposition}
      durationInFrames={100}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};
```

Metadata can also be calculated dynamically:

```tsx
import { Composition, CalculateMetadataFunction } from "remotion";
import { MyComposition, MyCompositionProps } from "./MyComposition";

const calculateMetadata: CalculateMetadataFunction<
  MyCompositionProps
> = async ({ props, abortSignal }) => {
  const data = await fetch(`https://api.example.com/video/${props.videoId}`, {
    signal: abortSignal,
  }).then((res) => res.json());

  return {
    durationInFrames: Math.ceil(data.duration * 30),
    props: {
      ...props,
      videoUrl: data.url,
    },
    width: 1080,
    height: 1080,
  };
};

export const RemotionRoot = () => {
  return (
    <Composition
      id="MyComposition"
      component={MyComposition}
      fps={30}
      width={1080}
      height={1080}
      defaultProps={{ videoId: "abc123" }}
      calculateMetadata={calculateMetadata}
    />
  );
};
```

## Starting preview

Start the Remotion Studio to preview a video:

```bash
npx remotion studio
```

## Optional: one-frame render check

You can render a single frame with the CLI to sanity-check layout, colors, or timing.  
Skip it for trivial edits, pure refactors, or when you already have enough confidence from Studio or prior renders.

```bash
npx remotion still [composition-id] --scale=0.25 --frame=30
```

At 30 fps, `--frame=30` is the one-second mark (`--frame` is zero-based).

## Captions

When dealing with captions or subtitles, load the [./rules/subtitles.md](./rules/subtitles.md) file for more information.

## Using FFmpeg

For some video operations, such as trimming videos or detecting silence, FFmpeg should be used. Load the [./rules/ffmpeg.md](./rules/ffmpeg.md) file for more information.

## Silence detection

When needing to detect and trim silent segments from video or audio files, load the [./rules/silence-detection.md](./rules/silence-detection.md) file.

## Audio visualization

When needing to visualize audio (spectrum bars, waveforms, bass-reactive effects), load the [./rules/audio-visualization.md](./rules/audio-visualization.md) file for more information.

## Sound effects

When needing to use sound effects, load the [./rules/sfx.md](./rules/sfx.md) file for more information.

## 3D content

See [rules/3d.md](rules/3d.md) for 3D content in Remotion using Three.js and React Three Fiber.

## Advanced audio

See [rules/audio.md](rules/audio.md) for advanced audio features like trimming, volume, speed, pitch.

## Dynamic duration, dimensions and data

See [rules/calculate-metadata.md](rules/calculate-metadata.md) for dynamically set composition duration, dimensions, and props.

## Advanced compositions

See [rules/compositions.md](rules/compositions.md) for how to define stills, folders, default props and for how to nest compositions.

## Google Fonts

Is the recommended way to load fonts in Remotion. See [rules/google-fonts.md](rules/google-fonts.md) for how to load Google Fonts.

## Local fonts

See [rules/local-fonts.md](rules/local-fonts.md) for how to load local fonts.

## Getting audio duration

See [rules/get-audio-duration.md](rules/get-audio-duration.md) for getting the duration of an audio file in seconds with Mediabunny.

## Getting video dimensions

See [rules/get-video-dimensions.md](rules/get-video-dimensions.md) for getting the width and height of a video file with Mediabunny.

## Getting video duration

See [rules/get-video-duration.md](rules/get-video-duration.md) for getting the duration of a video file in seconds with Mediabunny.

## GIFs

See [rules/gifs.md](rules/gifs.md) for how to display GIFs synchronized with Remotion's timeline.

## Advanced Images

See [rules/images.md](rules/images.md) for sizing and positioning images, dynamic image paths, and getting image dimensions.

## Light leaks

See [rules/light-leaks.md](rules/light-leaks.md) for light leak overlay effects using `@remotion/light-leaks`.

## Lottie animations

See [rules/lottie.md](rules/lottie.md) for embedding Lottie animations in Remotion.

## Measuring DOM nodes

See [rules/measuring-dom-nodes.md](rules/measuring-dom-nodes.md) for measuring DOM element dimensions in Remotion.

## Measuring text

See [rules/measuring-text.md](rules/measuring-text.md) for measuring text dimensions, fitting text to containers, and checking overflow.

## Advanced sequencing

See [rules/sequencing.md](rules/sequencing.md) for more sequencing patterns - delay, trim, limit duration of items.

## TailwindCSS

See [rules/tailwind.md](rules/tailwind.md) for using TailwindCSS in Remotion.

## Text animations

See [rules/text-animations.md](rules/text-animations.md) for typography and text animation patterns.

## Advanced timing

See [rules/timing.md](rules/timing.md) for advanced timing with `interpolate` and Bézier easing, and springs.

## Transitions

See [rules/transitions.md](rules/transitions.md) for scene transition patterns.

## Transparent videos

See [rules/transparent-videos.md](rules/transparent-videos.md) for rendering out a video with transparency.

## Trimming

See [rules/trimming.md](rules/trimming.md) for trimming patterns - cutting the beginning or end of animations.

## Advanced Videos

See [rules/videos.md](rules/videos.md) for advanced knowledge about embedding videos - trimming, volume, speed, looping, pitch.

## Parameterized videos

See [rules/parameters.md](rules/parameters.md) for making a composition parametrizable by adding a Zod schema.

## Maps

See [rules/maps.md](rules/maps.md) for adding a map using Mapbox and animating it.

## Voiceover

See [rules/voiceover.md](rules/voiceover.md) for adding AI-generated voiceover to Remotion compositions using ElevenLabs TTS.

## Video Types & Platform Specs

Build compositions at the correct dimensions for the target platform from day one. Do not default to 1080×1080 — always ask or infer platform before scaffolding.

| Platform | Ratio | Resolution | FPS | Max Duration |
|---|---|---|---|---|
| YouTube (long-form) | 16:9 | 1920×1080 min, 3840×2160 ideal | 24/30/60 | 12 hours |
| YouTube Shorts | 9:16 | 1080×1920 | 30–60 | 60s |
| TikTok | 9:16 | 1080×1920 | 30–60 **constant** | 60s optimal |
| Instagram Reels | 9:16 | 1080×1920 | 30–60 | 90s |
| Instagram Feed | 1:1 | 1080×1080 | 30 | 60s |
| Instagram Stories | 9:16 | 1080×1920 | 30 | 15s |
| Landing page hero | 16:9 | 1920×1080 | 24/30 | 60–90s |
| Short-form ads | 9:16 | 1080×1920 | 30 | 6–20s |

**Constant frame rate is mandatory for TikTok and Instagram.** Variable FPS causes compression artifacts on re-encode.

**Text safe zone:** Keep all text and UI elements at least 10–15% from all edges. Bottom 20% is covered by TikTok/Instagram native UI (captions, profile handle, action buttons). Never place a CTA or key information there.

**Always use `useVideoConfig()` to read `fps`** — never hardcode 30 or 60 in time calculations.

## Production Quality

### Codec and CRF

Default to `h264` for compatibility. Use `h265` where the platform explicitly supports it.

CRF is the primary quality lever. It is exponential: +6 CRF = ~half bitrate, –6 CRF = ~double bitrate.

| Use case | CRF | Notes |
|---|---|---|
| Social platform upload (1080p) | 18–22 | Platforms re-encode — start clean |
| YouTube 4K | 18–20 | Higher quality survives YouTube re-encode better |
| Preview / draft render | 28–35 | Fast iteration |
| Archive master | 16–18 | Largest file, best quality |

**Never use variable bitrate without a target bitrate when hardware-accelerating.** Use `--video-bitrate` instead of `--crf` with VideoToolbox (macOS hardware acceleration).

### Render commands

```bash
# Social (1080p, high quality)
npx remotion render src/index.ts MyComp out/video.mp4 --codec=h264 --crf=20

# GIF (social, reduced frame rate)
npx remotion render src/index.ts MyComp out/animation.gif --every-nth-frame=2 --number-of-gif-loops=0

# Single frame proof (layout check)
npx remotion still MyComp --scale=0.25 --frame=30

# Full render with concurrency
npx remotion render src/index.ts MyComp out/video.mp4 --concurrency=50%
```

### Hardware acceleration (macOS only)

Set `hardwareAcceleration: "if-possible"` in config. Use `--video-bitrate` not `--crf`. Supports H.264, H.265, ProRes.

## Product & Promotional Video Structure

Every product or promotional video must follow a proven narrative framework matched to the viewer's funnel stage. Do not invent structure — select from below.

### Framework selection

| Funnel stage | Framework | Core sequence |
|---|---|---|
| Cold (awareness) | **AIDA** | Attention → Interest → Desire → Action |
| Mid-funnel | **BAB** | Before (reality) → After (transformed) → Bridge (product) |
| Mid-funnel, urgent | **PAS** | Problem → Agitation → Solution |
| Conversion / VSL | **Hook-Story-Offer** | Hook → Story → Offer as transformation |
| Short-form ads (all stages) | **Hook-Body-CTA** | Stop scroll → Demonstrate value → Direct action |

### Anatomy of a 60-second product video

```
0–3s    Hook          — one arresting visual or statement. No logo.
3–15s   Problem       — specific, relatable pain point
15–40s  Solution      — benefit-led reveal + feature demo (max 3–4 features)
40–50s  Social proof  — testimonial pull quote, metric, or logo wall
50–60s  CTA           — one action, specific verb, spoken + on-screen
```

### Scene count

Aim for **5–8 scenes per 60-second video**. Minimum 3s per scene; maximum ~15s without a new visual event.

### CTA placement (Wistia data, 36,000 CTAs)

| Video length | Place CTA at |
|---|---|
| Under 60s | **First quarter** — can't guarantee completion |
| 1–3 min | Last quarter |
| 3–5 min | Around halfway |
| 5+ min | End |

### CTA rules (enforced)

- **One CTA per video** — multiple CTAs reduce conversion
- First-person verb: "Start My Free Trial" > "Start Your Free Trial"
- Specific beats vague: "Start your 14-day free trial" > "Learn more"
- Combine spoken CTA with on-screen text/button
- On-screen CTA must be visible for at least 5 seconds

### The hook (highest-leverage element)

- **Benchmark:** 3-second view rate of 35–45% is healthy; below 25% = hook failure
- Must work silent — text overlay carries the message without audio
- **Never open with a logo** — signals "ad", triggers scroll
- **Never use:** "Have you ever wondered..." / "What if I told you..." — scroll triggers in 2025+
- Hook types (use one): Pattern interrupt, Social proof, Anticipation, Number/List, Emotional, Open loop, Contradiction, Comparison

### Social proof placement

Place after the product demo, before the CTA. Never before the solution reveal. For short-form (under 30s), a social proof hook (open with the result) is an exception.

### Script pacing

Narration target: **130–150 words per minute**.
- 60s video = ~130–150 words
- 90s video = ~195–225 words
- 2-min video = ~260–300 words

### Ideal video lengths by platform

| Platform | Optimal | Notes |
|---|---|---|
| Landing page hero | 60–90s | Video above fold = +86% conversion |
| Instagram Reels | **15–30s** | Under 30s pulls highest median views |
| TikTok | 10–60s | 10–15s gets most momentum |
| LinkedIn | 30–90s | Executive-led outperforms brand films |
| YouTube Shorts | 30–60s | Full 60s differentiates from TikTok |
| Short-form ads | 6–20s | 47% of ad value delivered in first 3s |

## AI Asset Integration

When using AI-generated assets in a Remotion composition:

1. **Lock and finalize TTS audio before generating video clips.** Clips must be timed to match audio segment lengths.
2. **Export TTS at 44.1kHz or 48kHz, 16-bit minimum.** Add 0.2–0.5s silence padding at each segment boundary.
3. **Use `<Audio>` with `delayRender()` / `continueRender()`** when loading remote TTS files — Remotion must wait for the file before capturing frames.
4. **Use word-level timestamps from ElevenLabs** to drive caption timing. Map timestamps to `<Sequence from={...}>` boundaries.
5. **AI-generated video clips:** Place in `public/` via `staticFile()`, wrap in `<OffthreadVideo>` for frame-accurate extraction.
6. **Character consistency:** When using Midjourney assets, use `--cref` (character ref) across all frames. Generate at 1920×1080 minimum; never scale up raster assets.
7. **Upscaling:** If AI clip outputs at 720p, use Topaz Video AI before importing — never expect Remotion's `--scale` flag to recover lost detail.

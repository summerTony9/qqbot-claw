---
name: minimax-story-video
description: Generate narrated story videos from structured scene prompts plus existing narration audio, using MiniMax image generation for consistent visuals and ffmpeg for final assembly. Use when the user wants to turn a script/voiceover into a finished video, remake a previously generated story video with more images or more consistent style, add background music, or save the workflow as a reusable skill.
---

# MiniMax Story Video

Generate a complete narrated video from:
- a set of narration audio segments
- a shared visual style prompt
- multiple concrete shot prompts per segment

The bundled script handles image generation, clip rendering, narration concat, procedural background music, ducking, and final muxing.

## Workflow

1. Prepare narration audio files.
2. Create a config JSON based on `references/config-template.json`.
3. Write a **shared style prompt** that keeps the whole video visually unified.
4. Write **multiple shot prompts per narration segment**.
5. Run the renderer.
6. Review the output video and iterate on prompts or shot count.

## Prompting rules

### 1. Keep style unified

Put global style constraints in `style_prompt`, not repeated differently in each shot.

Include things like:
- visual medium: 电影级写实 / cinematic sci-fi concept art / photorealistic
- color palette: cold blue / silver / dark black
- lens/composition language: 35mm cinematic composition, high contrast, volumetric lighting
- continuity constraints:人物外观保持连续、服装连续、不要卡通、不要文字水印

### 2. Make shots concrete

Avoid vague prompts like only “sky”, “stars”, or “cosmos”.

Prefer:
- who is in frame
- what they are doing
- camera distance (close-up / medium / wide)
- where they are
- what visible objects define the scene
- emotional tone

Good examples:
- “叶文洁白发被风吹起的近景肖像，背景是黑色山脊和暮色天空”
- “伊文斯站在甲板护栏旁，手握通讯装置，脸被冷色屏幕光照亮”
- “审判日号巨轮夜航，船头有孤独人物轮廓，海浪与月光清晰可见”

### 3. Increase image count by splitting beats

If one narration segment is too long, break it into 2-3 shots instead of one.

Typical guidance:
- short segment: 1-2 shots
- medium segment: 2-3 shots
- long segment: 3-4 shots

The script automatically divides each segment duration evenly across its shots.

## Files

### `references/config-template.json`
Use as the starting point for a project config.

### `scripts/render_story_video.py`
Main renderer.

## Run command

```bash
python3 skills/minimax-story-video/scripts/render_story_video.py \
  --config /absolute/path/to/config.json \
  --workdir /absolute/path/to/output-dir \
  --api-key "$MINIMAX_API_KEY"
```

If the environment does not expose `MINIMAX_API_KEY`, pass `--api-key` explicitly.

To force image regeneration:

```bash
python3 skills/minimax-story-video/scripts/render_story_video.py \
  --config /absolute/path/to/config.json \
  --workdir /absolute/path/to/output-dir \
  --api-key "$MINIMAX_API_KEY" \
  --regen-images
```

## Output layout

The renderer creates:
- `images/` generated stills
- `clips/` per-shot mp4 clips
- `audio/narration_full.m4a`
- `audio/bgm.m4a`
- `audio/mixed_audio.m4a`
- final `*.mp4`
- `render_manifest.json`

## Iteration guidance

If the first result is weak:
- add more shots instead of stretching one image too long
- strengthen `style_prompt` to lock visual consistency
- replace abstract prompts with character/action/environment details
- prefer human presence where appropriate to avoid empty scenery
- rerun with `--regen-images` after prompt changes

## Constraints

- Requires `ffmpeg` and `ffprobe` locally.
- Expects narration audio to already exist.
- Uses procedural ambient BGM generation inside ffmpeg; if a user wants a custom music file, replace the generated BGM stage in the script or mix separately.

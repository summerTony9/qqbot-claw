#!/usr/bin/env python3
"""Generate a narrated story video from MiniMax images + local narration audio.

Features:
- Batch image generation with a shared style prompt (consistent look)
- Multi-shot pacing per narration segment (more images per segment)
- Automatic slideshow rendering with ffmpeg
- Procedural ambient background music generation
- Final mixdown (narration + ducked BGM)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import requests


def run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_image_url(api_key: str, prompt: str, model: str = "image-01") -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "response_format": "url",
        "n": 1,
        "prompt_optimizer": True,
    }
    resp = requests.post(
        "https://api.minimaxi.com/v1/image_generation",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    image_urls = (((data or {}).get("data") or {}).get("image_urls")) or []
    if not image_urls:
        raise RuntimeError(f"image_generation returned no image_urls: {data}")
    return image_urls[0]


def download_binary(url: str, path: Path) -> None:
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    path.write_bytes(r.content)


def render_shot_clip(image_path: Path, out_path: Path, duration: float, fps: int, width: int, height: int) -> None:
    # Keep rendering conservative for reliability: static frame + exact duration.
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},format=yuv420p"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(image_path),
            "-vf",
            vf,
            "-r",
            str(fps),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ]
    )


def concat_media(inputs: List[Path], output: Path, media_type: str) -> None:
    list_path = output.with_suffix(output.suffix + ".list.txt")
    list_path.write_text("\n".join([f"file '{p.as_posix()}'" for p in inputs]) + "\n", encoding="utf-8")

    if media_type == "video":
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)])
    elif media_type == "audio":
        # Re-encode for robust concat across VBR MP3 narration sources.
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output),
            ]
        )
    else:
        raise ValueError(f"Unknown media_type: {media_type}")


def generate_bgm(output: Path, duration: float) -> None:
    fade_out_start = max(0.0, duration - 3.0)
    filter_complex = (
        "[0:a]volume=0.035[a0];"
        "[1:a]volume=0.028[a1];"
        "[2:a]volume=0.008,lowpass=f=1000,highpass=f=80[a2];"
        f"[a0][a1][a2]amix=inputs=3:normalize=0,afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d=3[m]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            "sine=frequency=110:sample_rate=48000",
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            "sine=frequency=164.81:sample_rate=48000",
            "-f",
            "lavfi",
            "-t",
            f"{duration:.3f}",
            "-i",
            "anoisesrc=color=pink:sample_rate=48000:amplitude=0.2",
            "-filter_complex",
            filter_complex,
            "-map",
            "[m]",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(output),
        ]
    )


def mix_audio(narration: Path, bgm: Path, output: Path) -> None:
    filter_complex = (
        "[1:a][0:a]sidechaincompress=threshold=0.02:ratio=12:attack=20:release=400[ducked];"
        "[ducked]volume=0.75[bgm];"
        "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[mix]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(narration),
            "-i",
            str(bgm),
            "-filter_complex",
            filter_complex,
            "-map",
            "[mix]",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output),
        ]
    )


def mux_video_audio(video: Path, audio: Path, output: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render narrated story video with consistent-style generated images + BGM")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--workdir", required=True, help="Output working directory")
    parser.add_argument("--api-key", default=os.getenv("MINIMAX_API_KEY"), help="MiniMax API key (or set MINIMAX_API_KEY)")
    parser.add_argument("--regen-images", action="store_true", help="Regenerate images even if cached")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Missing API key. Pass --api-key or set MINIMAX_API_KEY")

    cfg = load_config(Path(args.config))
    workdir = Path(args.workdir)
    images_dir = workdir / "images"
    clips_dir = workdir / "clips"
    audio_dir = workdir / "audio"
    for d in (workdir, images_dir, clips_dir, audio_dir):
        d.mkdir(parents=True, exist_ok=True)

    width = int(cfg.get("resolution", "1920x1080").split("x")[0])
    height = int(cfg.get("resolution", "1920x1080").split("x")[1])
    fps = int(cfg.get("fps", 25))
    style_prompt = (cfg.get("style_prompt") or "").strip()

    narration_segments = cfg["audio_segments"]
    shots = cfg["shots"]

    # 1) Validate narration files and get segment durations.
    segment_duration: Dict[str, float] = {}
    segment_audio_paths: Dict[str, Path] = {}
    for seg in narration_segments:
        seg_id = seg["id"]
        path = Path(seg["file"])
        if not path.exists():
            raise FileNotFoundError(f"Narration file not found for segment {seg_id}: {path}")
        segment_audio_paths[seg_id] = path
        segment_duration[seg_id] = ffprobe_duration(path)

    # 2) Generate/download shot images.
    shot_image_paths: Dict[str, Path] = {}
    shot_meta = []
    for shot in shots:
        shot_id = shot["id"]
        seg_id = shot["segment"]
        prompt = shot["prompt"].strip()
        full_prompt = f"{style_prompt}\n\nScene requirement: {prompt}" if style_prompt else prompt

        image_path = images_dir / f"{shot_id}.jpg"
        if args.regen_images or not image_path.exists():
            print(f"[image] generating {shot_id}...")
            url = fetch_image_url(args.api_key, full_prompt, model=cfg.get("image_model", "image-01"))
            download_binary(url, image_path)
        else:
            print(f"[image] cache hit {shot_id}")

        shot_image_paths[shot_id] = image_path
        shot_meta.append({"id": shot_id, "segment": seg_id, "prompt": prompt, "image": image_path.as_posix()})

    # 3) Allocate shot durations inside each narration segment.
    shots_by_segment: Dict[str, List[dict]] = {}
    for shot in shots:
        shots_by_segment.setdefault(shot["segment"], []).append(shot)

    timeline = []
    for seg in narration_segments:
        seg_id = seg["id"]
        seg_shots = shots_by_segment.get(seg_id, [])
        if not seg_shots:
            raise RuntimeError(f"No shots configured for segment: {seg_id}")
        per = segment_duration[seg_id] / len(seg_shots)
        for s in seg_shots:
            timeline.append({
                "shot_id": s["id"],
                "segment": seg_id,
                "duration": per,
            })

    # 4) Render clip per shot.
    clip_paths: List[Path] = []
    for idx, item in enumerate(timeline, start=1):
        shot_id = item["shot_id"]
        duration = max(0.1, float(item["duration"]))
        clip_path = clips_dir / f"{idx:03d}_{shot_id}.mp4"
        print(f"[clip] {clip_path.name} duration={duration:.2f}s")
        render_shot_clip(shot_image_paths[shot_id], clip_path, duration, fps, width, height)
        clip_paths.append(clip_path)

    # 5) Concat video clips and narration.
    video_silent = workdir / "video_silent.mp4"
    concat_media(clip_paths, video_silent, media_type="video")

    narration_concat = audio_dir / "narration_full.m4a"
    narration_files = [segment_audio_paths[s["id"]] for s in narration_segments]
    concat_media(narration_files, narration_concat, media_type="audio")

    # 6) Build and mix BGM.
    total_duration = ffprobe_duration(narration_concat)
    bgm = audio_dir / "bgm.m4a"
    print(f"[bgm] generating procedural ambient track ({total_duration:.2f}s)")
    generate_bgm(bgm, total_duration)

    mixed_audio = audio_dir / "mixed_audio.m4a"
    mix_audio(narration_concat, bgm, mixed_audio)

    # 7) Final mux.
    output_file = workdir / cfg.get("output_filename", "story_video.mp4")
    mux_video_audio(video_silent, mixed_audio, output_file)

    manifest = {
        "title": cfg.get("title", "story-video"),
        "output": output_file.as_posix(),
        "shots": shot_meta,
        "timeline": timeline,
        "narration_segments": narration_segments,
        "total_duration": total_duration,
    }
    (workdir / "render_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[done] Video ready: {output_file}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n[error] command failed: {e}", file=sys.stderr)
        raise

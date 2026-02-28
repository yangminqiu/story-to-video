#!/usr/bin/env python3
"""
Generate YouTube Shorts (9:16, <=60s) from a landscape video.

Example:
  python generate_shorts.py \
    --input videos/episode.mp4 \
    --output-dir output/shorts \
    --max-duration 60
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def ffprobe_duration(input_path: Path) -> float:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ]
    ).stdout.strip()
    return float(out)


def ensure_tools() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise SystemExit(f"Missing required tool: {tool}")


def build_filter() -> str:
    # Crop center area to 9:16 then scale to 1080x1920
    # For landscape inputs, this creates a standard Shorts frame.
    return "crop='if(gte(iw/ih,9/16),ih*9/16,iw)':'if(gte(iw/ih,9/16),ih,iw*16/9)',scale=1080:1920"


def cut_short(input_path: Path, output_path: Path, start: float, duration: float) -> None:
    vf = build_filter()
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(input_path),
        "-t",
        f"{duration:.3f}",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate YouTube Shorts from a long video")
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output-dir", default="output/shorts", help="Output directory")
    parser.add_argument("--max-duration", type=int, default=60, help="Max seconds per short")
    parser.add_argument(
        "--clips",
        type=int,
        default=0,
        help="Limit number of shorts (0 = all possible segments)",
    )
    args = parser.parse_args()

    ensure_tools()

    input_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    total = ffprobe_duration(input_path)
    seg = max(1, int(args.max_duration))
    total_clips = math.ceil(total / seg)
    if args.clips > 0:
        total_clips = min(total_clips, args.clips)

    print(f"Input duration: {total:.2f}s")
    print(f"Generating {total_clips} short(s) with max {seg}s each...")

    for i in range(total_clips):
        start = i * seg
        dur = min(seg, max(0.0, total - start))
        if dur <= 0:
            break
        out = out_dir / f"short_{i+1:02d}.mp4"
        print(f" - {out.name}: start={start:.1f}s dur={dur:.1f}s")
        cut_short(input_path, out, start, dur)

    print(f"Done. Shorts saved to: {out_dir}")


if __name__ == "__main__":
    main()

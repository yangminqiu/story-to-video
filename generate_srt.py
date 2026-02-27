#!/usr/bin/env python3
"""
Generate SRT subtitles from a plain text script and optional audio file duration.

Usage:
  python generate_srt.py --text stories/script.txt --out output/subtitles.srt --audio output/voice.mp3
"""
import argparse
import re
import subprocess
from pathlib import Path


def ffprobe_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def split_sentences(text: str):
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    # basic punctuation split for EN/CN mixed scripts
    parts = re.split(r"(?<=[。！？.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="Path to plain text file")
    ap.add_argument("--out", required=True, help="Output .srt path")
    ap.add_argument("--audio", help="Optional audio path (for precise duration)")
    ap.add_argument("--duration", type=float, help="Manual duration seconds (if no audio)")
    args = ap.parse_args()

    script = Path(args.text).read_text(encoding="utf-8")
    lines = split_sentences(script)
    if not lines:
        raise SystemExit("No subtitle lines found in text.")

    total_dur = args.duration
    if args.audio:
        total_dur = ffprobe_duration(args.audio)
    if not total_dur:
        # fallback: 2.8 words/sec rough estimate
        words = max(1, len(script.split()))
        total_dur = max(5.0, words / 2.8)

    # allocate by char length
    weights = [max(1, len(x)) for x in lines]
    wsum = sum(weights)
    t = 0.0
    out = []
    for i, (line, w) in enumerate(zip(lines, weights), 1):
        seg = total_dur * (w / wsum)
        start = t
        end = t + seg
        t = end
        out.append(f"{i}\n{fmt_ts(start)} --> {fmt_ts(end)}\n{line}\n")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Saved SRT: {out_path}")


if __name__ == "__main__":
    main()

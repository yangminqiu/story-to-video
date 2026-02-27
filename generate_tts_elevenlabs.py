#!/usr/bin/env python3
"""
Generate narration using ElevenLabs TTS and save as mp3.

Usage:
  python generate_tts_elevenlabs.py <story.md>
  python generate_tts_elevenlabs.py <story.md> <voice_id>
  python generate_tts_elevenlabs.py --pattern "*.md"

Env:
  ELEVENLABS_API_KEY (required)
  ELEVENLABS_MODEL (optional, default: eleven_multilingual_v2)
"""

import os
import sys
import time
from pathlib import Path
import requests

STORIES_DIR = Path(__file__).parent / "stories"
NARRATIONS_DIR = Path(__file__).parent / "narrations"
DEFAULT_VOICE = "EXAVITQu4vr4xnSDxMaL"  # Sarah


def clean_story_text(filepath: Path) -> str:
    text = filepath.read_text(encoding="utf-8")
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def tts_elevenlabs(text: str, voice_id: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY")

    model = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs API error {r.status_code}: {r.text[:300]}")
    return r.content


def generate_one(story_file: str, voice_id: str = DEFAULT_VOICE):
    story_path = STORIES_DIR / story_file
    if not story_path.exists():
        print(f"Story not found: {story_path}")
        return None

    text = clean_story_text(story_path)
    out = NARRATIONS_DIR / story_file.replace('.md', '.mp3')
    print(f"Generating ElevenLabs TTS: {story_file} -> {out.name}")

    audio = tts_elevenlabs(text, voice_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    print(f"Saved: {out}")
    return out


def main():
    NARRATIONS_DIR.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print(__doc__)
        return

    if sys.argv[1] == "--pattern":
        pattern = sys.argv[2] if len(sys.argv) > 2 else "*.md"
        voice_id = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE
        stories = sorted(p.name for p in STORIES_DIR.glob(pattern))
        for i, s in enumerate(stories, 1):
            try:
                print(f"[{i}/{len(stories)}] {s}")
                generate_one(s, voice_id)
                if i < len(stories):
                    time.sleep(2)
            except Exception as e:
                print(f"Error on {s}: {e}")
    else:
        story = sys.argv[1]
        voice_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VOICE
        generate_one(story, voice_id)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Alternative TTS using Google Gemini (Zephyr voice).

Produces .wav narrations instead of .mp3. Useful when you want a different
voice engine or don't have an OpenAI key.

Usage:
    python generate_tts_gemini.py <story_file.md>                # Single story
    python generate_tts_gemini.py <story_file.md> Zephyr         # Custom voice
    python generate_tts_gemini.py --pattern "格林童话-*.md"       # Batch by glob

Requires: GEMINI_API_KEY env var
"""

import os
import sys
import time
import struct
from pathlib import Path
from google import genai
from google.genai import types

STORIES_DIR = Path(__file__).parent / "stories"
NARRATIONS_DIR = Path(__file__).parent / "narrations"


def clean_story_text(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def parse_audio_mime_type(mime_type: str) -> dict:
    bits_per_sample = 16
    rate = 24000
    for param in mime_type.split(";"):
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    p = parse_audio_mime_type(mime_type)
    bits = p["bits_per_sample"]
    rate = p["rate"]
    bps = bits // 8
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16,
        1, 1, rate, rate * bps, bps, bits, b"data", len(audio_data),
    )
    return header + audio_data


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def generate_narration(story_file, voice="Zephyr", output_filename=None):
    story_path = STORIES_DIR / story_file
    out_name = output_filename or story_file.replace(".md", ".wav")
    output_path = NARRATIONS_DIR / out_name

    if not story_path.exists():
        print(f"  Story not found: {story_path}")
        return None

    text = clean_story_text(story_path)
    print(f"  {story_file} ({len(text)} chars)")

    client = get_gemini_client()
    print(f"  Generating TTS (Gemini, voice={voice})...")

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Read aloud in a warm and friendly tone:\n\n{text}")],
        ),
    ]
    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    audio_chunks = []
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-pro-preview-tts",
        contents=contents,
        config=config,
    ):
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_chunks.append((part.inline_data.data, part.inline_data.mime_type))

    if not audio_chunks:
        print("  No audio data received")
        return None

    all_audio = b"".join(c[0] for c in audio_chunks)
    mime = audio_chunks[0][1] if audio_chunks else "audio/L16;rate=24000"
    wav_data = convert_to_wav(all_audio, mime)

    with open(output_path, "wb") as f:
        f.write(wav_data)

    print(f"  Saved: {output_path}")
    return output_path


def main():
    NARRATIONS_DIR.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print(__doc__)
        return

    arg = sys.argv[1]

    if arg == "--pattern":
        pattern = sys.argv[2] if len(sys.argv) > 2 else "*.md"
        stories = sorted(f.name for f in STORIES_DIR.glob(pattern))
        print(f"Generating narrations for {len(stories)} stories (pattern: {pattern})")
        for i, name in enumerate(stories, 1):
            out = NARRATIONS_DIR / name.replace(".md", ".wav")
            if out.exists():
                print(f"\n[{i}/{len(stories)}] {name} — exists, skipping")
                continue
            print(f"\n[{i}/{len(stories)}]")
            try:
                generate_narration(name)
                if i < len(stories):
                    time.sleep(5)
            except Exception as e:
                print(f"  Error: {e}")
    else:
        voice = sys.argv[2] if len(sys.argv) > 2 else "Zephyr"
        generate_narration(arg, voice=voice)


if __name__ == "__main__":
    main()

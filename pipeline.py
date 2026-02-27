#!/usr/bin/env python3
"""
Story-to-Video Pipeline

End-to-end pipeline that turns a markdown story into a narrated video:
  1. Generate TTS narration (OpenAI)
  2. Mix narration with background music (ffmpeg)
  3. Create video from thumbnail image + mixed audio (ffmpeg)

Usage:
    python pipeline.py --list                    # List available stories
    python pipeline.py --status                  # Show pipeline status
    python pipeline.py <story_name>              # Run full pipeline for one story
    python pipeline.py --step1 [story_name]      # Generate narration only
    python pipeline.py --step2 [story_name]      # Mix audio only
    python pipeline.py --step3 [story_name]      # Create video only
    python pipeline.py --all                     # Run full pipeline for all stories

Requires: OPENAI_API_KEY env var, ffmpeg/ffprobe installed
"""

import os
import re
import shutil
import sys
import time
import subprocess
from pathlib import Path
from openai import OpenAI
from generate_thumbnails import generate_image

BASE_DIR = Path(__file__).parent
STORIES_DIR = BASE_DIR / "stories"
IMAGES_DIR = BASE_DIR / "images"
NARRATIONS_DIR = BASE_DIR / "narrations"
MIXED_DIR = BASE_DIR / "mixed"
OUTPUT_DIR = BASE_DIR / "videos"
TEMP_DIR = BASE_DIR / "temp"

BACKGROUND_MUSIC = BASE_DIR / "background" / "background.m4a"

TTS_MODEL = "tts-1"
TTS_VOICE = "alloy"
NARRATION_DB = 5
MUSIC_DB = -15


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def clean_story_text(filepath):
    """Strip markdown formatting from a story file."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"^#+ .*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_story_title(filepath):
    """Pull the first markdown heading from a story file."""
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^#+\s*\**\s*(.+?)\s*\**\s*$", line)
            if m:
                return m.group(1)
    return filepath.stem


def get_audio_duration(filepath):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


# ---------------------------------------------------------------------------
# Step 1: TTS Narration
# ---------------------------------------------------------------------------

def generate_narration(story_name, client, voice=TTS_VOICE):
    story_path = STORIES_DIR / f"{story_name}.md"
    output_path = NARRATIONS_DIR / f"{story_name}.mp3"

    if not story_path.exists():
        print(f"  Story not found: {story_path}")
        return None

    text = clean_story_text(story_path)

    # OpenAI TTS has a ~4096 char limit per request; split into chunks
    max_chars = 4000
    chunks, current = [], ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) < max_chars:
            current += paragraph + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph + "\n\n"
    if current:
        chunks.append(current.strip())

    print(f"  Generating narration ({voice}, {len(chunks)} chunk(s))...")
    chunk_files = []

    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"    Chunk {i + 1}/{len(chunks)}...")
        chunk_path = TEMP_DIR / f"{story_name}_chunk{i}.mp3"

        for attempt in range(3):
            try:
                response = client.audio.speech.create(
                    model=TTS_MODEL, voice=voice,
                    input=chunk, response_format="mp3",
                )
                response.stream_to_file(str(chunk_path))
                chunk_files.append(chunk_path)
                break
            except Exception as e:
                if attempt < 2:
                    print(f"    Retry {attempt + 1} after: {str(e)[:60]}")
                    time.sleep(2)
                else:
                    raise

        if i < len(chunks) - 1:
            time.sleep(0.5)

    if len(chunk_files) == 1:
        os.rename(chunk_files[0], output_path)
    else:
        concat_file = TEMP_DIR / f"{story_name}_concat.txt"
        with open(concat_file, "w") as f:
            for p in chunk_files:
                f.write(f"file '{p}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file), "-c", "copy", str(output_path)],
            check=True, capture_output=True,
        )
        concat_file.unlink()
        for p in chunk_files:
            p.unlink()

    return output_path


def step1_narrations(stories):
    NARRATIONS_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)
    client = get_openai_client()

    print(f"\nSTEP 1: Generating narrations  ->  {NARRATIONS_DIR}")
    ok = fail = 0

    for story in stories:
        out = NARRATIONS_DIR / f"{story}.mp3"
        if out.exists():
            print(f"\n  {story} — exists, skipping")
            ok += 1
            continue
        print(f"\n  {story}")
        try:
            if generate_narration(story, client):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  Error: {e}")
            fail += 1

    print(f"\nStep 1 done: {ok} ok, {fail} failed")


# ---------------------------------------------------------------------------
# Step 2: Mix narration + background music
# ---------------------------------------------------------------------------

def mix_audio(story_name):
    narration = NARRATIONS_DIR / f"{story_name}.mp3"
    output = MIXED_DIR / f"{story_name}.mp3"

    if not narration.exists():
        print(f"  Narration not found: {narration}")
        return None
    if not BACKGROUND_MUSIC.exists():
        print(f"  No background music — copying narration as-is")
        shutil.copy2(narration, output)
        return output

    duration = get_audio_duration(narration)
    print(f"  Mixing narration (+{NARRATION_DB}dB) + music ({MUSIC_DB}dB)...")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(narration),
            "-stream_loop", "-1",
            "-i", str(BACKGROUND_MUSIC),
            "-filter_complex",
            f"[0:a]volume={NARRATION_DB}dB[narr];"
            f"[1:a]volume={MUSIC_DB}dB[music];"
            f"[narr][music]amix=inputs=2:duration=first:normalize=0[out]",
            "-map", "[out]",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(output),
        ],
        check=True, capture_output=True,
    )
    return output


def step2_mix(stories):
    MIXED_DIR.mkdir(exist_ok=True)
    print(f"\nSTEP 2: Mixing audio  ->  {MIXED_DIR}")
    ok = fail = 0

    for story in stories:
        out = MIXED_DIR / f"{story}.mp3"
        if out.exists():
            print(f"\n  {story} — exists, skipping")
            ok += 1
            continue
        print(f"\n  {story}")
        try:
            if mix_audio(story):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  Error: {e}")
            fail += 1

    print(f"\nStep 2 done: {ok} ok, {fail} failed")


# ---------------------------------------------------------------------------
# Step 2.5: Generate thumbnail if missing
# ---------------------------------------------------------------------------

def ensure_thumbnail(story_name, client):
    image_path = IMAGES_DIR / f"{story_name}.png"
    if image_path.exists():
        return image_path

    story_path = STORIES_DIR / f"{story_name}.md"
    title = extract_story_title(story_path) if story_path.exists() else story_name
    prompt = f"A fairy tale scene depicting {title}."
    print(f"  Generating thumbnail via DALL-E 3...")
    return generate_image(client, story_name, prompt)


def step_thumbnails(stories):
    IMAGES_DIR.mkdir(exist_ok=True)
    client = get_openai_client()
    print(f"\nGENERATING THUMBNAILS  ->  {IMAGES_DIR}")
    for story in stories:
        print(f"\n  {story}")
        try:
            ensure_thumbnail(story, client)
        except Exception as e:
            print(f"  Error: {e}")


# ---------------------------------------------------------------------------
# Step 3: Create video (image + mixed audio)
# ---------------------------------------------------------------------------

def create_video(story_name):
    image = IMAGES_DIR / f"{story_name}.png"
    audio = MIXED_DIR / f"{story_name}.mp3"
    output = OUTPUT_DIR / f"{story_name}.mp4"

    if not image.exists():
        print(f"  Image not found: {image}")
        return None
    if not audio.exists():
        print(f"  Mixed audio not found: {audio}")
        return None

    duration = get_audio_duration(audio)
    print(f"  Creating video ({duration:.0f}s)...")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image),
            "-i", str(audio),
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-shortest", "-t", str(duration),
            str(output),
        ],
        check=True, capture_output=True,
    )
    return output


def step3_videos(stories):
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"\nSTEP 3: Creating videos  ->  {OUTPUT_DIR}")
    ok = fail = 0

    for story in stories:
        out = OUTPUT_DIR / f"{story}.mp4"
        if out.exists():
            print(f"\n  {story} — exists, skipping")
            ok += 1
            continue
        print(f"\n  {story}")
        try:
            if create_video(story):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  Error: {e}")
            fail += 1

    print(f"\nStep 3 done: {ok} ok, {fail} failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_stories():
    stories = sorted(p.stem for p in STORIES_DIR.glob("*.md"))
    print(f"Available stories ({len(stories)}):")
    for i, s in enumerate(stories, 1):
        print(f"  {i:3}. {s}")
    return stories


def show_status():
    stories = sorted(p.stem for p in STORIES_DIR.glob("*.md"))
    print(f"\n{'Story':<30} {'Image':<12} {'Narration':<12} {'Mixed':<12} {'Video':<12}")
    print("-" * 78)
    for s in stories:
        img  = "yes" if (IMAGES_DIR / f"{s}.png").exists() else "-"
        narr = "yes" if (NARRATIONS_DIR / f"{s}.mp3").exists() else "-"
        mix_ = "yes" if (MIXED_DIR / f"{s}.mp3").exists() else "-"
        vid  = "yes" if (OUTPUT_DIR / f"{s}.mp4").exists() else "-"
        print(f"{s:<30} {img:<12} {narr:<12} {mix_:<12} {vid:<12}")


def main():
    for d in [IMAGES_DIR, NARRATIONS_DIR, MIXED_DIR, OUTPUT_DIR, TEMP_DIR]:
        d.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print(__doc__)
        list_stories()
        return

    arg = sys.argv[1]

    if arg == "--list":
        list_stories()
        return
    if arg == "--status":
        show_status()
        return

    # Determine stories to process
    if arg.startswith("--"):
        if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
            stories = [sys.argv[2]]
        else:
            stories = sorted(p.stem for p in STORIES_DIR.glob("*.md"))
    else:
        stories = [arg]

    if arg == "--step1":
        step1_narrations(stories)
    elif arg == "--step2":
        step2_mix(stories)
    elif arg == "--step3":
        step3_videos(stories)
    elif arg == "--all" or not arg.startswith("--"):
        print(f"Running full pipeline for {len(stories)} story(s)...")
        step1_narrations(stories)
        step2_mix(stories)
        step_thumbnails(stories)
        step3_videos(stories)
        print("\n" + "=" * 50)
        print("Pipeline complete!")
        show_status()

    if TEMP_DIR.exists() and not any(TEMP_DIR.iterdir()):
        TEMP_DIR.rmdir()


if __name__ == "__main__":
    main()

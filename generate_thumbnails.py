#!/usr/bin/env python3
"""
Generate story thumbnail images using DALL-E 3.

Usage:
    python generate_thumbnails.py "小红帽" "A little girl in a red hood..."
    python generate_thumbnails.py --batch prompts.json
    python generate_thumbnails.py --list

The --batch flag reads a JSON file mapping story names to DALL-E prompts:
    {
        "小红帽": "Classical oil painting style...",
        "白雪公主": "A beautiful princess..."
    }

Requires: OPENAI_API_KEY env var
"""

import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from openai import OpenAI
from PIL import Image

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"

STYLE_PREFIX = (
    "Classical oil painting style fairy tale illustration "
    "in the style of Pre-Raphaelite masters. "
)
STYLE_SUFFIX = (
    "\nWarm color palette with rich tones and detailed brushwork "
    "texture like a Renaissance masterpiece. "
    "No text, no words, no letters anywhere in the image."
)


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def generate_image(client, story_name: str, prompt: str, overwrite=False):
    IMAGES_DIR.mkdir(exist_ok=True)
    output_path = IMAGES_DIR / f"{story_name}.png"

    if output_path.exists() and not overwrite:
        print(f"  {story_name} — exists, skipping")
        return output_path

    full_prompt = STYLE_PREFIX + prompt + STYLE_SUFFIX
    print(f"  Generating: {story_name}")

    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1792x1024",
        quality="hd",
        n=1,
    )

    image_url = response.data[0].url
    img_response = requests.get(image_url)
    img = Image.open(io.BytesIO(img_response.content))
    img = img.resize((1600, 900), Image.Resampling.LANCZOS)
    img.save(output_path, "PNG")
    print(f"  Saved: {output_path.name}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    client = get_openai_client()

    if sys.argv[1] == "--list":
        images = sorted(IMAGES_DIR.glob("*.png")) if IMAGES_DIR.exists() else []
        print(f"Thumbnails ({len(images)}):")
        for img in images:
            print(f"  {img.stem}")
        return

    if sys.argv[1] == "--batch":
        prompts_file = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE_DIR / "prompts.json"
        if not prompts_file.exists():
            print(f"Prompts file not found: {prompts_file}")
            return
        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts = json.load(f)

        overwrite = "--overwrite" in sys.argv
        print(f"Generating {len(prompts)} thumbnails...")
        for i, (name, prompt) in enumerate(prompts.items(), 1):
            print(f"\n[{i}/{len(prompts)}]")
            try:
                generate_image(client, name, prompt, overwrite=overwrite)
                time.sleep(2)
            except Exception as e:
                print(f"  Error: {e}")
        return

    # Single image mode: generate_thumbnails.py "name" "prompt"
    story_name = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else f"A fairy tale scene depicting {story_name}."
    overwrite = "--overwrite" in sys.argv
    try:
        generate_image(client, story_name, prompt, overwrite=overwrite)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

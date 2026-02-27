# Story to Video

**Turn any written story into a fully narrated video with a single command.**

Drop a markdown file in, get an MP4 out — complete with AI-generated narration, cover art, and optional background music. Built for creators who want to publish story content to YouTube without touching audio or video editors.

```
story.md  →  AI narration  →  AI cover art  →  finished video
```

## Why this exists

Publishing narrated stories to YouTube is a proven content format — bedtime stories, fairy tales, language learning, audiobook previews — but the production workflow is tedious: record or generate audio, find or commission art, stitch it all together, export, upload, localize metadata for discoverability.

This pipeline automates the entire thing. Write your story in markdown, run one command, get a publish-ready MP4.

## What it does

| Step | What happens | Output |
|------|-------------|--------|
| **Narration** | Splits your story into chunks, sends each to OpenAI TTS, concatenates into one audio file | `narrations/<story>.mp3` |
| **Audio mix** | Overlays narration on background music (optional — works without it) | `mixed/<story>.mp3` |
| **Cover art** | Auto-generates a DALL-E 3 illustration from the story title if no image is provided | `images/<story>.png` |
| **Video** | Combines cover art + audio into a 1920x1080 MP4 | `videos/<story>.mp4` |

## Quick start

```bash
# Clone & install
git clone https://github.com/lymcho/story-to-video.git
cd story-to-video
pip install -r requirements.txt

# Set your OpenAI API key
cp .env.example .env
# Edit .env, then:
export $(cat .env | xargs)

# Run the full pipeline
python pipeline.py 格林童话-07-小红帽
```

That's it. One story file in `stories/`, one command, one video out.

### Optional extras

```bash
# Add background music (any .m4a file)
cp ~/Music/ambient.m4a background/background.m4a

# Provide your own cover art instead of generating one
cp ~/Art/cover.png images/格林童话-07-小红帽.png

# Run individual steps
python pipeline.py --step1 格林童话-07-小红帽   # Narration only
python pipeline.py --step2 格林童话-07-小红帽   # Audio mix only
python pipeline.py --step3 格林童话-07-小红帽   # Video only

# Process all stories at once
python pipeline.py --all

# Check what's been generated
python pipeline.py --status
```

## Project structure

```
story-to-video/
├── pipeline.py               # Main pipeline: story → video
├── generate_thumbnails.py    # Standalone DALL-E 3 cover art generation
├── generate_tts_gemini.py    # Alternative TTS via Google Gemini
├── upload_youtube.py         # YouTube upload with OAuth + scheduling
├── localize_youtube.py       # Auto-translate YouTube metadata via Gemini
├── stories/                  # Your story markdown files (input)
├── background/               # Background music file (optional)
├── images/                   # Cover art (auto-generated or manual)
├── narrations/               # TTS audio (auto-generated)
├── mixed/                    # Mixed audio (auto-generated)
└── videos/                   # Final MP4 files (auto-generated)
```

## YouTube publishing

Once your videos are ready, the included upload and localization scripts handle the rest:

- **`upload_youtube.py`** — OAuth-authenticated uploads with playlist support and daily scheduling
- **`localize_youtube.py`** — Uses Gemini to generate SEO-optimized English titles and descriptions, then writes them as YouTube localizations for international discoverability

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (for audio mixing and video creation)
- An [OpenAI API key](https://platform.openai.com/api-keys) (for TTS narration and DALL-E cover art)
- Google Gemini API key *(optional, for alternative TTS and YouTube localization)*
- Google OAuth credentials *(optional, for YouTube upload)*

## License

MIT

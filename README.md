# Story to Video

**Create a fully narrated YouTube audiobook channel in one command.**

An open-source YouTube automation pipeline that turns written stories into publish-ready videos — with AI-generated narration (OpenAI TTS), AI-generated cover art (DALL-E 3), optional background music mixing, and YouTube upload with localization. Built for faceless YouTube channels, audiobook creators, and anyone who wants to run an AI YouTube channel without touching an editor.

```
story.md  →  AI narration  →  AI cover art  →  finished video  →  YouTube
```

Whether you're building a faceless YouTube channel, a children's audiobook series, a story-to-video converter for language learning content, or just want a personal OpenAI TTS pipeline — drop in a markdown file and get an MP4 out.

<!-- TODO: Add demo GIF here
![Demo](docs/demo.gif)
-->

## Docker quick start

```bash
cp .env.example .env
# edit .env with your API keys
docker compose up --build
```

Run one-off command:

```bash
docker compose run --rm story-to-video python pipeline.py --help
```


## Use Cases

- **Faceless YouTube channels** — Automate narrated story content without showing your face or recording your voice
- **Audiobook generator** — Turn any written text into a narrated audiobook with a single command
- **Children's story channels** — Bilingual bedtime stories with AI narration and AI-generated illustrations
- **Language learning content** — Generate listen-along videos for students in any language
- **AI YouTube channel** — Full pipeline from text to published video with SEO-optimized metadata
- **Content repurposing** — Turn blog posts, short stories, or educational content into YouTube videos
- **YouTube upload automation** — Batch upload with scheduling, playlists, and auto-localized metadata

## What It Does

| Step | What happens | Output |
|------|-------------|--------|
| **Narration** | Splits your story into chunks, sends each to the OpenAI TTS pipeline, concatenates into one audio file | `narrations/<story>.mp3` |
| **Audio mix** | Overlays narration on background music (optional — works fine without it) | `mixed/<story>.mp3` |
| **Cover art** | DALL-E thumbnail generator — auto-generates an illustration from the story title if no image is provided | `images/<story>.png` |
| **Video** | Story to video converter — combines cover art + audio into a 1920x1080 MP4 | `videos/<story>.mp4` |
| **Upload** | YouTube upload automation with OAuth, playlists, and daily scheduling | Published to YouTube |
| **Localize** | Gemini-powered English metadata for international discoverability | YouTube localizations |

## Quick Start

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

### Run Individual Steps

```bash
python pipeline.py --step1 格林童话-07-小红帽   # Narration only
python pipeline.py --step2 格林童话-07-小红帽   # Audio mix only
python pipeline.py --step3 格林童话-07-小红帽   # Video only
python pipeline.py --all                        # Process all stories
python pipeline.py --status                     # Check progress
```

### Optional Extras

```bash
# Add background music (any .m4a file)
cp ~/Music/ambient.m4a background/background.m4a

# Provide your own cover art instead of generating one
cp ~/Art/cover.png images/格林童话-07-小红帽.png
```

## Example Output

> Once you run the pipeline on a story, you get three artifacts:

| Artifact | Description |
|----------|------------|
| **Narration** | Full-length AI-narrated MP3 of the story |
| **Cover art** | DALL-E 3 illustration in Pre-Raphaelite oil painting style |
| **Final video** | 1920x1080 MP4 ready to upload to YouTube |

<!-- TODO: Add actual examples
- 🎧 [Listen to generated narration](link)
- 🖼️ [See generated cover art](link)
- 🎬 [Watch final video on YouTube](link)
-->

## Project Structure

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

## YouTube Publishing

Once your videos are ready, the included upload and localization scripts handle the rest:

- **`upload_youtube.py`** — OAuth-authenticated YouTube upload automation with playlist support and daily scheduling
- **`localize_youtube.py`** — Uses Gemini to generate SEO-optimized English titles and descriptions, then writes them as YouTube localizations for international discoverability

## Roadmap

- [ ] Web UI for non-technical users
- [ ] Docker support for one-command deployment
- [ ] Multi-language batch generation
- [ ] Automatic YouTube Shorts generation
- [ ] Background animation support (Ken Burns effect)
- [ ] ElevenLabs TTS integration
- [ ] Auto-generated subtitles / SRT export
- [ ] Scheduling dashboard

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (for audio mixing and video creation)
- An [OpenAI API key](https://platform.openai.com/api-keys) (for TTS narration and DALL-E cover art)
- Google Gemini API key *(optional, for alternative TTS and YouTube localization)*
- Google OAuth credentials *(optional, for YouTube upload)*

## Keywords

story to video, youtube automation, ai youtube channel, faceless youtube, audiobook generator, story to video converter, openai tts pipeline, dall-e thumbnail generator, youtube upload automation, text to speech video, ai narration, ai video generator, content creation tools, youtube content automation, python youtube pipeline

## License

MIT

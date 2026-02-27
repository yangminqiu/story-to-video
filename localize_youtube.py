#!/usr/bin/env python3
"""
Add English localized metadata to YouTube videos using Gemini.

Fetches videos from your channel, generates search-optimized English
titles and descriptions via Gemini, and updates YouTube localizations.

Usage:
    python localize_youtube.py --list              # List videos + localization status
    python localize_youtube.py --preview           # Preview English titles
    python localize_youtube.py --all               # Localize all videos
    python localize_youtube.py --all --dry-run     # Generate but don't upload
    python localize_youtube.py <VIDEO_ID>          # Localize one video

Requires: GEMINI_API_KEY env var, client_secrets.json (Google OAuth)
"""

import json
import os
import pickle
import re
import sys
from pathlib import Path

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).parent
CLIENT_SECRETS = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.pickle"
CACHE_FILE = BASE_DIR / "localization_cache.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def get_youtube_service():
    credentials = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            credentials = flow.run_local_server(port=0, open_browser=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)
    return build("youtube", "v3", credentials=credentials)


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: set GEMINI_API_KEY or GOOGLE_API_KEY env var")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_channel_videos(youtube, max_results=500):
    resp = youtube.channels().list(part="contentDetails", mine=True).execute()
    if not resp.get("items"):
        return []
    uploads_id = resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos, next_page = [], None
    while len(videos) < max_results:
        resp = youtube.playlistItems().list(
            part="snippet", playlistId=uploads_id, maxResults=50, pageToken=next_page
        ).execute()
        for item in resp.get("items", []):
            videos.append({
                "id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
            })
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return videos


def get_video_localizations(youtube, video_id):
    try:
        resp = youtube.videos().list(part="localizations,snippet", id=video_id).execute()
        if resp.get("items"):
            item = resp["items"][0]
            return {
                "localizations": item.get("localizations", {}),
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
            }
    except HttpError:
        pass
    return None


def generate_english_metadata(gemini_client, chinese_title):
    prompt = f"""Translate this Chinese children's story YouTube title to an SEO-optimized English title.

CHINESE TITLE: {chinese_title}

Rules:
1. Translate the story name to English
2. Mention "Mandarin Chinese" so parents know the language
3. Include "bedtime story" or "kids story" and age range 3-6
4. Keep under 100 characters

Return JSON: {{"english_title": "...", "story_name_english": "..."}}"""

    resp = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7, response_mime_type="application/json"),
    )

    try:
        result = json.loads(resp.text)
        if isinstance(result, list):
            result = result[0]
        en_title = result.get("english_title", "")
        story_en = result.get("story_name_english", "Story")

        en_desc = (
            f"{story_en} - A gentle Mandarin Chinese bedtime story for children ages 3-8.\n\n"
            "Perfect for bilingual families, language immersion, and calm listening time.\n"
            "Subscribe for new classic stories every week!\n\n"
            "#MandarinStories #ChineseBedtimeStory #BilingualKids #LearnChinese"
        )
        return {"title": en_title, "description": en_desc}
    except (json.JSONDecodeError, KeyError):
        return None


def update_localizations(youtube, video_id, localizations):
    try:
        current = youtube.videos().list(part="snippet,localizations", id=video_id).execute()
        if not current.get("items"):
            return False
        existing = current["items"][0].get("localizations", {})
        existing.update(localizations)
        youtube.videos().update(
            part="localizations",
            body={"id": video_id, "localizations": existing},
        ).execute()
        return True
    except HttpError as e:
        print(f"  Failed: {e}")
        return False


def cmd_list(youtube):
    videos = get_channel_videos(youtube)
    for i, v in enumerate(videos, 1):
        loc = get_video_localizations(youtube, v["id"])
        has_en = "en" in loc.get("localizations", {}) if loc else False
        status = "EN" if has_en else "--"
        print(f"  {i:3}. [{status}] {v['title'][:60]}  ({v['id']})")


def cmd_localize_all(youtube, gemini, dry_run=False):
    videos = get_channel_videos(youtube)
    cache = load_cache()
    updated = skipped = failed = 0

    for i, v in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {v['title'][:50]}")
        loc = get_video_localizations(youtube, v["id"])
        if loc and "en" in loc.get("localizations", {}):
            print("  Already localized, skipping")
            skipped += 1
            continue

        en = cache.get(v["id"]) or generate_english_metadata(gemini, v["title"])
        if en:
            cache[v["id"]] = en
            save_cache(cache)
        else:
            failed += 1
            continue

        print(f"  EN: {en['title']}")
        if dry_run:
            continue

        if update_localizations(youtube, v["id"], {"en": en}):
            updated += 1
        else:
            failed += 1

    print(f"\nDone: {updated} updated, {skipped} skipped, {failed} failed")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    arg = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    youtube = get_youtube_service()

    if arg == "--list":
        cmd_list(youtube)
    elif arg in ("--preview", "--all"):
        gemini = get_gemini_client()
        cmd_localize_all(youtube, gemini, dry_run=(arg == "--preview" or dry_run))
    else:
        gemini = get_gemini_client()
        en = generate_english_metadata(gemini, arg)
        if en:
            print(f"EN title: {en['title']}")
            if not dry_run:
                update_localizations(youtube, arg, {"en": en})


if __name__ == "__main__":
    main()

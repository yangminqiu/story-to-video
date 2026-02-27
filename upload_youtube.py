#!/usr/bin/env python3
"""
Upload videos to YouTube with OAuth authentication.

Usage:
    python upload_youtube.py <video_file>                   # Upload one video
    python upload_youtube.py --all                          # Upload all in videos/
    python upload_youtube.py --all --schedule               # Daily schedule starting tomorrow
    python upload_youtube.py --list                         # List videos ready to upload
    python upload_youtube.py --playlists                    # List your playlists
    python upload_youtube.py <video> --playlist <ID>        # Upload to a playlist
    python upload_youtube.py --create-playlist "Name"       # Create playlist
    python upload_youtube.py --auth                         # Test authentication

Requires: client_secrets.json (Google OAuth), google-api-python-client
"""

import os
import re
import sys
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"
STORIES_DIR = BASE_DIR / "stories"
CLIENT_SECRETS = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.pickle"

SCOPES = ["https://www.googleapis.com/auth/youtube"]
DEFAULT_CATEGORY = "1"
DEFAULT_PRIVACY = "public"
DEFAULT_LANGUAGE = "zh"
DEFAULT_AUDIO_LANGUAGE = "zh-Hans"


def get_authenticated_service():
    credentials = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
        if credentials and hasattr(credentials, "scopes"):
            if not set(SCOPES).issubset(set(credentials.scopes or [])):
                credentials = None

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                print(f"Error: {CLIENT_SECRETS} not found. Set up Google OAuth first.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            credentials = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)

    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, video_path, privacy=DEFAULT_PRIVACY, playlist_id=None, publish_at=None):
    video_path = Path(video_path)
    story_name = video_path.stem

    # Strip leading number prefix like "07-小红帽" or "格林童话-07-小红帽"
    display_name = re.sub(r"^\d+[-_]", "", story_name)

    title = f"{display_name}"
    print(f"\n  Uploading: {title}")

    body = {
        "snippet": {
            "title": title,
            "description": "",
            "tags": ["story", "bedtime", "fairy tale", display_name],
            "categoryId": DEFAULT_CATEGORY,
            "defaultLanguage": DEFAULT_LANGUAGE,
            "defaultAudioLanguage": DEFAULT_AUDIO_LANGUAGE,
        },
        "status": {
            "privacyStatus": "private" if publish_at else privacy,
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }

    if publish_at:
        body["status"]["publishAt"] = publish_at.isoformat().replace("+00:00", "Z")

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=1024 * 1024)

    try:
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        print("  Uploading", end="", flush=True)
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"\r  Uploading: {int(status.progress() * 100)}%", end="", flush=True)

        video_id = response["id"]
        url = f"https://youtu.be/{video_id}"
        print(f"\r  Done: {url}")

        if playlist_id:
            add_to_playlist(youtube, video_id, playlist_id)

        return {"success": True, "video_id": video_id, "url": url, "title": title}
    except HttpError as e:
        print(f"\r  Upload failed: {e.reason}")
        return {"success": False, "error": str(e)}


def add_to_playlist(youtube, video_id, playlist_id):
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
        ).execute()
    except HttpError as e:
        print(f"  Could not add to playlist: {e.reason}")


def list_playlists(youtube):
    response = youtube.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50).execute()
    for item in response.get("items", []):
        print(f"  {item['snippet']['title']} ({item['contentDetails']['itemCount']} videos)  ID: {item['id']}")


def list_videos():
    videos = sorted(VIDEOS_DIR.glob("*.mp4"))
    print(f"Videos ready ({len(videos)}):")
    for v in videos:
        size = v.stat().st_size / (1024 * 1024)
        print(f"  {v.stem} ({size:.1f} MB)")
    return videos


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        list_videos()
        return

    arg = sys.argv[1]

    if arg == "--list":
        list_videos()
        return

    if arg == "--auth":
        get_authenticated_service()
        print("Authentication OK")
        return

    youtube = get_authenticated_service()

    if arg == "--playlists":
        list_playlists(youtube)
        return

    if arg == "--create-playlist":
        title = sys.argv[2] if len(sys.argv) > 2 else "My Playlist"
        youtube.playlists().insert(
            part="snippet,status",
            body={"snippet": {"title": title}, "status": {"privacyStatus": "public"}},
        ).execute()
        print(f"Created playlist: {title}")
        return

    playlist_id = None
    if "--playlist" in sys.argv:
        idx = sys.argv.index("--playlist")
        playlist_id = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    schedule = "--schedule" in sys.argv
    privacy = "private" if "--private" in sys.argv else "unlisted" if "--unlisted" in sys.argv else DEFAULT_PRIVACY

    if arg == "--all":
        videos = sorted(VIDEOS_DIR.glob("*.mp4"))
    else:
        vp = Path(arg)
        if not vp.exists():
            vp = VIDEOS_DIR / f"{arg}.mp4"
        if not vp.exists():
            print(f"Video not found: {arg}")
            return
        videos = [vp]

    publish_times = [None] * len(videos)
    if schedule:
        tz = ZoneInfo("America/Los_Angeles")
        start = datetime.now(tz).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        publish_times = [start + timedelta(days=i) for i in range(len(videos))]

    results = [upload_video(youtube, v, privacy, playlist_id, pt) for v, pt in zip(videos, publish_times)]
    ok = sum(1 for r in results if r.get("success"))
    print(f"\nDone: {ok}/{len(results)} uploaded")


if __name__ == "__main__":
    main()

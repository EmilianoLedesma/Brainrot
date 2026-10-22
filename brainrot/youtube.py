"""Project-scoped Google OAuth, reviewed uploads, and channel analytics."""
from datetime import date, datetime, timedelta, timezone
from contextlib import contextmanager
import hashlib
import base64
import json
import os
import re
import secrets
import sqlite3
import tempfile
import time
from urllib.parse import urlencode
import requests

from . import db, media, publish, retention, render

SCOPES = ("https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly")


def redirect_uri():
    return os.getenv("YOUTUBE_REDIRECT_URI", "http://127.0.0.1:8001/youtube/callback")


@contextmanager
def _states():
    folder = media.PROJECT_ROOT / ".brainrot"
    folder.mkdir(exist_ok=True)
    connection = sqlite3.connect(folder / "oauth.sqlite", timeout=10)
    connection.execute("create table if not exists states (nonce text primary key, verifier text not null, expires integer not null)")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def status():
    try:
        data = publish.credentials("youtube")
    except publish.MissingCredentials:
        data = {}
    return {"configured": bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET")),
            "connected": bool(data.get("refresh_token") or data.get("access_token")),
            "channel_title": data.get("channel_title"), "channel_id": data.get("channel_id"),
            "privacy_status": data.get("privacy_status", "private"), "auto_publish": data.get("auto_publish", False),
            "auto_publish_after": data.get("auto_publish_after"),
            "redirect_uri": redirect_uri()}


def connect():
    if not os.getenv("YOUTUBE_CLIENT_ID") or not os.getenv("YOUTUBE_CLIENT_SECRET"):
        raise ValueError("Configure this project's YouTube OAuth client first.")
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    with _states() as connection:
        connection.execute("delete from states where expires < ?", (time.time(),))
        connection.execute("insert into states values (?,?,?)", (hashlib.sha256(state.encode()).hexdigest(), verifier, int(time.time()) + 600))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return {"url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": os.environ["YOUTUBE_CLIENT_ID"], "redirect_uri": redirect_uri(), "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})}


def finish(state: str, code: str):
    # Atomic one-time consumption prevents concurrent callback replay.
    with _states() as connection:
        row = connection.execute("delete from states where nonce=? and expires>=? returning verifier",
                                 (hashlib.sha256(state.encode()).hexdigest(), int(time.time()))).fetchone()
    if not row:
        raise ValueError("This connection request expired or was already used. Start again from YouTube.")
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YOUTUBE_CLIENT_ID"], "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "code": code, "code_verifier": row[0], "redirect_uri": redirect_uri(), "grant_type": "authorization_code"}, timeout=30)
    response.raise_for_status()
    token = response.json()
    if not set(SCOPES).issubset(set(token.get("scope", "").split())) or not token.get("refresh_token"):
        raise ValueError("Grant upload, channel-read, and analytics access to finish connecting.")
    channel = _get("channels", token["access_token"], part="snippet,contentDetails", mine="true").get("items", [])
    if not channel:
        raise ValueError("This Google account has no available YouTube channel.")
    channel = channel[0]
    data = {"access_token": token["access_token"], "refresh_token": token["refresh_token"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=token.get("expires_in", 3600))).isoformat(),
            "channel_id": channel["id"], "channel_title": channel["snippet"]["title"],
            "uploads_playlist": channel["contentDetails"]["relatedPlaylists"]["uploads"],
            "scope": token["scope"], "privacy_status": "private", "auto_publish": False}
    db.client().table("platform_credentials").upsert({"platform": "youtube", "data": data}, on_conflict="platform").execute()
    return {"channel_title": data["channel_title"]}


def _get(resource: str, token: str, **params):
    response = requests.get("https://www.googleapis.com/youtube/v3/" + resource, params=params,
                            headers={"Authorization": "Bearer " + token}, timeout=30)
    response.raise_for_status()
    return response.json()


def disconnect():
    active = db.client().table("publications").select("id").eq("platform", "youtube").eq("status", "uploading").execute().data
    if active:
        raise ValueError("Wait for the current YouTube upload to finish before disconnecting.")
    # Stop worker access first. Revocation remains a separate Google account control.
    db.client().table("platform_credentials").delete().eq("platform", "youtube").execute()


def settings(auto_publish: bool, privacy_status: str, include_queued: bool):
    data = publish.credentials("youtube")
    was_enabled = data.get("auto_publish", False)
    data.update(auto_publish=auto_publish, privacy_status=privacy_status)
    if auto_publish and include_queued:
        data["auto_publish_after"] = None
    elif auto_publish and not was_enabled:
        data["auto_publish_after"] = datetime.now(timezone.utc).isoformat()
    publish._save("youtube", data)
    return status()


def videos():
    data = publish.credentials("youtube")
    token = publish.youtube_token(data)
    playlist = data.get("uploads_playlist")
    if not playlist:
        channel = _get("channels", token, part="contentDetails", mine="true")["items"][0]
        playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    rows = _get("playlistItems", token, part="snippet,contentDetails", playlistId=playlist, maxResults=25).get("items", [])
    return [{"id": row["contentDetails"]["videoId"], "title": row["snippet"]["title"],
             "published_at": row["snippet"].get("publishedAt"),
             "url": "https://www.youtube.com/watch?v=" + row["contentDetails"]["videoId"]} for row in rows]


def analytics(video_id: str, start: date, end: date):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) or start > end or end > date.today():
        raise ValueError("Choose a video and a valid date range ending today or earlier.")
    data = publish.credentials("youtube")
    token = publish.youtube_token(data)
    metadata = _get("videos", token, part="contentDetails", id=video_id).get("items", [])
    if not metadata:
        raise ValueError("This video is unavailable.")
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", metadata[0]["contentDetails"]["duration"])
    if not match:
        raise ValueError("This video's duration is not available yet.")
    seconds = sum(float(value or 0) * multiplier for value, multiplier in zip(match.groups(), (3600, 60, 1)))
    response = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers={"Authorization": "Bearer " + token},
                            params={"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
                                    "metrics": "audienceWatchRatio", "dimensions": "elapsedVideoTimeRatio", "filters": "video==" + video_id}, timeout=30)
    response.raise_for_status()
    result = response.json()
    headers = [header["name"] for header in result.get("columnHeaders", [])]
    rows = result.get("rows", [])
    if len(rows) < 3:
        raise ValueError("YouTube has not returned enough retention data for this video and date range yet.")
    x, y = headers.index("elapsedVideoTimeRatio"), headers.index("audienceWatchRatio")
    csv_text = "\n".join(f"{row[x]},{row[y]}" for row in rows)
    subtitle_text = ""
    if media.local():
        publications = db.client().table("publications").select("*").eq("platform", "youtube").eq("platform_post_id", video_id).limit(1).execute().data
        if publications:
            item = publish.target(publications[0])
            subtitle_file = media.path(item["path"]).with_suffix(".srt")
            if subtitle_file.is_file():
                subtitle_text = subtitle_file.read_text(encoding="utf-8")
    report = retention.analyze(csv_text, axis="fraction", retention_unit="fraction", duration_seconds=seconds,
                               transcript_srt=subtitle_text, allow_partial_start=True)
    return {**report, "video_id": video_id, "start_date": start.isoformat(), "end_date": end.isoformat()}


def prepare_upload(source: str, target_id: str, metadata: dict):
    rows = db.client().table("story_chapters" if source == "chapter" else "clips").select("id,status").eq("id", target_id).execute().data
    if not rows or rows[0]["status"] != "ready":
        raise ValueError("Choose a finished video from Output.")
    publish.credentials("youtube")
    field = "chapter_id" if source == "chapter" else "clip_id"
    existing = db.client().table("publications").select("*").eq("platform", "youtube").eq(field, target_id).execute().data
    if not existing:
        db.client().table("publications").upsert({"platform": "youtube", field: target_id, "status": "scheduled"},
            on_conflict=f"{field},platform", ignore_duplicates=True).execute()
        existing = db.client().table("publications").select("*").eq("platform", "youtube").eq(field, target_id).execute().data
    row = existing[0]
    if row["status"] == "published":
        return row, False
    if row["status"] != "scheduled" or not publish._take(row["id"]):
        raise ValueError("This video is already uploading or needs its previous upload checked in YouTube Studio.")
    db.client().table("publications").update({"metadata": metadata}).eq("id", row["id"]).execute()
    return {**row, "metadata": metadata}, True


def upload_claimed(row):
    try:
        item = publish.target(row)
        content = db.download(item["path"])
        with tempfile.TemporaryDirectory() as folder:
            from pathlib import Path
            path = Path(folder) / "reviewed.mp4"
            path.write_bytes(content)
            render.check_video(str(path))
        publish.publish_one(row, claimed=True)
    except Exception:
        db.client().table("publications").update({"status": "failed", "error": "Upload did not complete. Check YouTube Studio before trying again."}).eq("id", row["id"]).eq("status", "uploading").execute()


def uploads():
    rows = db.client().table("publications").select("id,status,url,error,created_at,metadata").eq("platform", "youtube").order("created_at", desc=True).limit(30).execute().data
    return [{"id": row["id"], "status": row["status"], "url": row.get("url"), "title": (row.get("metadata") or {}).get("title"),
             "error": "Upload needs attention. Check YouTube Studio before trying again." if row.get("error") else None} for row in rows]

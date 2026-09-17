"""Phase 5: upload due publications to YouTube, TikTok, and Instagram.

There is deliberately no OAuth authorization flow here. Registering the developer
apps and granting consent is a manual, browser-bound step; this module only reads
whatever tokens ended up in `platform_credentials` and uses them. Until a row
exists for a platform, its uploads fail with a clear message and nothing else.

Populate a platform like this, once its app exists:

    db.client().table("platform_credentials").upsert({
        "platform": "youtube",
        "data": {"access_token": ..., "refresh_token": ..., "client_id": ..., "client_secret": ...},
    }, on_conflict="platform").execute()
"""

import json
import time
from datetime import datetime, timedelta, timezone

import requests

from . import db

TIMEOUT = 120
# Signed URLs handed to Instagram have to outlive its transcoding queue.
SIGNED_URL_TTL = 3600


class MissingCredentials(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def credentials(platform: str) -> dict:
    rows = (
        db.client()
        .table("platform_credentials")
        .select("data")
        .eq("platform", platform)
        .execute()
        .data
    )
    if not rows or not rows[0]["data"]:
        raise MissingCredentials(
            f"no credentials for {platform}: register the app, then insert a "
            f"platform_credentials row"
        )
    return rows[0]["data"]


def _save(platform: str, data: dict) -> None:
    db.client().table("platform_credentials").update(
        {"data": data, "updated_at": _now().isoformat()}
    ).eq("platform", platform).execute()


def youtube_token(data: dict) -> str:
    """Google access tokens last an hour, so refresh before they lapse.

    This is a token refresh, not an authorization grant - it needs a refresh_token
    that the manual consent step already produced.
    """
    expires_at = data.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) - _now() > timedelta(minutes=5):
        return data["access_token"]
    if not data.get("refresh_token"):
        return data["access_token"]

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    fresh = response.json()
    data["access_token"] = fresh["access_token"]
    data["expires_at"] = (_now() + timedelta(seconds=fresh.get("expires_in", 3600))).isoformat()
    _save("youtube", data)
    return data["access_token"]


def post_youtube(video: bytes, title: str, description: str) -> tuple[str, str]:
    """Resumable upload. Returns (video id, watch URL).

    A vertical video under three minutes is treated as a Short by YouTube itself -
    there is no API field that declares one.
    """
    data = credentials("youtube")
    token = youtube_token(data)
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": "24",
        },
        "status": {
            "privacyStatus": data.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }

    start = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"part": "snippet,status", "uploadType": "resumable"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(len(video)),
        },
        data=json.dumps(metadata),
        timeout=TIMEOUT,
    )
    start.raise_for_status()
    session_url = start.headers["Location"]

    upload = requests.put(
        session_url,
        headers={"Content-Type": "video/mp4", "Content-Length": str(len(video))},
        data=video,
        timeout=TIMEOUT,
    )
    upload.raise_for_status()
    video_id = upload.json()["id"]
    return video_id, f"https://youtube.com/shorts/{video_id}"


def post_tiktok(video: bytes, title: str) -> tuple[str, str]:
    """Direct post via FILE_UPLOAD in a single chunk.

    PULL_FROM_URL would need TikTok to have verified the bucket's domain, which a
    Supabase signed URL cannot satisfy.
    """
    data = credentials("tiktok")
    headers = {
        "Authorization": f"Bearer {data['access_token']}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    size = len(video)
    init = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": title[:2200],
                # Until TikTok audits the app every post is forced private anyway,
                # so this default matches what an unaudited client actually gets.
                "privacy_level": data.get("privacy_level", "SELF_ONLY"),
                "disable_comment": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        },
        timeout=TIMEOUT,
    )
    init.raise_for_status()
    payload = init.json()["data"]

    upload = requests.put(
        payload["upload_url"],
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        data=video,
        timeout=TIMEOUT,
    )
    upload.raise_for_status()
    # TikTok exposes no permalink until processing finishes, so only the
    # publish_id is knowable here.
    return payload["publish_id"], ""


def post_instagram(video_url: str, caption: str) -> tuple[str, str]:
    """Container, poll, publish. Instagram pulls the file from `video_url` itself."""
    data = credentials("instagram")
    base = f"https://graph.instagram.com/v25.0/{data['ig_user_id']}"
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    container = requests.post(
        f"{base}/media",
        headers=headers,
        json={"media_type": "REELS", "video_url": video_url, "caption": caption[:2200]},
        timeout=TIMEOUT,
    )
    container.raise_for_status()
    creation_id = container.json()["id"]

    # Instagram documents polling once a minute for at most five minutes.
    for _ in range(5):
        status = requests.get(
            f"https://graph.instagram.com/v25.0/{creation_id}",
            headers=headers,
            params={"fields": "status_code"},
            timeout=TIMEOUT,
        )
        status.raise_for_status()
        code = status.json().get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"instagram container {code}")
        time.sleep(60)
    else:
        raise RuntimeError("instagram container still processing after five minutes")

    published = requests.post(
        f"{base}/media_publish",
        headers=headers,
        json={"creation_id": creation_id},
        timeout=TIMEOUT,
    )
    published.raise_for_status()
    media_id = published.json()["id"]
    return media_id, f"https://www.instagram.com/reel/{media_id}/"


def target(publication: dict) -> dict:
    """The clip or chapter a publication points at, with its storage path and title."""
    client = db.client()
    if publication["clip_id"]:
        row = (
            client.table("clips")
            .select("title,storage_path")
            .eq("id", publication["clip_id"])
            .single()
            .execute()
            .data
        )
        return {"title": row["title"] or "clip", "path": row["storage_path"]}

    row = (
        client.table("story_chapters")
        .select("chapter_index,video_path,stories(title)")
        .eq("id", publication["chapter_id"])
        .single()
        .execute()
        .data
    )
    name = (row.get("stories") or {}).get("title") or "story"
    index = row["chapter_index"]
    return {
        "title": name if index == 1 else f"{name} - part {index}",
        "path": row["video_path"],
    }


def publish_one(publication: dict) -> None:
    """Upload one publication and record what happened to it."""
    client = db.client()
    client.table("publications").update({"status": "uploading"}).eq(
        "id", publication["id"]
    ).execute()

    try:
        item = target(publication)
        if not item["path"]:
            raise RuntimeError("nothing rendered for this publication yet")
        platform = publication["platform"]

        if platform == "youtube":
            post_id, url = post_youtube(db.download(item["path"]), item["title"], item["title"])
        elif platform == "tiktok":
            post_id, url = post_tiktok(db.download(item["path"]), item["title"])
        elif platform == "instagram":
            post_id, url = post_instagram(
                db.signed_url(item["path"], SIGNED_URL_TTL), item["title"]
            )
        else:
            raise RuntimeError(f"unknown platform {platform}")

        client.table("publications").update(
            {
                "status": "published",
                "published_at": _now().isoformat(),
                "platform_post_id": post_id,
                "url": url or None,
                "error": None,
            }
        ).eq("id", publication["id"]).execute()

    except Exception as exc:
        # A failure lands on `failed` and stays there. Re-queueing is a manual call:
        # an upload that timed out after the platform accepted it would otherwise
        # post the same video twice.
        client.table("publications").update(
            {"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:2000]}
        ).eq("id", publication["id"]).execute()
        raise


def run_due(limit: int = 5) -> list[str]:
    """Publish everything whose time has come. Returns the ids that went out."""
    from . import scheduler

    published = []
    for publication in scheduler.due(limit):
        try:
            publish_one(publication)
            published.append(publication["id"])
            print(f"published {publication['platform']} {publication['id']}")
        except MissingCredentials as exc:
            print(f"skipping {publication['platform']}: {exc}")
        except Exception as exc:
            print(f"failed {publication['platform']} {publication['id']}: {exc}")
    return published

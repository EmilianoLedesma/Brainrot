"""Provider-specific video discovery and bounded, local downloads with provenance."""
import json
import math
import os
import re
import subprocess
from urllib.parse import urlsplit
import requests

from . import db, media

MAX_BYTES = 200_000_000


def _json(url, **options):
    response = requests.get(url, timeout=25, **options)
    response.raise_for_status()
    return response.json()


def search(provider: str, query: str) -> list[dict]:
    if provider == "pexels":
        key = os.getenv("PEXELS_API_KEY")
        if not key:
            raise ValueError("Add PEXELS_API_KEY to this project's .env to search Pexels. NASA works without it.")
        rows = _json("https://api.pexels.com/v1/videos/search", params={"query": query, "per_page": 8}, headers={"Authorization": key}).get("videos", [])
        return [{"id": str(row["id"]), "provider": provider, "title": row.get("url", "").rstrip("/").rsplit("/", 1)[-1],
                 "preview": row.get("image"), "source_url": row["url"], "credit": row.get("user", {}).get("name", "Pexels"),
                 "duration_seconds": row.get("duration")} for row in rows]
    if provider == "nasa":
        rows = _json("https://images-api.nasa.gov/search", params={"q": query, "media_type": "video", "page_size": 8}).get("collection", {}).get("items", [])
        return [{"id": row["data"][0]["nasa_id"], "provider": provider, "title": row["data"][0].get("title", "NASA video"),
                 "preview": next((link["href"] for link in row.get("links", []) if link.get("rel") == "preview"), None),
                 "source_url": "https://images.nasa.gov/details/" + row["data"][0]["nasa_id"],
                 "credit": row["data"][0].get("photographer") or row["data"][0].get("center", "NASA"), "duration_seconds": None} for row in rows if row.get("data")]
    raise ValueError("Choose NASA or Pexels.")


def _id(provider: str, asset_id: str):
    if provider not in {"nasa", "pexels"} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,149}", asset_id):
        raise ValueError("Choose an item from the media search results.")


def _metadata_path(provider, asset_id):
    _id(provider, asset_id)
    return f"library/{provider}/{asset_id}.json"


def import_video(provider: str, asset_id: str) -> dict:
    _id(provider, asset_id)
    destination = f"backgrounds/{provider}-{asset_id}.mp4"
    if media.path(_metadata_path(provider, asset_id)).is_file() and media.path(destination).is_file():
        return json.loads(media.path(_metadata_path(provider, asset_id)).read_text(encoding="utf-8"))
    if provider == "pexels":
        key = os.getenv("PEXELS_API_KEY")
        if not key or not asset_id.isdigit():
            raise ValueError("Pexels needs an API key and a video selected from its search results.")
        row = _json(f"https://api.pexels.com/v1/videos/videos/{asset_id}", headers={"Authorization": key})
        files = [file for file in row.get("video_files", []) if file.get("file_type") == "video/mp4" and file.get("height")]
        files.sort(key=lambda file: abs(file["height"] - 1920) + abs(file.get("width", 1080) - 1080))
        urls = [file["link"] for file in files]
        info = {"title": row.get("url", "Pexels video").rstrip("/").rsplit("/", 1)[-1], "source_url": row["url"],
                "credit": row.get("user", {}).get("name", "Pexels"), "license_url": "https://www.pexels.com/license/"}
        hosts = {"videos.pexels.com", "player.vimeo.com"}
    else:
        assets = _json(f"https://images-api.nasa.gov/asset/{asset_id}").get("collection", {}).get("items", [])
        urls = [asset["href"] for asset in assets if asset.get("href", "").lower().endswith(".mp4")]
        urls.sort(key=lambda url: ("~orig" in url, "~large" in url, "~medium" not in url))
        info = {"title": asset_id, "source_url": f"https://images.nasa.gov/details/{asset_id}",
                "credit": "NASA (check the source record for additional credits)", "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/"}
        hosts = {"images-assets.nasa.gov"}
    if not urls:
        raise ValueError("This item has no downloadable MP4 video.")
    url = urls[0]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in hosts or parsed.username or parsed.port not in {None, 443}:
        raise ValueError("This provider returned an unsupported media location.")
    with requests.get(url, stream=True, allow_redirects=False, timeout=60) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("This video could not be downloaded directly.")
        if int(response.headers.get("Content-Length", "0")) > MAX_BYTES:
            raise ValueError("Choose a video smaller than 200 MB.")
        content = bytearray()
        for chunk in response.iter_content(1024 * 1024):
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise ValueError("Choose a video smaller than 200 MB.")
    media.save(destination, bytes(content))
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media.path(destination))],
                               capture_output=True, text=True, check=True, timeout=30)
        seconds = float(probe.stdout.strip())
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("This video is empty.")
    except Exception:
        media.path(destination).unlink(missing_ok=True)
        raise ValueError("This download is not a playable video.") from None
    result = {**info, "provider": provider, "id": asset_id, "storage_path": destination, "duration_seconds": seconds}
    media.save(_metadata_path(provider, asset_id), json.dumps(result, indent=2).encode())
    return result


def items() -> list[dict]:
    result = []
    backgrounds = db.client().table("background_clips").select("*").execute().data
    active = {row["storage_path"] for row in backgrounds if row.get("active")}
    for path in sorted((media.root() / "library").glob("*/*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        if media.path(item["storage_path"]).is_file():
            result.append({**item, "active": item["storage_path"] in active})
    known = {item["storage_path"] for item in result}
    for row in backgrounds:
        if row["storage_path"] not in known:
            result.append({"id": row["id"], "provider": "existing", "title": row.get("label") or "Project background",
                "credit": "Project background", "storage_path": row["storage_path"], "active": bool(row.get("active")),
                "source_url": None, "license_url": None, "duration_seconds": row.get("duration_seconds")})
    return result


def activate(provider: str, asset_id: str) -> dict:
    item = json.loads(media.path(_metadata_path(provider, asset_id)).read_text(encoding="utf-8"))
    if not media.path(item["storage_path"]).is_file():
        raise FileNotFoundError("Media is missing on this computer")
    db.client().rpc("activate_library_background", {"p_path": item["storage_path"], "p_label": item["title"][:150],
        "p_duration": item["duration_seconds"], "p_provider": provider}).execute()
    return item

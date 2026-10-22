"""Safe, per-job finished-video details shared by Output and Inspect."""
from . import db, media


def _url(value):
    return value if isinstance(value, str) and value.startswith("https://") else None


def for_job(job_id, base_url):
    client = db.client()
    stories = client.table("stories").select("id,title,topic,permalink").eq("job_id", job_id).execute().data
    parents = {row["id"]: row for row in stories}
    chapters = client.table("story_chapters").select("*").in_("story_id", list(parents)).eq("status", "ready").execute().data if parents else []
    clips = client.table("clips").select("*").eq("job_id", job_id).eq("status", "ready").execute().data
    sources = client.table("source_videos").select("id,youtube_url,transcript").eq("job_id", job_id).execute().data if clips else []
    sources = {row["id"]: row for row in sources}
    publications = []
    for field, ids in (("chapter_id", [row["id"] for row in chapters]), ("clip_id", [row["id"] for row in clips])):
        if ids:
            publications += client.table("publications").select("*").in_(field, ids).execute().data
    result = []
    for source, rows in (("chapter", chapters), ("clip", clips)):
        for row in rows:
            path = row.get("video_path") if source == "chapter" else row.get("storage_path")
            if not path:
                continue
            parent = parents.get(row.get("story_id"), {}) if source == "chapter" else sources.get(row.get("source_video_id"), {})
            narration = row.get("text", "")
            if source == "clip":
                transcript = parent.get("transcript") or []
                if isinstance(transcript, dict):
                    transcript = transcript.get("segments", [])
                narration = " ".join(cue.get("text", "") for cue in transcript if cue.get("end", 0) > float(row["start_seconds"]) and cue.get("start", 0) < float(row["end_seconds"]))
            title = (parent.get("title") or parent.get("topic") or "Story") if source == "chapter" else (row.get("title") or "Clip")
            if source == "chapter" and row["chapter_index"] > 1:
                title += f" — part {row['chapter_index']}"
            url = db.signed_url(path)
            if url.startswith("/"):
                url = base_url.rstrip("/") + url
            visible_publications = []
            for publication in publications:
                if publication.get(source + "_id") != row["id"]:
                    continue
                metadata = publication.get("metadata") or {}
                visible_publications.append({"id": publication["id"], "platform": publication["platform"], "status": publication["status"],
                    "url": _url(publication.get("url")), "video_id": publication.get("platform_post_id") if publication["platform"] == "youtube" else None,
                    "published_at": publication.get("published_at"), "scheduled_at": publication.get("scheduled_at"),
                    "metadata": {key: metadata.get(key) for key in ("title", "description", "tags", "privacy_status", "youtube_mode", "made_for_kids", "contains_synthetic_media")},
                    "analytics": {key: (publication.get("analytics") or {}).get(key) for key in ("views", "engagedViews", "likes", "comments", "averageViewDuration", "averageViewPercentage", "start_date", "end_date", "measured_at")}})
            subtitles = ""
            if media.local():
                sidecar = media.path(path).with_suffix(".srt")
                if sidecar.is_file() and sidecar.stat().st_size <= 250_000:
                    subtitles = sidecar.read_text(encoding="utf-8")
            result.append({"id": row["id"], "job_id": job_id, "source": source, "title": title, "url": url, "created_at": row.get("created_at"), "subtitles": subtitles,
                "narration": narration, "source_url": _url(parent.get("permalink") or parent.get("youtube_url")), "publications": visible_publications})
    return result

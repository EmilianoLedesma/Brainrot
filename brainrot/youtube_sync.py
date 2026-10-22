"""Bounded YouTube analytics ingestion, independent of pacing and uploading."""
from datetime import datetime, timedelta, timezone
import math
import re

import requests

from . import db, publish
from .application.analytics import Performance
from .observability.logging import event

METRICS = ("views", "engagedViews", "likes", "comments", "averageViewDuration", "averageViewPercentage")


def sync(*, limit=10):
    try:
        credentials = publish.credentials("youtube")
    except publish.MissingCredentials:
        return {"updated": 0, "waiting": 0, "failed": 0}
    now = datetime.now(timezone.utc)
    rows = db.client().table("publications").select("*").eq("platform", "youtube").eq("status", "published").order("analytics_checked_at", nullsfirst=True).limit(100).execute().data
    due = [row for row in rows if row.get("platform_post_id") and
           (not row.get("analytics_checked_at") or datetime.fromisoformat(row["analytics_checked_at"]) <= now - timedelta(hours=6)) and
           (not (row.get("metadata") or {}).get("channel_id") or (row.get("metadata") or {})["channel_id"] == credentials.get("channel_id"))][:limit]
    result = {"updated": 0, "waiting": 0, "failed": 0}
    if not due:
        return result
    token = publish.youtube_token(credentials)
    for row in due:
        try:
            video_id = row["platform_post_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError("Invalid YouTube video identifier")
            start = datetime.fromisoformat(row["published_at"] or row["created_at"]).date()
            end = now.date() - timedelta(days=1)
            if start > end:
                result["waiting"] += 1
                db.client().table("publications").update({"analytics_checked_at": now.isoformat()}).eq("id", row["id"]).execute()
                continue
            response = requests.get("https://youtubeanalytics.googleapis.com/v2/reports", headers={"Authorization": "Bearer " + token},
                params={"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(), "metrics": ",".join(METRICS), "filters": "video==" + video_id}, timeout=30)
            response.raise_for_status()
            body = response.json()
            values = body.get("rows", [])
            patch = {"analytics_checked_at": now.isoformat()}
            if not values:
                result["waiting"] += 1
            else:
                metrics = dict(zip((header["name"] for header in body["columnHeaders"]), values[0]))
                if any(name not in metrics or not math.isfinite(float(metrics[name])) or float(metrics[name]) < 0 for name in METRICS):
                    raise ValueError("Incomplete analytics report")
                patch["analytics"] = {**metrics, "start_date": start.isoformat(), "end_date": end.isoformat(),
                    "measured_at": now.isoformat(), "channel_id": credentials.get("channel_id")}
                # Zero views means insufficient evidence, not zero retention.
                if row.get("chapter_id") and metrics["engagedViews"] > 0:
                    performance = Performance("youtube", video_id, now, views=int(metrics["views"]), retention_pct=min(float(metrics["averageViewPercentage"]), 100))
                    db.client().table("chapter_metrics").insert({"chapter_id": row["chapter_id"], "platform": "youtube", "views": performance.views,
                        "likes": int(metrics["likes"]), "comments": int(metrics["comments"]), "avg_watch_seconds": metrics["averageViewDuration"],
                        "retention_pct": performance.retention_pct, "captured_at": now.isoformat()}).execute()
                result["updated"] += 1
            db.client().table("publications").update(patch).eq("id", row["id"]).execute()
        except Exception as error:
            result["failed"] += 1
            # Throttle failures too; one unavailable service cannot flood requests.
            db.client().table("publications").update({"analytics_checked_at": now.isoformat()}).eq("id", row["id"]).execute()
            event("youtube_analytics_failed", publication_id=row["id"], error_type=type(error).__name__)
    return result


def performance():
    credentials = publish.credentials("youtube")
    rows = db.client().table("publications").select("id,url,metadata,analytics,analytics_checked_at").eq("platform", "youtube").eq("status", "published").order("published_at", desc=True).limit(50).execute().data
    return [{"id": row["id"], "title": (row.get("metadata") or {}).get("title") or "YouTube video", "url": row.get("url"),
             "metrics": row.get("analytics") or {}, "checked_at": row.get("analytics_checked_at")} for row in rows
            if not (row.get("analytics") or {}).get("channel_id") or row["analytics"]["channel_id"] == credentials.get("channel_id")]

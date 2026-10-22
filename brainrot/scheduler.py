"""Publishing schedule and chapter pacing.

Chapter one of a story goes out immediately. Every chapter after it waits on the
previous chapter's retention, so a story nobody is finishing stops consuming the
feed instead of dumping ten parts into it.

Nothing here uploads anything - it only decides *when* each piece should go out.
The posting itself is Phase 5 and needs the developer apps registered first.
"""

from datetime import datetime, timedelta, timezone

from . import db
from .application.analytics import ABANDON_BELOW_PCT, METRICS_GRACE, PACING, gap_for, next_chapter

PLATFORMS = ("youtube", "tiktok", "instagram")



def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


def queue(target: str, target_id: str, when: datetime) -> list[dict]:
    """Schedule one clip or chapter on every platform at `when`.

    A platform that already has a publication for this target keeps it, so
    planning the same clip or chapter twice (a retried job) never double-posts.
    """
    options = _youtube_options(target, target_id)
    rows = [
        {"platform": platform, target: target_id, "scheduled_at": when.isoformat()}
        for platform in PLATFORMS if platform != "youtube" or not options or options.get("mode") != "off"
    ]
    if options:
        for row in rows:
            if row["platform"] == "youtube":
                row["metadata"] = {**{key: value for key, value in options.items() if key != "mode"}, "youtube_mode": options["mode"]}
    return (
        db.client()
        .table("publications")
        .upsert(rows, on_conflict=f"{target},platform", ignore_duplicates=True)
        .execute()
        .data
    )


def _youtube_options(target, target_id):
    client = db.client()
    rows = client.table("clips" if target == "clip_id" else "story_chapters").select("*").eq("id", target_id).execute().data
    if not rows:
        return None
    row = rows[0]
    if target == "chapter_id":
        stories = client.table("stories").select("job_id").eq("id", row["story_id"]).execute().data
        if not stories:
            return None
        row = stories[0]
    jobs = client.table("jobs").select("params").eq("id", row.get("job_id")).execute().data
    return (jobs[0].get("params") or {}).get("youtube_publishing") if jobs else None


def retention(chapter_id: str) -> float | None:
    """Best retention reported for a chapter across platforms, or None if silent."""
    rows = (
        db.client()
        .table("chapter_metrics")
        .select("retention_pct,platform,captured_at")
        .eq("chapter_id", chapter_id)
        .not_.is_("retention_pct", "null")
        .order("captured_at", desc=True)
        .execute()
        .data
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.get("platform", "unknown"), float(row["retention_pct"]))
    values = list(latest.values())
    return max(values) if values else None


def plan_story(story_id: str) -> None:
    """Queue chapter one now. Later chapters wait for `tick` to pace them."""
    chapters = (
        db.client()
        .table("story_chapters")
        .select("id,chapter_index")
        .eq("story_id", story_id)
        .eq("status", "ready")
        .order("chapter_index")
        .execute()
        .data
    )
    if chapters and chapters[0]["chapter_index"] == 1:
        queue("chapter_id", chapters[0]["id"], _now())


def plan_clip(clip_id: str) -> None:
    """H1 clips have no chapter ordering, so they go out as soon as they exist."""
    queue("clip_id", clip_id, _now())


def _published_at(chapter_id: str) -> datetime | None:
    rows = (
        db.client()
        .table("publications")
        .select("published_at")
        .eq("chapter_id", chapter_id)
        .eq("status", "published")
        .not_.is_("published_at", "null")
        .order("published_at")
        .limit(1)
        .execute()
        .data
    )
    return _parse(rows[0]["published_at"]) if rows else None


def tick() -> list[str]:
    """Advance pacing for every story with an unscheduled next chapter.

    Returns the chapter ids newly queued.
    """
    client = db.client()
    scheduled = {
        row["chapter_id"]
        for row in client.table("publications").select("chapter_id").execute().data
        if row["chapter_id"]
    }
    chapters = (
        client.table("story_chapters")
        .select("id,story_id,chapter_index")
        .eq("status", "ready")
        .order("story_id")
        .order("chapter_index")
        .execute()
        .data
    )

    by_story: dict[str, list[dict]] = {}
    for chapter in chapters:
        by_story.setdefault(chapter["story_id"], []).append(chapter)

    queued = []
    for story_chapters in by_story.values():
        for previous, nxt in zip(story_chapters, story_chapters[1:]):
            if nxt["id"] in scheduled:
                continue
            if previous["id"] not in scheduled:
                break  # the previous chapter has not even been queued yet

            went_out = _published_at(previous["id"])
            if went_out is None:
                break  # previous chapter is queued but has not gone out yet

            decision = next_chapter(retention(previous["id"]), went_out, _now())
            if decision.action != "schedule":
                break
            queue("chapter_id", nxt["id"], decision.when)
            queued.append(nxt["id"])
            break  # one chapter per story per tick

    return queued


def due(limit: int = 20, *, platform: str | None = None, created_after: str | None = None, youtube_mode: str | None = None, channel_id: str | None = None) -> list[dict]:
    """Publications whose time has come. Phase 5 will hand these to the platforms."""
    query = (
        db.client()
        .table("publications")
        .select("*")
        .eq("status", "scheduled")
        .lte("scheduled_at", _now().isoformat())
    )
    if platform:
        query = query.eq("platform", platform)
    if created_after:
        query = query.gte("created_at", created_after)
    if youtube_mode == "auto":
        query = query.contains("metadata", {"youtube_mode": "auto", "channel_id": channel_id})
    elif youtube_mode == "legacy":
        query = query.not_.contains("metadata", {"youtube_mode": "auto"}).not_.contains("metadata", {"youtube_mode": "review"})
    return query.order("scheduled_at").limit(limit).execute().data

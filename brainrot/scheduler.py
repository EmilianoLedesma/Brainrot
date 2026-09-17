"""Publishing schedule and chapter pacing.

Chapter one of a story goes out immediately. Every chapter after it waits on the
previous chapter's retention, so a story nobody is finishing stops consuming the
feed instead of dumping ten parts into it.

Nothing here uploads anything - it only decides *when* each piece should go out.
The posting itself is Phase 5 and needs the developer apps registered first.
"""

from datetime import datetime, timedelta, timezone

from . import db

PLATFORMS = ("youtube", "tiktok", "instagram")

# Retention of the previous chapter -> how long to wait before the next one.
# A story people finish earns a faster cadence; one they drop gets slowed down.
PACING = (
    (60.0, timedelta(hours=12)),
    (40.0, timedelta(hours=24)),
    (0.0, timedelta(hours=48)),
)
# Below this, publishing further chapters is not worth the slot.
ABANDON_BELOW_PCT = 20.0
# How long to wait for the platforms to report numbers before giving up on
# pacing and falling back to the slowest cadence.
METRICS_GRACE = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


def queue(target: str, target_id: str, when: datetime) -> list[dict]:
    """Schedule one clip or chapter on every platform at `when`."""
    rows = [
        {"platform": platform, target: target_id, "scheduled_at": when.isoformat()}
        for platform in PLATFORMS
    ]
    return db.client().table("publications").insert(rows).execute().data


def retention(chapter_id: str) -> float | None:
    """Best retention reported for a chapter across platforms, or None if silent."""
    rows = (
        db.client()
        .table("chapter_metrics")
        .select("retention_pct")
        .eq("chapter_id", chapter_id)
        .not_.is_("retention_pct", "null")
        .execute()
        .data
    )
    values = [float(r["retention_pct"]) for r in rows]
    return max(values) if values else None


def gap_for(retention_pct: float) -> timedelta:
    for threshold, gap in PACING:
        if retention_pct >= threshold:
            return gap
    return PACING[-1][1]


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

            score = retention(previous["id"])
            if score is None:
                # No numbers yet. Give the platforms a grace period, then pace at
                # the slowest cadence rather than stalling the story forever.
                if _now() - went_out < METRICS_GRACE:
                    break
                gap = PACING[-1][1]
            elif score < ABANDON_BELOW_PCT:
                break  # nobody is watching; stop spending slots on this story
            else:
                gap = gap_for(score)

            queue("chapter_id", nxt["id"], went_out + gap)
            queued.append(nxt["id"])
            break  # one chapter per story per tick

    return queued


def due(limit: int = 20) -> list[dict]:
    """Publications whose time has come. Phase 5 will hand these to the platforms."""
    return (
        db.client()
        .table("publications")
        .select("*")
        .eq("status", "scheduled")
        .lte("scheduled_at", _now().isoformat())
        .order("scheduled_at")
        .limit(limit)
        .execute()
        .data
    )

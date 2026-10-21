"""H2b: scan configured subreddits and turn qualifying posts into jobs.

Reads `reddit_sources_config` for which subreddits to watch and the bar a post has
to clear. A post gets at most one job (jobs.idempotency_key) and one story
(stories.reddit_post_id is unique), so it can never be narrated twice.
"""

import os
import time

import praw

from . import db, pipeline, script

USER_AGENT = os.getenv("REDDIT_USER_AGENT", "brainrot/0.1")
# Posts shorter than this have no story in them; longer than this and the rewrite
# loses too much to be faithful.
MIN_CHARS, MAX_CHARS = 500, 12_000


def client() -> praw.Reddit:
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=USER_AGENT,
    )


def job_key(post_id: str) -> str:
    return f"reddit:{post_id}"


def already_used(post_ids: list[str]) -> set[str]:
    """Posts that already have a story, or a job queued, running or failed for them."""
    if not post_ids:
        return set()
    stories = db.client().table("stories").select("reddit_post_id").in_("reddit_post_id", post_ids).execute().data
    jobs = (
        db.client()
        .table("jobs")
        .select("idempotency_key")
        .in_("idempotency_key", [job_key(p) for p in post_ids])
        .execute()
        .data
    )
    return {r["reddit_post_id"] for r in stories} | {
        r["idempotency_key"].removeprefix("reddit:") for r in jobs
    }


def find_posts(limit_per_sub: int = 25) -> list[dict]:
    """Return posts that clear their subreddit's configured bar and are unused."""
    sources = db.client().table("reddit_sources_config").select("*").eq("enabled", True).execute().data
    if not sources:
        return []

    reddit = client()
    now = time.time()
    candidates = []
    for source in sources:
        subreddit = reddit.subreddit(source["subreddit"])
        for post in subreddit.top(time_filter="week", limit=limit_per_sub):
            age_hours = (now - post.created_utc) / 3600
            if (
                post.stickied
                or post.over_18
                or not post.is_self
                or post.score < source["min_upvotes"]
                or post.num_comments < source["min_comments"]
                or age_hours > source["max_age_hours"]
                or not (MIN_CHARS <= len(post.selftext) <= MAX_CHARS)
            ):
                continue
            candidates.append(
                {
                    "reddit_post_id": post.id,
                    "subreddit": source["subreddit"],
                    "title": post.title,
                    "body": post.selftext,
                    "permalink": f"https://reddit.com{post.permalink}",
                    "upvotes": post.score,
                }
            )

    used = already_used([c["reddit_post_id"] for c in candidates])
    fresh = [c for c in candidates if c["reddit_post_id"] not in used]
    fresh.sort(key=lambda c: c["upvotes"], reverse=True)
    return fresh


def scan(max_jobs: int = 3) -> list[str]:
    """Queue jobs for the best unused posts. Returns the job ids created."""
    # The key makes a second scan of the same post return the existing job.
    return [
        db.create_job("reddit", idempotency_key=job_key(post["reddit_post_id"]), **post)
        for post in find_posts()[:max_jobs]
    ]


def run_reddit(job: dict) -> str:
    """Worker handler: rewrite the post, then render it like any other story."""
    params = job["params"]
    return pipeline.produce(
        job["id"],
        lambda: script.rewrite_post(params["title"], params["body"]),
        reddit_post_id=params["reddit_post_id"],
        subreddit=params["subreddit"],
        permalink=params["permalink"],
        upvotes=params["upvotes"],
    )

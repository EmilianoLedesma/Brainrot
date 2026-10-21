"""HTTP API for the dashboard.

Creates jobs and exposes read-only views of jobs and finished media. A created
job stays `pending` until a worker (python -m brainrot.worker) leases it.

Reads go through here rather than straight from the browser to Supabase: every table
has RLS on with no policies, and opening them to `anon` would expose them to anyone
holding the anon key, which ships in the JS bundle.
"""

import os
import secrets
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, model_validator

from . import db
from .observability.metrics import APIMetricsMiddleware, render
from .observability.logging import safe_text

API_KEY = os.getenv("DASHBOARD_API_KEY", "")
ALLOWED_ORIGINS = os.getenv("DASHBOARD_ORIGINS", "http://localhost:5173").split(",")

app = FastAPI(title="brainrot dashboard")
app.add_middleware(APIMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def require_key(x_api_key: str = Header("")) -> None:
    """Shared-secret gate. With DASHBOARD_API_KEY unset, every request is rejected."""
    if not API_KEY or not secrets.compare_digest(x_api_key.encode("utf-8"), API_KEY.encode("utf-8")):
        raise HTTPException(status_code=401, detail="bad or missing X-API-Key")


@app.get("/metrics", dependencies=[Depends(require_key)], include_in_schema=False)
def metrics() -> Response:
    return Response(render(db.operational_metrics()), media_type="text/plain; version=0.0.4; charset=utf-8")


class JobIn(BaseModel):
    kind: Literal["repurpose", "brainrot"]
    youtube_url: str | None = None
    topic: str | None = None

    @model_validator(mode="after")
    def check_payload(self) -> "JobIn":
        if self.kind == "repurpose" and not self.youtube_url:
            raise ValueError("repurpose needs youtube_url")
        if self.kind == "brainrot" and not self.topic:
            raise ValueError("brainrot needs topic")
        return self


@app.post("/jobs", dependencies=[Depends(require_key)])
def create_job(job: JobIn) -> dict:
    params = {k: v for k, v in job.model_dump(exclude={"kind"}).items() if v is not None}
    return {"id": db.create_job(job.kind, **params)}


@app.get("/jobs", dependencies=[Depends(require_key)])
def list_jobs(limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    return [_job_view(row) for row in db.list_job_executions(limit)]


def _safe_row(row: dict, fields: tuple) -> dict:
    return {key: safe_text(row[key]) if isinstance(row.get(key), str) else row.get(key) for key in fields}


def _error_summary(value) -> str | None:
    return safe_text(str(value).splitlines()[-1])[:500] if value else None


def _job_view(row: dict) -> dict:
    result = _safe_row(row, (
        "id", "kind", "status", "attempts", "max_attempts", "run_after", "error_kind",
        "created_at", "started_at", "finished_at", "duration_seconds",
    ))
    result["params"] = _safe_row(row.get("params") or {}, ("topic", "youtube_url", "title", "subreddit"))
    result["error"] = result["error_summary"] = _error_summary(row.get("error"))
    current = row.get("current_stage")
    result["current_stage"] = _safe_row(current, ("stage", "scope", "started_at")) if current else None
    return result


@app.get("/jobs/{job_id}", dependencies=[Depends(require_key)])
def inspect_job(job_id: UUID) -> dict:
    detail = db.job_execution(str(job_id))
    if detail is None:
        raise HTTPException(status_code=404, detail="job not found")
    stages = []
    for row in detail.get("stages", []):
        stage = _safe_row(row, ("id", "stage", "scope", "attempt", "worker_id", "status", "started_at", "completed_at", "duration_seconds"))
        stage["error"] = _error_summary(row.get("error"))
        stages.append(stage)
    publications = []
    for row in detail.get("publications", []):
        publication = _safe_row(row, ("id", "platform", "status", "scheduled_at", "published_at"))
        publication["error"] = _error_summary(row.get("error"))
        publications.append(publication)
    return {"job": _job_view(detail["job"]), "stages": stages, "publications": publications}


@app.get("/gallery", dependencies=[Depends(require_key)])
def gallery(limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    """Finished H1 clips and H2/H2b chapters, newest first, with playable URLs."""
    sb = db.client()
    clips = (
        sb.table("clips")
        .select("id,title,storage_path,created_at")
        .eq("status", "ready")
        .not_.is_("storage_path", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
    chapters = (
        sb.table("story_chapters")
        .select("id,chapter_index,video_path,created_at,stories(title,topic,subreddit)")
        .eq("status", "ready")
        .not_.is_("video_path", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )

    items = [
        {
            "id": c["id"],
            "source": "clip",
            "title": c.get("title") or "untitled clip",
            "path": c["storage_path"],
            "created_at": c["created_at"],
        }
        for c in clips
    ] + [
        {
            "id": ch["id"],
            "source": "chapter",
            "title": _chapter_title(ch),
            "path": ch["video_path"],
            "created_at": ch["created_at"],
        }
        for ch in chapters
    ]
    items.sort(key=lambda i: i["created_at"], reverse=True)

    # ponytail: one signed-URL round trip per item. Fine for a personal gallery;
    # batch or cache them if the list ever runs long.
    for item in items[:limit]:
        item["url"] = db.signed_url(item["path"])
    return items[:limit]


def _chapter_title(chapter: dict) -> str:
    story = chapter.get("stories") or {}
    name = story.get("title") or story.get("topic") or story.get("subreddit") or "untitled story"
    return f"{name} — ch. {chapter['chapter_index']}"

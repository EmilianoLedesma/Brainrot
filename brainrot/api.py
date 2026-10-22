"""HTTP API for the dashboard.

Creates/deletes jobs and exposes views of jobs and finished media. A created
job stays `pending` until a worker (python -m brainrot.worker) leases it.

Reads go through here rather than straight from the browser to Supabase: every table
has RLS on with no policies, and opening them to `anon` would expose them to anyone
holding the anon key, which ships in the JS bundle.
"""

import os
import logging
import secrets
from datetime import date, timedelta
from typing import Literal
from uuid import UUID
from urllib.parse import parse_qs, urlsplit

import httpx
import requests
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import db, retention, media, research, library, youtube, publish, youtube_metadata, youtube_sync, outputs
from .domain.jobs import PermanentError
from .observability.metrics import APIMetricsMiddleware, render
from .observability.logging import safe_text

API_KEY = os.getenv("DASHBOARD_API_KEY", "")
ALLOWED_ORIGINS = os.getenv("DASHBOARD_ORIGINS", "http://localhost:5173").split(",")

app = FastAPI(title="brainrot dashboard")


class OAuthLogFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5 and "/youtube/callback?" in str(record.args[2]):
            record.args = (*record.args[:2], "/youtube/callback?[redacted]", *record.args[3:])
        return True


logging.getLogger("uvicorn.access").addFilter(OAuthLogFilter())
app.add_middleware(APIMetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "HEAD", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(httpx.TransportError)
async def database_unreachable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database connection interrupted. Retrying shortly."},
                        headers={"Retry-After": "2"})


def require_key(x_api_key: str = Header("")) -> None:
    """Shared-secret gate. With DASHBOARD_API_KEY unset, every request is rejected."""
    if not API_KEY or not secrets.compare_digest(x_api_key.encode("utf-8"), API_KEY.encode("utf-8")):
        raise HTTPException(status_code=401, detail="bad or missing X-API-Key")


@app.exception_handler(requests.RequestException)
async def provider_unavailable(request, exc):
    return JSONResponse(status_code=503, content={"detail": "The external service is unavailable. Check its connection and try again."})


@app.exception_handler(publish.MissingCredentials)
async def provider_not_connected(request, exc):
    return JSONResponse(status_code=409, content={"detail": "Connect this platform before continuing."})


@app.get("/youtube/status", dependencies=[Depends(require_key)])
def youtube_status():
    return youtube.status()


@app.post("/youtube/connect", dependencies=[Depends(require_key)])
def youtube_connect():
    try:
        return youtube.connect()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/youtube/callback", include_in_schema=False)
def youtube_callback(state: str = "", code: str = "", error: str = ""):
    try:
        if error or not state or not code or len(state) > 200 or len(code) > 4096:
            raise ValueError("Connection was not completed.")
        youtube.finish(state, code)
        text = "YouTube connected. Return to Brainrot and refresh the connection status. No videos have been uploaded."
        status_code = 200
    except Exception:
        text = "YouTube connection was not completed. Return to Brainrot, check the setup steps, and connect again."
        status_code = 400
    return HTMLResponse(f"<!doctype html><html><head><title>Brainrot · YouTube</title></head><body><h1>Brainrot</h1><p>{text}</p></body></html>",
                        status_code=status_code, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@app.delete("/youtube/connection", dependencies=[Depends(require_key)])
def youtube_disconnect():
    try:
        youtube.disconnect()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"disconnected": True}


@app.get("/youtube/videos", dependencies=[Depends(require_key)])
def youtube_videos():
    return youtube.videos()


@app.get("/youtube/uploads", dependencies=[Depends(require_key)])
def youtube_uploads():
    return youtube.uploads()


class YouTubeMetadataIn(BaseModel):
    source: Literal["chapter", "clip"]
    target_id: UUID
    regenerate: bool = False


class YouTubeSettingsIn(BaseModel):
    auto_publish: bool
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    include_queued: bool = False


@app.post("/youtube/settings", dependencies=[Depends(require_key)])
def youtube_settings(payload: YouTubeSettingsIn):
    return youtube.settings(**payload.model_dump())


@app.get("/youtube/performance", dependencies=[Depends(require_key)])
def youtube_performance():
    return youtube_sync.performance()


@app.post("/youtube/sync", dependencies=[Depends(require_key)])
def youtube_sync_metrics():
    return youtube_sync.sync()


@app.post("/youtube/metadata", dependencies=[Depends(require_key)])
def youtube_metadata_preview(payload: YouTubeMetadataIn):
    try:
        return youtube_metadata.draft(payload.source, str(payload.target_id), regenerate=payload.regenerate)
    except ValueError:
        raise HTTPException(422, "Upload details could not be generated. Check that this video has saved narration.") from None
    except (PermanentError, TimeoutError):
        raise HTTPException(503, "The writing assistant is unavailable. Check its login or usage limit, or enter upload details yourself.") from None


class YouTubeUploadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["chapter", "clip"]
    target_id: UUID
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    tags: list[str] = Field(default_factory=list, max_length=15)
    made_for_kids: bool = False
    contains_synthetic_media: bool = False

    @model_validator(mode="after")
    def valid_metadata(self):
        self.title = self.title.strip()
        if not self.title or sum(len(tag) + 3 for tag in self.tags) > 450 or any(len(tag) > 100 for tag in self.tags):
            raise ValueError("Use a title and a short list of tags.")
        return self


@app.post("/youtube/upload", dependencies=[Depends(require_key)], status_code=202)
def youtube_upload(payload: YouTubeUploadIn, tasks: BackgroundTasks):
    try:
        row, claimed = youtube.prepare_upload(payload.source, str(payload.target_id), payload.model_dump(exclude={"source", "target_id"}))
        if claimed:
            tasks.add_task(youtube.upload_claimed, row)
        return {"id": row["id"], "status": "uploading" if claimed else row["status"], "url": row.get("url")}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@app.get("/youtube/retention/{video_id}", dependencies=[Depends(require_key)])
def youtube_retention(video_id: str, start: date | None = None, end: date | None = None):
    try:
        return youtube.analytics(video_id, start or date.today() - timedelta(days=28), end or date.today())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


class RetentionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(min_length=1, max_length=250_000)
    axis: Literal["seconds", "percent", "fraction"]
    retention_unit: Literal["percent", "fraction"] = "percent"
    duration_seconds: float = Field(ge=1, le=86_400, allow_inf_nan=False)
    transcript_srt: str = Field(default="", max_length=250_000)
    time_column: int = Field(default=0, ge=0, le=99)
    retention_column: int = Field(default=1, ge=0, le=99)


@app.post("/insights/retention", dependencies=[Depends(require_key)])
def retention_report(payload: RetentionIn) -> dict:
    try:
        return retention.analyze(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/metrics", dependencies=[Depends(require_key)], include_in_schema=False)
def metrics() -> Response:
    return Response(render(db.operational_metrics()), media_type="text/plain; version=0.0.4; charset=utf-8")


class JobYouTubeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["review", "auto", "off"] = "review"
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    made_for_kids: bool = False
    contains_synthetic_media: bool = False


class JobIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["repurpose", "brainrot"]
    youtube_url: str | None = Field(default=None, max_length=2048)
    topic: str | None = Field(default=None, max_length=1000)
    llm_provider: Literal["claude-code", "codex"] | None = None
    brainrot_level: int | None = Field(default=None, ge=0, le=100, strict=True)
    reference_entity: str | None = Field(default=None, pattern=r"^Q[1-9]\d{0,11}$")
    youtube_publishing: JobYouTubeIn | None = None

    @model_validator(mode="after")
    def check_payload(self) -> "JobIn":
        if self.topic is not None:
            self.topic = self.topic.strip()
        if self.youtube_url is not None:
            self.youtube_url = self.youtube_url.strip()
        if self.kind == "repurpose" and not self.youtube_url:
            raise ValueError("repurpose needs youtube_url")
        if self.kind == "brainrot" and not self.topic:
            raise ValueError("brainrot needs topic")
        if self.kind == "repurpose":
            if self.reference_entity is not None:
                raise ValueError("References apply to generated stories only")
            if self.brainrot_level is not None:
                raise ValueError("brainrot_level applies to generated scripts only")
            parsed = urlsplit(self.youtube_url)
            hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
            video_path = (parsed.hostname in {"youtu.be", "www.youtu.be"} and bool(parsed.path.strip("/"))) or (
                parsed.path == "/watch" and bool(parse_qs(parsed.query).get("v"))
            ) or any(parsed.path.startswith(prefix) and parsed.path[len(prefix):] for prefix in ("/shorts/", "/live/", "/embed/"))
            if (parsed.scheme not in {"https", "http"} or parsed.hostname not in hosts
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in {None, 443 if parsed.scheme == "https" else 80} or not video_path):
                raise ValueError("repurpose needs a YouTube video URL")
        return self


@app.post("/jobs", dependencies=[Depends(require_key)])
def create_job(job: JobIn) -> dict:
    params = {k: v for k, v in job.model_dump(exclude={"kind"}).items() if v is not None}
    if job.reference_entity:
        params["reference_context"] = research.context(research.entity(job.reference_entity))
    if job.youtube_publishing:
        status = youtube.status()
        if job.youtube_publishing.mode == "auto" and (not status["connected"] or not status.get("channel_id")):
            raise HTTPException(409, "Connect your YouTube channel before choosing automatic upload.")
        params["youtube_publishing"]["channel_id"] = status.get("channel_id")
    return {"id": db.create_job(job.kind, **params)}


@app.get("/research/search", dependencies=[Depends(require_key)])
def research_search(q: str = Query(min_length=2, max_length=120)):
    return research.search(q)


@app.get("/research/{entity_id}", dependencies=[Depends(require_key)])
def research_entity(entity_id: str):
    try:
        return research.entity(entity_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/library/search", dependencies=[Depends(require_key)])
def library_search(provider: Literal["nasa", "pexels"], q: str = Query(min_length=2, max_length=120)):
    try:
        return library.search(provider, q)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/library", dependencies=[Depends(require_key)])
def library_items(request: Request):
    return [{**item, "url": str(request.base_url).rstrip("/") + media.signed_url(item["storage_path"])} for item in library.items()]


@app.post("/library/{provider}/{asset_id}", dependencies=[Depends(require_key)])
def library_import(provider: str, asset_id: str):
    try:
        return library.import_video(provider, asset_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post("/library/{provider}/{asset_id}/activate", dependencies=[Depends(require_key)])
def library_activate(provider: str, asset_id: str):
    try:
        return library.activate(provider, asset_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "Save this video to the library first.") from None


@app.get("/jobs", dependencies=[Depends(require_key)])
def list_jobs(limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    return [_job_view(row) for row in db.list_job_executions(limit)]


def _safe_row(row: dict, fields: tuple) -> dict:
    return {key: safe_text(row[key]) if isinstance(row.get(key), str)
            else row.get(key) if isinstance(row.get(key), (int, float, bool, type(None))) else None for key in fields}


def _error_summary(value) -> str | None:
    return safe_text(str(value).splitlines()[-1])[:500] if value else None


def _job_view(row: dict) -> dict:
    result = _safe_row(row, (
        "id", "kind", "status", "attempts", "max_attempts", "run_after", "error_kind",
        "created_at", "started_at", "finished_at", "duration_seconds",
    ))
    result["params"] = _safe_row(row.get("params") or {}, ("topic", "youtube_url", "title", "subreddit", "llm_provider", "brainrot_level"))
    publishing = (row.get("params") or {}).get("youtube_publishing")
    if isinstance(publishing, dict):
        result["params"]["youtube_publishing"] = _safe_row(publishing, ("mode", "privacy_status", "made_for_kids", "contains_synthetic_media"))
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


@app.delete("/jobs/{job_id}", dependencies=[Depends(require_key)], status_code=204)
def delete_job(job_id: UUID) -> Response:
    result = db.delete_job(str(job_id))
    if result == "missing":
        raise HTTPException(status_code=404, detail="job not found")
    if result == "uploading":
        raise HTTPException(status_code=409, detail="A video is being published. Wait until the upload finishes before deleting.")
    if result != "deleted":
        raise HTTPException(status_code=503, detail="Could not delete job. Refresh the queue and try again.")
    db.cleanup_media(str(job_id))
    return Response(status_code=204)


@app.get("/jobs/{job_id}/outputs", dependencies=[Depends(require_key)])
def job_outputs(job_id: UUID, request: Request):
    existing = db.client().table("jobs").select("id").eq("id", str(job_id)).execute().data
    if not existing:
        raise HTTPException(404, "Job no longer available.")
    return outputs.for_job(str(job_id), str(request.base_url))


@app.post("/jobs/{job_id}/retry", dependencies=[Depends(require_key)])
def retry_job(job_id: UUID) -> dict:
    result = db.retry_job(str(job_id))
    if result == "missing":
        raise HTTPException(status_code=404, detail="job not found")
    if result == "not_failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
    if result not in {"queued", "already_pending"}:
        raise HTTPException(status_code=503, detail="Could not retry job")
    return {"id": str(job_id), "status": "pending"}


@app.get("/gallery", dependencies=[Depends(require_key)])
def gallery(request: Request, limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    """Finished H1 clips and H2/H2b chapters, newest first, with playable URLs."""
    sb = db.client()
    clips = (
        sb.table("clips")
        .select("id,job_id,title,storage_path,created_at")
        .eq("status", "ready")
        .not_.is_("storage_path", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
    chapters = (
        sb.table("story_chapters")
        .select("id,chapter_index,video_path,created_at,stories(title,topic,subreddit,job_id)")
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
            "job_id": c.get("job_id"),
            "title": c.get("title") or "untitled clip",
            "path": c["storage_path"],
            "created_at": c["created_at"],
        }
        for c in clips
    ] + [
        {
            "id": ch["id"],
            "source": "chapter",
            "job_id": (ch.get("stories") or {}).get("job_id"),
            "title": _chapter_title(ch),
            "path": ch["video_path"],
            "created_at": ch["created_at"],
        }
        for ch in chapters
    ]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    publications = sb.table("publications").select("chapter_id,clip_id,metadata,platform_post_id").eq("platform", "youtube").execute().data
    youtube_settings = {(row.get("clip_id") or row.get("chapter_id")): row.get("metadata") or {} for row in publications}

    # ponytail: one signed-URL round trip per item. Fine for a personal gallery;
    # batch or cache them if the list ever runs long.
    for item in items[:limit]:
        item["youtube_video_id"] = next((row.get("platform_post_id") for row in publications if (row.get("clip_id") or row.get("chapter_id")) == item["id"]), None)
        item["youtube"] = _safe_row(youtube_settings.get(item["id"], {}), ("privacy_status", "made_for_kids", "contains_synthetic_media"))
        item["url"] = db.signed_url(item["path"])
        if item["url"].startswith("/"):
            item["url"] = str(request.base_url).rstrip("/") + item["url"]
    return items[:limit]


@app.api_route("/media/{relative:path}", methods=["GET", "HEAD"], include_in_schema=False)
def local_media(relative: str, expires: int, signature: str):
    if not media.local() or not media.verify(relative, expires, signature):
        raise HTTPException(403, "Media link is invalid or expired.")
    try:
        target = media.path(relative)
        if not target.is_file():
            db.download(relative)
        return FileResponse(target, headers={"Cache-Control": "private, max-age=300"})
    except Exception:
        raise HTTPException(404, "Media file is unavailable on this computer.") from None


def _chapter_title(chapter: dict) -> str:
    story = chapter.get("stories") or {}
    name = story.get("title") or story.get("topic") or story.get("subreddit") or "untitled story"
    return f"{name} — ch. {chapter['chapter_index']}"

"""Supabase access layer.

Every piece of persistent state lives in Supabase: rows in Postgres, media in the
`media` Storage bucket. Nothing on the local disk survives a job.
"""

import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from .domain.pipelines import PipelineContext
from .domain.jobs import LeaseLost
from .observability.logging import event

load_dotenv()

MEDIA_BUCKET = os.getenv("MEDIA_BUCKET", "media")


@lru_cache(maxsize=1)
def client() -> Client:
    """Service-role client. Bypasses RLS, so this key must never reach a browser."""
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
        options=SyncClientOptions(postgrest_client_timeout=8),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(kind: str, idempotency_key: str | None = None, **params) -> str:
    """Enqueue a job. `kind` is one of the job_kind enum values.

    With an idempotency_key, enqueueing the same work twice returns the job that
    already exists instead of creating a second one.
    """
    row = {"kind": kind, "params": params}
    if idempotency_key is None:
        return client().table("jobs").insert(row).execute().data[0]["id"]

    row["idempotency_key"] = idempotency_key
    inserted = (
        client()
        .table("jobs")
        .upsert(row, on_conflict="idempotency_key", ignore_duplicates=True)
        .execute()
        .data
    )
    if inserted:
        return inserted[0]["id"]
    return (
        client().table("jobs").select("id").eq("idempotency_key", idempotency_key)
        .single().execute().data["id"]
    )


def get_job(job_id: str) -> dict:
    return client().table("jobs").select("*").eq("id", job_id).single().execute().data


def assign_story_background(story_id: str) -> str | None:
    """Reserve the next background once; retries reuse the stored assignment."""
    return client().rpc("assign_story_background", {"p_story": str(story_id)}).execute().data


def set_job_status(job_id: str, status: str, error: str | None = None) -> None:
    patch: dict = {"status": status}
    if status == "running":
        patch["started_at"] = _now()
    elif status in ("done", "failed", "cancelled"):
        patch["finished_at"] = _now()
    if error is not None:
        patch["error"] = error
    client().table("jobs").update(patch).eq("id", job_id).execute()


# --- leased execution (migrations/002_job_execution.sql) -------------------------
# Every worker-side state change goes through these. Each one is conditioned in
# SQL on the caller still holding the lease, so a worker whose lease expired and
# was recovered cannot overwrite the new owner's outcome.


def claim_job(worker_id: str, lease_seconds: int = 600) -> dict | None:
    """Lease the oldest claimable job to `worker_id`, or return None."""
    rows = client().rpc(
        "claim_job", {"p_worker": worker_id, "p_lease_seconds": lease_seconds}
    ).execute().data
    return rows[0] if rows else None


def renew_lease(job_id: str, worker_id: str, lease_seconds: int = 600) -> bool:
    return bool(client().rpc(
        "renew_lease", {"p_job": job_id, "p_worker": worker_id, "p_lease_seconds": lease_seconds}
    ).execute().data)


def complete_job(job_id: str, worker_id: str) -> bool:
    return bool(client().rpc(
        "complete_job", {"p_job": job_id, "p_worker": worker_id}
    ).execute().data)


def fail_job(
    job_id: str,
    worker_id: str,
    error: str,
    error_kind: str,
    retry_at: datetime | None = None,
) -> str | None:
    """Record a failed attempt. Returns the new status, or None if the lease was lost."""
    return client().rpc(
        "fail_job",
        {
            "p_job": job_id,
            "p_worker": worker_id,
            "p_error": error,
            "p_error_kind": error_kind,
            "p_retry_at": retry_at.isoformat() if retry_at else None,
        },
    ).execute().data


def recover_expired_jobs() -> list[dict]:
    """Requeue (or fail) jobs whose worker stopped renewing. Returns [{id, status}]."""
    return client().rpc("recover_expired_jobs", {}).execute().data or []


def operational_metrics() -> dict:
    return client().rpc("operational_metrics", {}).execute().data


def list_job_executions(limit: int = 50) -> list[dict]:
    return client().rpc("list_job_executions", {"p_limit": limit}).execute().data or []


def job_execution(job_id: str) -> dict | None:
    return client().rpc("job_execution", {"p_job": str(job_id)}).execute().data


def delete_job(job_id: str) -> str:
    """Remove work atomically and durably enqueue its Storage cleanup."""
    return client().rpc("delete_job", {"p_job": str(job_id)}).execute().data


def cleanup_media(job_id: str | None = None) -> bool:
    """Remove deleted jobs' objects. Failed requests remain queued for the worker."""
    rows = []
    try:
        rows = client().rpc("pending_media_cleanup", {"p_job": job_id}).execute().data or []
        paths = [row["storage_path"] for row in rows if not row["is_referenced"]]
        if paths:
            client().storage.from_(MEDIA_BUCKET).remove(paths)
        if rows:
            client().rpc("finish_media_cleanup", {
                "p_ids": [row["id"] for row in rows], "p_success": True,
            }).execute()
        return True
    except Exception as exc:
        event("media_cleanup_deferred", error_type=type(exc).__name__)
        if rows:
            try:
                client().rpc("finish_media_cleanup", {
                    "p_ids": [row["id"] for row in rows], "p_success": False,
                }).execute()
            except Exception:
                pass  # The durable rows already exist and remain eligible.
        return False


def retry_job(job_id: str) -> str:
    """Requeue failed work without discarding saved results or attempt history."""
    return client().rpc("retry_job", {"p_job": str(job_id)}).execute().data


# --- stage execution (migrations/003_stage_execution.sql) ------------------------


def start_stage(context: PipelineContext, stage: str, scope: str = "") -> str | None:
    return client().rpc("start_stage", {
        "p_job": context.job_id, "p_worker": context.worker_id,
        "p_attempt": context.attempt, "p_stage": stage, "p_scope": scope,
    }).execute().data


def finish_stage(execution_id: str, worker_id: str, status: str, error: str | None = None) -> bool:
    if status not in ("done", "failed"):
        raise ValueError(f"invalid stage outcome: {status}")
    return bool(client().rpc("finish_stage", {
        "p_execution": execution_id, "p_worker": worker_id,
        "p_status": status, "p_error": error,
    }).execute().data)


def upload(path: str, data: bytes, content_type: str) -> str:
    """Put bytes in the media bucket at `path` and return that path."""
    client().storage.from_(MEDIA_BUCKET).upload(
        path, data, {"content-type": content_type, "upsert": "true"}
    )
    return path


def upload_job_media(job_id: str, table: str, asset_id: str, path: str, data: bytes, content_type: str) -> str:
    """Fence Storage uploads against deletion of their owning chapter or clip."""
    if table not in {"story_chapters", "clips", "source_videos"}:
        raise ValueError("invalid job media owner")

    def owner_exists():
        return bool(client().table(table).select("id").eq("id", asset_id).execute().data)

    if not owner_exists():
        raise LeaseLost("media owner was deleted")
    uploaded = upload(path, data, content_type)
    if not owner_exists():
        # The delete transaction captured this destination already. Re-enqueue
        # as well so even a cleanup that ran during this HTTP upload is repeated.
        client().rpc("queue_media_cleanup", {"p_job": job_id, "p_paths": [path]}).execute()
        cleanup_media(job_id)
        raise LeaseLost("media owner was deleted during upload")
    return uploaded


def download(path: str) -> bytes:
    return client().storage.from_(MEDIA_BUCKET).download(path)


def signed_url(path: str, expires_in: int = 3600) -> str:
    res = client().storage.from_(MEDIA_BUCKET).create_signed_url(path, expires_in)
    return res["signedURL"]

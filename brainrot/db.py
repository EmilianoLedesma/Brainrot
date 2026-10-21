"""Supabase access layer.

Every piece of persistent state lives in Supabase: rows in Postgres, media in the
`media` Storage bucket. Nothing on the local disk survives a job.
"""

import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

from .domain.pipelines import PipelineContext

load_dotenv()

MEDIA_BUCKET = os.getenv("MEDIA_BUCKET", "media")


@lru_cache(maxsize=1)
def client() -> Client:
    """Service-role client. Bypasses RLS, so this key must never reach a browser."""
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
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


def download(path: str) -> bytes:
    return client().storage.from_(MEDIA_BUCKET).download(path)


def signed_url(path: str, expires_in: int = 3600) -> str:
    res = client().storage.from_(MEDIA_BUCKET).create_signed_url(path, expires_in)
    return res["signedURL"]

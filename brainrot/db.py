"""Supabase access layer.

Every piece of persistent state lives in Supabase: rows in Postgres, media in the
`media` Storage bucket. Nothing on the local disk survives a job.
"""

import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

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


def create_job(kind: str, **params) -> str:
    """Enqueue a job. `kind` is one of the job_kind enum values."""
    rows = client().table("jobs").insert({"kind": kind, "params": params}).execute().data
    return rows[0]["id"]


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


def upload(path: str, data: bytes, content_type: str) -> str:
    """Put bytes in the media bucket at `path` and return that path."""
    client().storage.from_(MEDIA_BUCKET).upload(
        path, data, {"content-type": content_type, "upsert": "true"}
    )
    return path


def signed_url(path: str, expires_in: int = 3600) -> str:
    res = client().storage.from_(MEDIA_BUCKET).create_signed_url(path, expires_in)
    return res["signedURL"]

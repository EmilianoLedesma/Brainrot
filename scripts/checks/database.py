"""Phase 0 smoke check: round-trip a job row and a media file through Supabase.

Needs a real project (SUPABASE_URL + SUPABASE_SERVICE_KEY in .env) and
all migrations applied. Run with `python -m scripts.checks.database`.
Creates and deletes its own delayed job and media object; leaves compact
operational observations of that job in the metrics journal.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

from brainrot import db


def main() -> None:
    assert os.getenv("SUPABASE_URL"), "SUPABASE_URL missing; copy .env.example to .env"

    # A future run_after prevents real workers from taking this smoke job.
    owner = "smoke:" + uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=1)).isoformat()
    job_id = db.client().table("jobs").insert({
        "kind": "brainrot", "params": {"topic": "smoke test"},
        "run_after": future, "idempotency_key": owner,
    }).execute().data[0]["id"]
    path = f"smoke/{job_id}.txt"
    try:
        assert db.get_job(job_id)["status"] == "pending"
        db.client().table("jobs").update({
            "status": "running", "started_at": now.isoformat(), "attempts": 1,
            "lease_owner": owner, "lease_expires_at": future,
        }).eq("id", job_id).eq("status", "pending").execute()
        assert db.renew_lease(job_id, owner, 600)
        assert db.complete_job(job_id, owner)
        assert db.get_job(job_id)["status"] == "done"
        db.upload(path, b"hello", "text/plain")
        assert db.download(path) == b"hello"
        assert db.signed_url(path).startswith("http")
        assert db.job_execution(job_id)["job"]["status"] == "done"
    finally:
        try:
            db.client().storage.from_(db.MEDIA_BUCKET).remove([path])
        finally:
            db.client().table("jobs").delete().eq("id", job_id).execute()
    assert not db.client().table("jobs").select("id").eq("id", job_id).execute().data

    print("phase 0 ok")


if __name__ == "__main__":
    main()

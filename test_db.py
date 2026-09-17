"""Phase 0 smoke check: round-trip a job row and a media file through Supabase.

Needs a real project (SUPABASE_URL + SUPABASE_SERVICE_KEY in .env) and the
001_init.sql migration applied. Run with `python test_db.py`.
"""

import os

from brainrot import db


def main() -> None:
    assert os.getenv("SUPABASE_URL"), "SUPABASE_URL missing; copy .env.example to .env"

    job_id = db.create_job("brainrot", topic="smoke test")
    assert db.get_job(job_id)["status"] == "pending"

    db.set_job_status(job_id, "running")
    job = db.get_job(job_id)
    assert job["status"] == "running", job
    assert job["started_at"], "started_at should be stamped on running"

    db.set_job_status(job_id, "done")
    job = db.get_job(job_id)
    assert job["status"] == "done", job
    assert job["finished_at"], "finished_at should be stamped on done"

    path = db.upload(f"smoke/{job_id}.txt", b"hello", "text/plain")
    assert db.signed_url(path).startswith("http")

    db.client().table("jobs").delete().eq("id", job_id).execute()
    db.client().storage.from_(db.MEDIA_BUCKET).remove([path])
    assert not db.client().table("jobs").select("id").eq("id", job_id).execute().data

    print("phase 0 ok")


if __name__ == "__main__":
    main()

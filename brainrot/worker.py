"""Job worker. Claims pending jobs and runs the matching pipeline.

Run it with: python -m brainrot.worker
"""

import time
import traceback

from . import db, pipeline, publish, reddit, repurpose, scheduler

HANDLERS = {
    "brainrot": pipeline.run_brainrot,
    "reddit": reddit.run_reddit,
    "repurpose": repurpose.run_repurpose,
}

POLL_SECONDS = 5


def claim() -> dict | None:
    """Take the oldest pending job, or None.

    The update is conditioned on the row still being `pending`, so two workers
    racing for the same job leave exactly one winner.
    """
    pending = (
        db.client()
        .table("jobs")
        .select("*")
        .eq("status", "pending")
        .order("created_at")
        .limit(1)
        .execute()
        .data
    )
    if not pending:
        return None
    job = pending[0]
    won = (
        db.client()
        .table("jobs")
        .update({"status": "running", "started_at": db._now()})
        .eq("id", job["id"])
        .eq("status", "pending")
        .execute()
        .data
    )
    return job if won else None


def run(job: dict) -> None:
    handler = HANDLERS.get(job["kind"])
    if handler is None:
        db.set_job_status(job["id"], "failed", f"no handler for kind {job['kind']}")
        return
    try:
        handler(job)
        db.set_job_status(job["id"], "done")
    except Exception:
        # The traceback is the only record of why a job died, so it goes on the row.
        db.set_job_status(job["id"], "failed", traceback.format_exc(limit=5))
        raise


def run_once() -> bool:
    """Run one job if any is waiting. Returns whether it found work."""
    job = claim()
    if job is None:
        return False
    print(f"running {job['kind']} job {job['id']}")
    try:
        run(job)
        print("  done")
    except Exception as exc:
        print(f"  failed: {exc}")
    return True


def main() -> None:
    print("worker started")
    while True:
        if not run_once():
            # Quiet moment: advance chapter pacing before going back to sleep.
            for chapter_id in scheduler.tick():
                print(f"scheduled chapter {chapter_id}")
            publish.run_due()
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

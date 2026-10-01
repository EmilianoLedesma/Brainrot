"""Job worker. Leases pending jobs and runs the matching pipeline.

Run it with: python -m brainrot.worker

Each iteration first returns abandoned jobs (expired leases) to the queue, then
claims one. While a job runs, a background thread keeps renewing its lease; if
the worker dies, the lease lapses and any worker recovers the job. A failure is
retried with bounded backoff when it looks transient, and ends the job when it
does not. Every outcome is recorded only if this worker still holds the lease.
"""

import os
import socket
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone

from . import db, pipeline, publish, reddit, repurpose, scheduler
from .application import retry

HANDLERS = {
    "brainrot": pipeline.run_brainrot,
    "reddit": reddit.run_reddit,
    "repurpose": repurpose.run_repurpose,
}

POLL_SECONDS = 5
# Long enough that a renewal missed to a network blip does not lose the job,
# short enough that a dead worker's job is picked up again within minutes.
LEASE_SECONDS = 600
RENEW_EVERY_SECONDS = 60
# Pacing and publishing also run between jobs when the queue never empties.
HOUSEKEEPING_EVERY_SECONDS = 300

POLICY = retry.DEFAULT_POLICY
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"


class LeaseKeeper(threading.Thread):
    """Renews a job's lease until stopped. Notes it if the lease was lost."""

    def __init__(self, job_id: str, worker_id: str, lease_seconds: int, every: float):
        super().__init__(daemon=True, name=f"lease-{job_id}")
        self.job_id, self.worker_id = job_id, worker_id
        self.lease_seconds, self.every = lease_seconds, every
        self.lost = False
        self._halt = threading.Event()

    def run(self) -> None:
        while not self._halt.wait(self.every):
            try:
                if not db.renew_lease(self.job_id, self.worker_id, self.lease_seconds):
                    self.lost = True
                    return
            except Exception as exc:
                # One failed renewal is not fatal; the lease has slack for it.
                print(f"  lease renewal failed: {exc}")

    def stop(self) -> None:
        self._halt.set()
        self.join()


def execute(
    job: dict,
    worker_id: str = WORKER_ID,
    lease_seconds: int = LEASE_SECONDS,
    renew_every: float = RENEW_EVERY_SECONDS,
) -> str:
    """Run a claimed job and record its outcome. Returns the job's new status,
    or "lease_lost" if another worker owns it by now."""
    handler = HANDLERS.get(job["kind"])
    if handler is None:
        status = db.fail_job(job["id"], worker_id, f"no handler for kind {job['kind']}", "permanent")
        return status or "lease_lost"

    keeper = LeaseKeeper(job["id"], worker_id, lease_seconds, renew_every)
    keeper.start()
    try:
        handler(job)
    except Exception as exc:
        keeper.stop()
        decision = retry.decide(
            exc, job["attempts"], job["max_attempts"], datetime.now(timezone.utc), POLICY
        )
        # The traceback is the only record of why an attempt died, so it goes on the row.
        status = db.fail_job(
            job["id"], worker_id, traceback.format_exc(limit=5), decision.kind, decision.retry_at
        )
        return status or "lease_lost"

    keeper.stop()
    return "done" if db.complete_job(job["id"], worker_id) else "lease_lost"


def run_once(
    worker_id: str = WORKER_ID,
    lease_seconds: int = LEASE_SECONDS,
    renew_every: float = RENEW_EVERY_SECONDS,
) -> bool:
    """Recover abandoned jobs, then run one job if any is waiting.
    Returns whether it found work."""
    for row in db.recover_expired_jobs():
        print(f"recovered job {row['id']} -> {row['status']}")

    job = db.claim_job(worker_id, lease_seconds)
    if job is None:
        return False
    print(f"running {job['kind']} job {job['id']} (attempt {job['attempts']}/{job['max_attempts']})")
    status = execute(job, worker_id, lease_seconds, renew_every)
    print(f"  {status}")
    return True


def housekeeping() -> None:
    """Advance chapter pacing and upload whatever is due."""
    for chapter_id in scheduler.tick():
        print(f"scheduled chapter {chapter_id}")
    publish.run_due()


def main() -> None:
    print(f"worker {WORKER_ID} started")
    last_housekeeping = 0.0
    while True:
        found = run_once()
        if not found or time.monotonic() - last_housekeeping > HOUSEKEEPING_EVERY_SECONDS:
            housekeeping()
            last_housekeeping = time.monotonic()
        if not found:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

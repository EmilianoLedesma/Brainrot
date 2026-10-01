"""The worker loop against a real database: claim, run, retry, recover."""

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from brainrot import db, worker
from brainrot.application.retry import RetryPolicy
from brainrot.domain.jobs import PermanentError
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job, job


@pytest.fixture
def run(pg, monkeypatch):
    """Run one worker iteration with the given brainrot handler."""
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    monkeypatch.setattr(worker, "POLICY", RetryPolicy(base=timedelta(seconds=30)))

    def go(handler, worker_id="worker-a", **kwargs):
        monkeypatch.setitem(worker.HANDLERS, "brainrot", handler)
        return worker.run_once(worker_id=worker_id, **kwargs)

    return go


def ok(job):
    return "story-1"


def test_a_successful_run_completes_the_job(pg, run):
    job_id = add_job(pg)
    assert run(ok) is True
    row = job(pg, job_id)
    assert row["status"] == "done" and row["attempts"] == 1 and row["lease_owner"] is None


def test_no_work_returns_false(pg, run):
    assert run(ok) is False


def test_a_transient_failure_is_scheduled_for_retry(pg, run):
    job_id = add_job(pg)

    def flaky(job):
        raise TimeoutError("render stalled")

    before = datetime.now(timezone.utc)
    run(flaky)

    row = job(pg, job_id)
    assert row["status"] == "pending"
    assert row["error_kind"] == "transient"
    assert "render stalled" in row["error"]
    assert row["run_after"] >= before + timedelta(seconds=29)
    # Not claimable until the backoff passes.
    assert run(ok) is False


def test_a_retried_job_completes_on_its_next_attempt(pg, run):
    job_id = add_job(pg)
    run(lambda job: (_ for _ in ()).throw(TimeoutError()))
    pg.execute("update jobs set run_after = now() where id = %s", (job_id,))  # skip the wait

    seen = []
    run(lambda job: seen.append(job["attempts"]))

    assert seen == [2]
    assert job(pg, job_id)["status"] == "done"


def test_a_permanent_failure_is_terminal(pg, run):
    job_id = add_job(pg)

    def broken(job):
        raise PermanentError("no active background_clips")

    run(broken)
    row = job(pg, job_id)
    assert row["status"] == "failed" and row["error_kind"] == "permanent"
    assert row["finished_at"] is not None


def test_the_last_attempt_fails_for_good(pg, run):
    job_id = add_job(pg, attempts=2, max_attempts=3)
    run(lambda job: (_ for _ in ()).throw(TimeoutError()))
    assert job(pg, job_id)["status"] == "failed"


def test_an_unknown_kind_fails_permanently(pg, run, monkeypatch):
    job_id = add_job(pg, kind="reddit")
    monkeypatch.delitem(worker.HANDLERS, "reddit")
    run(ok)
    row = job(pg, job_id)
    assert row["status"] == "failed" and "no handler" in row["error"]


def test_the_worker_recovers_an_abandoned_job_before_claiming(pg, run):
    job_id = add_job(pg)
    db.claim_job("crashed-worker", lease_seconds=0)

    assert run(ok, worker_id="worker-b") is True

    row = job(pg, job_id)
    assert row["status"] == "done" and row["attempts"] == 2


def test_a_job_with_a_live_lease_is_left_alone(pg, run):
    job_id = add_job(pg)
    db.claim_job("busy-worker", lease_seconds=600)
    assert run(ok, worker_id="worker-b") is False
    assert job(pg, job_id)["lease_owner"] == "busy-worker"


def test_the_lease_is_renewed_while_a_long_job_runs(pg, run):
    job_id = add_job(pg)
    expiries = []

    def slow(job):
        for _ in range(3):
            time.sleep(0.4)
            expiries.append(pg.execute("select lease_expires_at from jobs where id = %s", (job_id,)).fetchone()["lease_expires_at"])

    run(slow, lease_seconds=5, renew_every=0.2)

    assert expiries[-1] > expiries[0], "the lease moved forward during the run"
    assert job(pg, job_id)["status"] == "done"


def test_a_worker_whose_lease_was_taken_does_not_record_the_outcome(pg, run):
    job_id = add_job(pg)
    taken = threading.Event()

    def outlived(job):
        # Another worker recovers and claims the job while this one is still busy.
        pg.execute("update jobs set lease_expires_at = now() - interval '1 second' where id = %s", (job_id,))
        db.recover_expired_jobs()
        db.claim_job("worker-b", lease_seconds=600)
        taken.set()

    run(outlived, worker_id="worker-a", renew_every=60)

    assert taken.is_set()
    row = job(pg, job_id)
    assert row["status"] == "running" and row["lease_owner"] == "worker-b"

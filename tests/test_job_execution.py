"""Claims, leases, retries and idempotency, against a real Postgres.

These run the SQL in migrations/002_job_execution.sql directly, plus the
brainrot.db wrappers that call it through rpc().
"""

from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from brainrot import db
from tests.pgclient import PgRpcClient


def add_job(pg, kind="brainrot", **columns) -> str:
    columns = {"kind": kind, **columns}
    names = ", ".join(columns)
    values = ", ".join(f"%({k})s" for k in columns)
    return str(pg.execute(f"insert into jobs ({names}) values ({values}) returning id", columns).fetchone()["id"])


def job(pg, job_id) -> dict:
    return pg.execute("select * from jobs where id = %s", (job_id,)).fetchone()


@pytest.fixture
def repo(pg, monkeypatch):
    """brainrot.db with its client pointed at the test database."""
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    return db


# --- claim ----------------------------------------------------------------------

def test_claim_takes_the_oldest_pending_job_and_leases_it(pg, repo):
    first = add_job(pg, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    add_job(pg, created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))

    claimed = repo.claim_job("worker-a", lease_seconds=60)

    assert claimed["id"] == first
    row = job(pg, first)
    assert row["status"] == "running"
    assert row["attempts"] == 1
    assert row["lease_owner"] == "worker-a"
    assert row["lease_expires_at"] > datetime.now(timezone.utc) + timedelta(seconds=30)
    assert row["started_at"] is not None


def test_claim_returns_none_when_nothing_is_waiting(pg, repo):
    assert repo.claim_job("worker-a") is None


def test_claim_skips_a_job_whose_retry_time_has_not_come(pg, repo):
    add_job(pg, run_after=datetime.now(timezone.utc) + timedelta(hours=1))
    assert repo.claim_job("worker-a") is None


def test_a_second_worker_cannot_claim_a_leased_job(pg, repo):
    add_job(pg)
    assert repo.claim_job("worker-a") is not None
    assert repo.claim_job("worker-b") is None


def test_concurrent_claims_do_not_block_or_share_a_job(pg):
    # Worker A holds its claim in an open transaction; B must skip that row
    # rather than wait for it or take it too.
    only = add_job(pg)
    with psycopg.connect(pg.info.dsn) as a, psycopg.connect(pg.info.dsn, autocommit=True) as b:
        a.execute("set lock_timeout = '2s'")
        b.execute("set lock_timeout = '2s'")
        got_a = a.execute("select id from claim_job('worker-a', 60)").fetchall()
        got_b = b.execute("select id from claim_job('worker-b', 60)").fetchall()
        a.commit()
    assert [str(r[0]) for r in got_a] == [only]
    assert got_b == []


def test_attempts_count_every_claim(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a")
    repo.fail_job(job_id, "worker-a", "flaky", "transient", retry_at=datetime.now(timezone.utc))
    repo.claim_job("worker-b")
    assert job(pg, job_id)["attempts"] == 2


# --- lease ownership --------------------------------------------------------------

def test_only_the_owner_renews_the_lease(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a", lease_seconds=10)
    before = job(pg, job_id)["lease_expires_at"]

    assert repo.renew_lease(job_id, "worker-b", lease_seconds=600) is False
    assert repo.renew_lease(job_id, "worker-a", lease_seconds=600) is True
    assert job(pg, job_id)["lease_expires_at"] > before


def test_complete_requires_the_lease(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a")

    assert repo.complete_job(job_id, "worker-b") is False
    assert job(pg, job_id)["status"] == "running"

    assert repo.complete_job(job_id, "worker-a") is True
    row = job(pg, job_id)
    assert row["status"] == "done"
    assert row["finished_at"] is not None
    assert row["lease_owner"] is None and row["lease_expires_at"] is None


# --- failure and retry ---------------------------------------------------------------

def test_failure_with_retry_time_goes_back_to_pending(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a")
    retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    assert repo.fail_job(job_id, "worker-a", "timeout", "transient", retry_at=retry_at) == "pending"

    row = job(pg, job_id)
    assert row["status"] == "pending"
    assert abs(row["run_after"] - retry_at) < timedelta(seconds=1)
    assert row["error"] == "timeout" and row["error_kind"] == "transient"
    assert row["lease_owner"] is None and row["finished_at"] is None


def test_failure_without_retry_time_is_terminal(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a")

    assert repo.fail_job(job_id, "worker-a", "bad input", "permanent") == "failed"

    row = job(pg, job_id)
    assert row["status"] == "failed" and row["finished_at"] is not None
    assert repo.claim_job("worker-a") is None


def test_a_worker_that_lost_its_lease_cannot_record_failure(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a")
    assert repo.fail_job(job_id, "worker-b", "x", "permanent") is None
    assert job(pg, job_id)["status"] == "running"


# --- recovery -------------------------------------------------------------------------

def test_an_expired_lease_is_recovered_to_pending(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a", lease_seconds=0)

    recovered = repo.recover_expired_jobs()

    assert recovered == [{"id": job_id, "status": "pending"}]
    row = job(pg, job_id)
    assert row["status"] == "pending" and row["error_kind"] == "lease_expired"
    assert "worker-a" in row["error"]
    # The job is claimable again, by anyone.
    assert repo.claim_job("worker-b")["id"] == job_id


def test_an_active_lease_is_not_recovered(pg, repo):
    add_job(pg)
    repo.claim_job("worker-a", lease_seconds=600)
    assert repo.recover_expired_jobs() == []


def test_recovery_fails_a_job_that_used_up_its_attempts(pg, repo):
    job_id = add_job(pg, max_attempts=1)
    repo.claim_job("worker-a", lease_seconds=0)
    assert repo.recover_expired_jobs() == [{"id": job_id, "status": "failed"}]


def test_the_previous_owner_cannot_complete_after_recovery(pg, repo):
    job_id = add_job(pg)
    repo.claim_job("worker-a", lease_seconds=0)
    repo.recover_expired_jobs()
    repo.claim_job("worker-b")

    assert repo.complete_job(job_id, "worker-a") is False
    assert job(pg, job_id)["lease_owner"] == "worker-b"


def test_running_jobs_from_before_leases_existed_are_recovered(pg, repo):
    # A row left `running` by the old worker has no lease at all.
    job_id = add_job(pg, status="running", attempts=1)
    assert repo.recover_expired_jobs() == [{"id": job_id, "status": "pending"}]


# --- idempotency and uniqueness ---------------------------------------------------------

def test_idempotency_keys_are_unique(pg):
    add_job(pg, idempotency_key="reddit:abc")
    with pytest.raises(psycopg.errors.UniqueViolation):
        add_job(pg, idempotency_key="reddit:abc")
    # Jobs without a key are unconstrained.
    add_job(pg)
    add_job(pg)


def test_one_story_and_one_source_video_per_job(pg):
    job_id = add_job(pg)
    pg.execute("insert into stories (job_id) values (%s)", (job_id,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        pg.execute("insert into stories (job_id) values (%s)", (job_id,))

    pg.execute("insert into source_videos (job_id, youtube_url) values (%s, 'u')", (job_id,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        pg.execute("insert into source_videos (job_id, youtube_url) values (%s, 'u')", (job_id,))


def test_one_publication_per_target_and_platform(pg):
    job_id = add_job(pg)
    story = pg.execute("insert into stories (job_id) values (%s) returning id", (job_id,)).fetchone()["id"]
    chapter = pg.execute(
        "insert into story_chapters (story_id, chapter_index, text) values (%s, 1, 't') returning id",
        (story,),
    ).fetchone()["id"]
    pg.execute("insert into publications (platform, chapter_id) values ('youtube', %s)", (chapter,))
    pg.execute("insert into publications (platform, chapter_id) values ('tiktok', %s)", (chapter,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        pg.execute("insert into publications (platform, chapter_id) values ('youtube', %s)", (chapter,))


@pytest.mark.parametrize("fn", ["claim_job", "renew_lease", "complete_job", "fail_job", "recover_expired_jobs"])
def test_browser_roles_cannot_call_the_job_functions(pg, fn):
    for role in ("anon", "authenticated"):
        allowed = pg.execute(
            "select bool_or(has_function_privilege(%s, p.oid, 'execute')) as ok "
            "from pg_proc p where p.proname = %s",
            (role, fn),
        ).fetchone()["ok"]
        assert allowed is False, f"{role} can execute {fn}"


# --- create_job ----------------------------------------------------------------------------

def test_create_job_with_a_key_returns_the_existing_job(fake_db):
    first = db.create_job("reddit", idempotency_key="reddit:abc", title="t")
    second = db.create_job("reddit", idempotency_key="reddit:abc", title="t")
    assert first == second
    assert len(fake_db.rows("jobs")) == 1

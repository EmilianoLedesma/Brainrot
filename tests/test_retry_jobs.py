import psycopg
import pytest

from brainrot import db
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job, job


def test_manual_retry_keeps_saved_progress_and_monotonic_attempts(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg, status="failed", attempts=3, max_attempts=3, error="render failed", error_kind="permanent")
    story = pg.execute("insert into stories(job_id,script) values(%s,'Saved script') returning id", (job_id,)).fetchone()["id"]
    chapter = pg.execute("insert into story_chapters(story_id,chapter_index,text,status,video_path) values(%s,1,'Saved chapter','ready','saved.mp4') returning id", (story,)).fetchone()["id"]
    pg.execute("insert into publications(chapter_id,platform) values(%s,'youtube')", (chapter,))
    pg.execute("insert into stage_executions(job_id,stage,attempt,worker_id,status,completed_at) values(%s,'script',3,'old-worker','done',clock_timestamp())", (job_id,))

    assert db.retry_job(job_id) == "queued"
    row = job(pg, job_id)
    assert row["status"] == "pending" and row["attempts"] == 3 and row["max_attempts"] == 6
    assert row["error"] is None and row["error_kind"] is None
    assert row["finished_at"] is None and row["lease_owner"] is None
    assert db.retry_job(job_id) == "already_pending"
    assert job(pg, job_id)["max_attempts"] == 6
    assert pg.execute("select script from stories where job_id=%s", (job_id,)).fetchone()["script"] == "Saved script"
    assert pg.execute("select video_path from story_chapters where id=%s", (chapter,)).fetchone()["video_path"] == "saved.mp4"
    assert pg.execute("select count(*) from publications").fetchone()["count"] == 1
    assert pg.execute("select attempt from stage_executions").fetchone()["attempt"] == 3
    claimed = db.claim_job("new-worker")
    assert claimed["id"] == job_id and claimed["attempts"] == 4
    assert db.complete_job(job_id, "old-worker") is False


@pytest.mark.parametrize("status", ["running", "done", "cancelled"])
def test_retry_cannot_restart_active_or_successful_jobs(pg, status):
    job_id = add_job(pg, status=status)
    assert pg.execute("select retry_job(%s)", (job_id,)).fetchone()["retry_job"] == "not_failed"
    assert job(pg, job_id)["status"] == status


def test_retry_missing_job(pg):
    assert pg.execute("select retry_job('00000000-0000-0000-0000-000000000001')").fetchone()["retry_job"] == "missing"


def test_concurrent_retries_only_grant_one_retry_budget(pg):
    job_id = add_job(pg, status="failed", attempts=3)
    with psycopg.connect(pg.info.dsn) as first, psycopg.connect(pg.info.dsn, autocommit=True) as second:
        assert first.execute("select retry_job(%s)", (job_id,)).fetchone()[0] == "queued"
        second.execute("set lock_timeout='100ms'")
        with pytest.raises(psycopg.errors.LockNotAvailable):
            second.execute("select retry_job(%s)", (job_id,))
        first.commit()
        assert second.execute("select retry_job(%s)", (job_id,)).fetchone()[0] == "already_pending"
    assert job(pg, job_id)["max_attempts"] == 6


def test_claim_skips_retry_until_it_commits(pg):
    job_id = add_job(pg, status="failed")
    with psycopg.connect(pg.info.dsn) as retrying, psycopg.connect(pg.info.dsn, autocommit=True) as claiming:
        retrying.execute("select retry_job(%s)", (job_id,))
        assert claiming.execute("select * from claim_job('worker',600)").fetchall() == []
    assert str(pg.execute("select id from claim_job('worker',600)").fetchone()["id"]) == job_id


def test_retry_rpc_is_service_only(pg):
    for role in ("anon", "authenticated"):
        assert not pg.execute("select has_function_privilege(%s,'retry_job(uuid)','execute')", (role,)).fetchone()["has_function_privilege"]

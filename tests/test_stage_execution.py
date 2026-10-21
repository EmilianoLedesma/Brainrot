from datetime import datetime, timezone

import pytest

from brainrot import db
from brainrot.application import stages
from brainrot.domain.jobs import LeaseLost
from brainrot.domain.pipelines import PipelineContext
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


@pytest.fixture
def context(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg)
    claimed = db.claim_job("worker-a")
    return PipelineContext(job_id, "brainrot", {}, claimed["attempts"], "worker-a")


def records(pg):
    return pg.execute("select * from stage_executions order by started_at, id").fetchall()


def test_stage_is_visible_while_running(pg, context):
    with stages.tracking(context), stages.stage("render", scope="chapter:1"):
        row = records(pg)[0]
        assert str(row["job_id"]) == context.job_id
        assert (row["stage"], row["scope"], row["status"]) == ("render", "chapter:1", "running")
        assert (row["attempt"], row["worker_id"]) == (1, "worker-a")
        assert row["started_at"] is not None
        assert row["completed_at"] is None and row["duration_seconds"] is None


def test_success_records_completion_and_database_duration(pg, context):
    with stages.tracking(context), stages.stage("tts"):
        pg.execute("update stage_executions set started_at = clock_timestamp() - interval '2 seconds'")
    row = records(pg)[0]
    assert row["status"] == "done" and row["error"] is None
    assert row["completed_at"] >= row["started_at"]
    assert row["duration_seconds"] >= 2


def test_failure_records_the_error_and_reraises_it(pg, context):
    with pytest.raises(TimeoutError, match="provider stalled"):
        with stages.tracking(context), stages.stage("render"):
            raise TimeoutError("provider stalled")
    row = records(pg)[0]
    assert row["status"] == "failed"
    assert "TimeoutError: provider stalled" in row["error"]
    assert row["completed_at"] is not None and row["duration_seconds"] >= 0


def test_retry_keeps_both_stage_attempts(pg, context):
    with pytest.raises(TimeoutError):
        with stages.tracking(context), stages.stage("render"):
            raise TimeoutError("temporary")
    db.fail_job(context.job_id, "worker-a", "temporary", "transient", datetime.now(timezone.utc))
    claimed = db.claim_job("worker-b")
    retried = PipelineContext(context.job_id, "brainrot", {}, claimed["attempts"], "worker-b")
    with stages.tracking(retried), stages.stage("render"):
        pass
    assert [(r["attempt"], r["worker_id"], r["status"]) for r in records(pg)] == [
        (1, "worker-a", "failed"), (2, "worker-b", "done"),
    ]


def test_each_chapter_has_a_separate_execution(pg, context):
    with stages.tracking(context):
        for chapter in ("chapter:1", "chapter:2"):
            with stages.stage("render", scope=chapter):
                pass
    assert [r["scope"] for r in records(pg)] == ["chapter:1", "chapter:2"]


def test_a_worker_without_the_lease_cannot_start_a_stage(pg, context):
    other = PipelineContext(context.job_id, "brainrot", {}, 1, "other-worker")
    with pytest.raises(LeaseLost):
        with stages.tracking(other), stages.stage("render"):
            pytest.fail("stage work started without a lease")
    assert records(pg) == []


def test_recovery_closes_the_abandoned_stage_and_rejects_old_outcomes(pg, context):
    execution_id = db.start_stage(context, "render", "chapter:1")
    pg.execute("update jobs set lease_expires_at = now() - interval '1 second' where id = %s", (context.job_id,))
    assert db.recover_expired_jobs() == [{"id": context.job_id, "status": "pending"}]
    row = records(pg)[0]
    assert row["status"] == "abandoned" and row["completed_at"] is not None
    assert "lease expired" in row["error"]
    db.claim_job("worker-b")
    assert db.finish_stage(execution_id, "worker-a", "done") is False


def test_expired_lease_cannot_start_or_finish_a_stage(pg, context):
    execution_id = db.start_stage(context, "render", "")
    pg.execute("update jobs set lease_expires_at = now() - interval '1 second' where id = %s", (context.job_id,))
    assert db.start_stage(context, "upload", "") is None
    assert db.finish_stage(execution_id, "worker-a", "done") is False


def test_failed_operation_reports_lease_loss_when_the_lease_expired(pg, context):
    with pytest.raises(LeaseLost):
        with stages.tracking(context), stages.stage("render"):
            pg.execute("update jobs set lease_expires_at = now() - interval '1 second' where id = %s", (context.job_id,))
            raise TimeoutError("renderer stalled beyond the lease")
    assert records(pg)[0]["status"] == "running"


def test_job_failure_closes_unfinished_stage_records(pg, context):
    db.start_stage(context, "render", "")
    db.fail_job(context.job_id, "worker-a", "worker interrupted", "permanent")
    row = records(pg)[0]
    assert row["status"] == "abandoned"
    assert row["error"] == "worker interrupted"


def test_failure_to_record_stage_error_preserves_the_provider_error(pg, context, monkeypatch):
    def unavailable(*args):
        raise ConnectionError("database temporarily unavailable")

    monkeypatch.setattr(db, "finish_stage", unavailable)
    with pytest.raises(ValueError, match="invalid provider input"):
        with stages.tracking(context), stages.stage("script"):
            raise ValueError("invalid provider input")


def test_legacy_calls_do_no_tracking_io_without_a_context(monkeypatch):
    def unexpected(*args):
        pytest.fail("legacy call unexpectedly contacted the database")

    monkeypatch.setattr(db, "start_stage", unexpected)
    with stages.stage("render"):
        pass


def test_tracking_context_is_reset_after_an_exception(monkeypatch):
    monkeypatch.setattr(db, "start_stage", lambda *args: "execution-1")
    monkeypatch.setattr(db, "finish_stage", lambda *args: True)
    with pytest.raises(ValueError):
        with stages.tracking(PipelineContext("job-1", "brainrot", {}, 1, "worker-a")):
            raise ValueError("stopped")

    def unexpected(*args):
        pytest.fail("execution context leaked outside its scope")

    monkeypatch.setattr(db, "start_stage", unexpected)
    with stages.stage("render"):
        pass


@pytest.mark.parametrize("fn", ["start_stage", "finish_stage", "abandon_job_stages"])
def test_browser_roles_cannot_execute_stage_functions(pg, fn):
    for role in ("anon", "authenticated"):
        assert pg.execute(
            "select bool_or(has_function_privilege(%s,p.oid,'execute')) from pg_proc p where proname=%s",
            (role, fn),
        ).fetchone()["bool_or"] is False


def test_stage_table_has_closed_rls(pg):
    assert pg.execute("select relrowsecurity from pg_class where oid='stage_executions'::regclass").fetchone()["relrowsecurity"]
    assert pg.execute("select count(*) from pg_policies where tablename='stage_executions'").fetchone()["count"] == 0

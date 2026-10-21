from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from brainrot import api, db, worker
from brainrot.application import stages
from brainrot.application.registry import PipelineRegistry
from brainrot.domain.pipelines import PipelineContext, PipelineResult
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job, job


@pytest.fixture
def lifecycle(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    monkeypatch.setattr(api, "API_KEY", "integration-key")
    failures = []

    class Pipeline:
        name = "brainrot"

        def execute(self, context):
            with stages.tracking(context), stages.stage("script"):
                if failures:
                    raise failures.pop()
            return PipelineResult()

    monkeypatch.setattr(worker, "REGISTRY", PipelineRegistry([Pipeline()]))
    return failures


def test_job_to_stages_to_completion_to_authenticated_read_model(pg, lifecycle):
    job_id = add_job(pg)
    assert worker.run_once(worker_id="integration-worker") is True
    assert job(pg, job_id)["status"] == "done"
    http = TestClient(api.app, headers={"X-API-Key": "integration-key"})
    detail = http.get("/jobs/" + job_id).json()
    assert detail["job"]["status"] == "done" and detail["stages"][0]["status"] == "done"
    metrics = http.get("/metrics").text
    assert 'brainrot_jobs_completed_total{pipeline="brainrot"} 1' in metrics


def test_transient_failure_then_retry_records_both_attempts(pg, lifecycle):
    job_id = add_job(pg)
    lifecycle.append(TimeoutError("temporary"))
    worker.run_once(worker_id="first")
    assert job(pg, job_id)["status"] == "pending"
    pg.execute("update jobs set run_after=now() where id=%s", (job_id,))
    worker.run_once(worker_id="second")
    assert job(pg, job_id)["status"] == "done"
    rows = pg.execute("select attempt,status from stage_executions where job_id=%s order by attempt", (job_id,)).fetchall()
    assert [(r["attempt"],r["status"]) for r in rows] == [(1,"failed"),(2,"done")]


def test_worker_disappearance_closes_stage_and_recovers_on_next_iteration(pg, lifecycle):
    job_id = add_job(pg)
    db.claim_job("crashed")
    db.start_stage(PipelineContext(job_id,"brainrot",{},1,"crashed"),"render")
    pg.execute("update jobs set lease_expires_at=now()-interval '1 second' where id=%s", (job_id,))
    worker.run_once(worker_id="replacement")
    assert job(pg, job_id)["status"] == "done" and job(pg, job_id)["attempts"] == 2
    assert pg.execute("select status from stage_executions where stage='render'").fetchone()["status"] == "abandoned"

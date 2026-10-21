from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from brainrot import api, db
from brainrot.observability.metrics import RequestMetrics, render
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


def test_durable_metrics_capture_retry_completion_and_stage_duration(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg)
    db.claim_job("a")
    db.fail_job(job_id, "a", "timeout", "transient", datetime.now(timezone.utc))
    db.claim_job("b")
    from brainrot.domain.pipelines import PipelineContext
    stage_id = db.start_stage(PipelineContext(job_id, "brainrot", {}, 2, "b"), "render")
    db.finish_stage(stage_id, "b", "done")
    db.complete_job(job_id, "b")
    snapshot = db.operational_metrics()
    text = render(snapshot, RequestMetrics())
    assert 'brainrot_jobs_processed_total{pipeline="brainrot"} 2' in text
    assert 'brainrot_jobs_retried_total{pipeline="brainrot"} 1' in text
    assert 'brainrot_jobs_completed_total{pipeline="brainrot"} 1' in text
    assert 'brainrot_stage_duration_seconds_count{pipeline="brainrot",stage="render"} 1' in text
    assert 'brainrot_job_duration_seconds_count{pipeline="brainrot"} 2' in text
    assert text.endswith("\n")


def test_recovery_and_failure_counters_are_persistent(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    add_job(pg, max_attempts=1)
    db.claim_job("crashed", lease_seconds=0)
    db.recover_expired_jobs()
    output = render(db.operational_metrics(), RequestMetrics())
    assert 'brainrot_jobs_recovered_total{pipeline="brainrot"} 1' in output
    assert 'brainrot_jobs_failed_total{pipeline="brainrot"} 1' in output


def test_queue_depth_excludes_future_retries_from_ready_depth(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    add_job(pg)
    pg.execute("insert into jobs(kind,run_after) values ('brainrot',now()+interval '1 hour')")
    text = render(db.operational_metrics(), RequestMetrics())
    assert 'brainrot_queue_depth{pipeline="brainrot",state="pending"} 2' in text
    assert 'brainrot_queue_ready{pipeline="brainrot"} 1' in text


def test_request_metrics_bound_labels_and_histogram_buckets():
    requests = RequestMetrics()
    requests.observe("/jobs/{job_id}", "GET", 200, 0.25)
    output = render({}, requests)
    assert 'brainrot_api_duration_seconds_count{route="/jobs/{job_id}",method="GET",status="200"} 1' in output
    assert 'le="+Inf"} 1' in output


def test_metrics_endpoint_requires_key_and_never_queries_db_when_unauthorized(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-dashboard-key")
    monkeypatch.setattr(db, "operational_metrics", lambda: pytest.fail("unauthorized database query"))
    assert TestClient(api.app).get("/metrics").status_code == 401


def test_metrics_endpoint_returns_prometheus_text(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-dashboard-key")
    monkeypatch.setattr(db, "operational_metrics", lambda: {})
    response = TestClient(api.app).get("/metrics", headers={"X-API-Key": "test-dashboard-key"})
    assert response.status_code == 200
    assert "version=0.0.4" in response.headers["content-type"]
    assert "test-dashboard-key" not in response.text


@pytest.mark.parametrize("fn", ["operational_metrics", "record_job_metrics", "record_stage_metrics", "record_publication_metrics"])
def test_browser_roles_cannot_access_metric_functions(pg, fn):
    for role in ("anon", "authenticated"):
        assert pg.execute("select bool_or(has_function_privilege(%s,p.oid,'execute')) from pg_proc p where proname=%s", (role, fn)).fetchone()["bool_or"] is False

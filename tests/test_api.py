import pytest
from fastapi.testclient import TestClient

from brainrot import api, db
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "dashboard-test-key")
    return TestClient(api.app, headers={"X-API-Key": "dashboard-test-key"})


@pytest.mark.parametrize("provider", ["claude-code", "codex"])
@pytest.mark.parametrize("payload", [
    {"kind": "brainrot", "topic": "octopuses"},
    {"kind": "repurpose", "youtube_url": "https://youtube.com/watch?v=example"},
])
def test_new_job_persists_the_selected_local_provider(http, fake_db, provider, payload):
    response = http.post("/jobs", json={**payload, "llm_provider": provider})
    assert response.status_code == 200
    assert db.get_job(response.json()["id"])["params"]["llm_provider"] == provider


@pytest.mark.parametrize("provider", ["anthropic", "unknown", "codex --unsafe", {"value": "codex"}])
def test_frontend_cannot_select_api_billing_or_arbitrary_commands(http, provider):
    assert http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses", "llm_provider": provider}).status_code == 422


def test_legacy_enqueue_keeps_worker_default_behavior(http, fake_db):
    response = http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses"})
    assert response.status_code == 200
    assert "llm_provider" not in db.get_job(response.json()["id"])["params"]


def test_operational_job_list_uses_bounded_parameters_and_explicit_fields(http, monkeypatch):
    seen = []
    monkeypatch.setattr(db, "list_job_executions", lambda limit: seen.append(limit) or [{
        "id": "job-1", "kind": "brainrot", "status": "pending", "attempts": 1,
        "params": {"topic": "story", "llm_provider": "codex", "access_token": "private-provider-token"},
        "service_role_key": "private-service-key", "lease_owner": "private-worker",
    }])
    response = http.get("/jobs?limit=20")
    assert response.status_code == 200 and seen == [20]
    assert "private" not in response.text
    assert response.json()[0]["attempts"] == 1
    assert response.json()[0]["params"]["llm_provider"] == "codex"
    assert http.get("/jobs?limit=-1").status_code == 422
    assert http.get("/jobs?limit=201").status_code == 422


def test_job_details_include_stage_attempts_and_publications_with_redacted_errors(http, monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sensitive-live-value")
    monkeypatch.setattr(db, "job_execution", lambda job_id: {
        "job": {"id": str(job_id), "kind": "brainrot", "status": "failed", "error": "ValueError: sensitive-live-value"},
        "stages": [{"stage": "render", "attempt": 2, "status": "failed", "error": "token=signed-secret", "private": "drop-me"}],
        "publications": [{"platform": "youtube", "status": "scheduled", "data": {"access_token": "drop-me"}}],
    })
    response = http.get("/jobs/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 200
    assert response.json()["stages"][0]["attempt"] == 2
    assert all(secret not in response.text for secret in ("sensitive-live-value", "signed-secret", "drop-me"))


def test_job_details_return_404_and_validate_uuid(http, monkeypatch):
    monkeypatch.setattr(db, "job_execution", lambda job_id: None)
    assert http.get("/jobs/00000000-0000-0000-0000-000000000001").status_code == 404
    assert http.get("/jobs/not-a-uuid").status_code == 422


def test_sql_read_model_includes_current_stage_and_attempt_duration(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg)
    db.claim_job("worker-a")
    from brainrot.domain.pipelines import PipelineContext
    db.start_stage(PipelineContext(job_id, "brainrot", {}, 1, "worker-a"), "render", "chapter:1")
    rows = db.list_job_executions(10)
    assert rows[0]["current_stage"]["stage"] == "render"
    assert rows[0]["duration_seconds"] >= 0
    detail = db.job_execution(job_id)
    assert detail["job"]["id"] == job_id and len(detail["stages"]) == 1


@pytest.mark.parametrize("path", ["/jobs", "/metrics", "/jobs/00000000-0000-0000-0000-000000000001", "/gallery"])
def test_operational_endpoints_reject_unset_or_wrong_keys(monkeypatch, path):
    monkeypatch.setattr(api, "API_KEY", "")
    assert TestClient(api.app).get(path, headers={"X-API-Key": "anything"}).status_code == 401


@pytest.mark.parametrize("fn", ["list_job_executions", "job_execution"])
def test_job_inspection_rpc_is_server_only(pg, fn):
    for role in ("anon", "authenticated"):
        assert pg.execute("select bool_or(has_function_privilege(%s,p.oid,'execute')) from pg_proc p where proname=%s", (role, fn)).fetchone()["bool_or"] is False

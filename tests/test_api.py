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
    assert "brainrot_level" not in db.get_job(response.json()["id"])["params"]


@pytest.mark.parametrize("level", [0, 35, 100])
def test_enqueue_persists_brainrot_level(http, fake_db, level):
    response = http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses", "llm_provider": "codex", "brainrot_level": level})
    assert response.status_code == 200
    assert db.get_job(response.json()["id"])["params"]["brainrot_level"] == level


@pytest.mark.parametrize("level", [-1, 101, 35.5, "50", True, False])
def test_invalid_brainrot_level_is_rejected(http, level):
    assert http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses", "brainrot_level": level}).status_code == 422


def test_repurpose_does_not_accept_script_intensity(http):
    assert http.post("/jobs", json={"kind": "repurpose", "youtube_url": "https://youtu.be/example", "brainrot_level": 50}).status_code == 422


def test_operational_job_list_uses_bounded_parameters_and_explicit_fields(http, monkeypatch):
    seen = []
    monkeypatch.setattr(db, "list_job_executions", lambda limit: seen.append(limit) or [{
        "id": "job-1", "kind": "brainrot", "status": "pending", "attempts": 1,
        "params": {"topic": "story", "llm_provider": "codex", "brainrot_level": 85, "access_token": "private-provider-token"},
        "service_role_key": "private-service-key", "lease_owner": "private-worker",
    }])
    response = http.get("/jobs?limit=20")
    assert response.status_code == 200 and seen == [20]
    assert "private" not in response.text
    assert response.json()[0]["attempts"] == 1
    assert response.json()[0]["params"]["llm_provider"] == "codex"
    assert response.json()[0]["params"]["brainrot_level"] == 85
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


@pytest.mark.parametrize("result,status", [("deleted", 204), ("missing", 404), ("uploading", 409)])
def test_delete_job_returns_atomic_database_outcome(http, monkeypatch, result, status):
    monkeypatch.setattr(db, "delete_job", lambda job_id: result)
    cleaned = []
    monkeypatch.setattr(db, "cleanup_media", lambda job_id: cleaned.append(job_id))
    response = http.delete("/jobs/00000000-0000-0000-0000-000000000001")
    assert response.status_code == status
    if status == 204:
        assert not response.content
    assert cleaned == (["00000000-0000-0000-0000-000000000001"] if status == 204 else [])


def test_delete_requires_auth_and_valid_uuid(http, monkeypatch):
    monkeypatch.setattr(db, "delete_job", lambda job_id: pytest.fail("unexpected deletion"))
    assert TestClient(api.app).delete("/jobs/00000000-0000-0000-0000-000000000001").status_code == 401
    assert http.delete("/jobs/not-a-uuid").status_code == 422


def test_connection_reset_returns_recoverable_error_without_secrets(http, monkeypatch):
    import httpx
    def disconnected(limit):
        raise httpx.ReadError("private-connection-detail")
    monkeypatch.setattr(db, "list_job_executions", disconnected)
    response = http.get("/jobs")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "2"
    assert "private-connection-detail" not in response.text


@pytest.mark.parametrize("outcome,status", [("queued", 200), ("already_pending", 200), ("missing", 404), ("not_failed", 409)])
def test_retry_returns_same_job_and_database_outcome(http, monkeypatch, outcome, status):
    monkeypatch.setattr(db, "retry_job", lambda job_id: outcome)
    job_id = "00000000-0000-0000-0000-000000000001"
    response = http.post(f"/jobs/{job_id}/retry")
    assert response.status_code == status
    if status == 200:
        assert response.json() == {"id": job_id, "status": "pending"}


def test_retry_requires_auth_and_valid_uuid(http, monkeypatch):
    monkeypatch.setattr(db, "retry_job", lambda job_id: pytest.fail("unexpected retry"))
    assert TestClient(api.app).post("/jobs/00000000-0000-0000-0000-000000000001/retry").status_code == 401
    assert http.post("/jobs/not-a-uuid/retry").status_code == 422


def test_motion_graphics_is_stored_only_when_chosen(http, fake_db):
    off = http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses", "motion_graphics": False})
    on = http.post("/jobs", json={"kind": "brainrot", "topic": "octopuses", "motion_graphics": True})
    assert "motion_graphics" not in db.get_job(off.json()["id"])["params"]
    assert db.get_job(on.json()["id"])["params"]["motion_graphics"] is True


def test_repurpose_does_not_accept_motion_graphics(http):
    assert http.post("/jobs", json={"kind": "repurpose", "youtube_url": "https://youtu.be/example", "motion_graphics": True}).status_code == 422

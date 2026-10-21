import json
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from brainrot import api, db
from brainrot.observability.logging import JsonFormatter, event


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-key")
    return TestClient(api.app, headers={"X-API-Key": "test-key"})


@pytest.mark.parametrize("payload", [
    {"kind": "brainrot", "topic": " "},
    {"kind": "brainrot", "topic": "x" * 1001},
    {"kind": "brainrot", "topic": "story", "idempotency_key": "privileged-key"},
    {"kind": "repurpose", "youtube_url": "http://127.0.0.1/admin"},
    {"kind": "repurpose", "youtube_url": "file:///etc/passwd"},
    {"kind": "repurpose", "youtube_url": "https://youtube.com.attacker.test/watch?v=x"},
    {"kind": "repurpose", "youtube_url": "https://user:password@youtube.com/watch?v=x"},
    {"kind": "repurpose", "youtube_url": "https://youtube.com/redirect?q=http://localhost"},
])
def test_invalid_or_privileged_payloads_never_reach_the_queue(http, monkeypatch, payload):
    monkeypatch.setattr(db, "create_job", lambda *a, **kw: pytest.fail("unsafe enqueue"))
    assert http.post("/jobs", json=payload).status_code == 422


def test_valid_job_preserves_input_and_cannot_supply_an_idempotency_key(http, monkeypatch):
    seen = []
    monkeypatch.setattr(db, "create_job", lambda kind, **params: seen.append((kind, params)) or "job-1")
    assert http.post("/jobs", json={"kind": "repurpose", "youtube_url": "https://youtu.be/example"}).status_code == 200
    assert seen == [("repurpose", {"youtube_url": "https://youtu.be/example"})]


def test_unauthorized_enqueue_never_reaches_database(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-key")
    monkeypatch.setattr(db, "create_job", lambda *a, **kw: pytest.fail("unauthorized enqueue"))
    assert TestClient(api.app).post("/jobs", json={"kind": "brainrot", "topic": "story"}).status_code == 401


def test_non_ascii_bad_key_is_rejected_cleanly(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-key")
    with pytest.raises(HTTPException) as exc:
        api.require_key("wrong-ñ")
    assert exc.value.status_code == 401


def test_nested_values_cannot_escape_response_allowlists(http, monkeypatch):
    monkeypatch.setattr(db, "list_job_executions", lambda limit: [{
        "id": "job-1", "kind": "brainrot", "status": "pending",
        "params": {"topic": {"client_secret": "nested-private-value"}},
    }])
    assert "nested-private-value" not in http.get("/jobs").text


def test_secrets_do_not_appear_in_operational_events(monkeypatch, caplog):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "private-anthropic-key")
    with caplog.at_level(logging.INFO, logger="brainrot"):
        event("job_failed", job_id="private-anthropic-key", error_type="TimeoutError",
              authorization="Bearer private-header", credentials={"secret": "private-object"})
    output = JsonFormatter().format(caplog.records[-1])
    assert not any(value in output for value in ("private-anthropic-key", "private-header", "private-object"))

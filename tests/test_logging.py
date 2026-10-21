import json
import logging

import pytest

from brainrot.observability.logging import JsonFormatter, bind, event, safe_text


def test_logs_have_execution_fields_and_parse_as_json(caplog):
    with caplog.at_level(logging.INFO, logger="brainrot"):
        with bind(job_id="job-1", pipeline="brainrot", attempt=2, worker_id="worker-a"):
            with bind(stage="render", scope="chapter:1"):
                event("stage_completed", duration_seconds=1.25)
    payload = json.loads(JsonFormatter().format(caplog.records[-1]))
    assert {k: payload[k] for k in ("event", "job_id", "pipeline", "attempt", "worker_id", "stage")} == {
        "event": "stage_completed", "job_id": "job-1", "pipeline": "brainrot",
        "attempt": 2, "worker_id": "worker-a", "stage": "render",
    }
    assert payload["duration_seconds"] == 1.25
    assert payload["timestamp"].endswith("+00:00")


def test_log_context_is_reset_after_failure(caplog):
    with caplog.at_level(logging.INFO, logger="brainrot"):
        with pytest.raises(ValueError):
            with bind(job_id="private-job"):
                raise ValueError("stop")
        event("worker_started")
    assert "job_id" not in json.loads(JsonFormatter().format(caplog.records[-1]))


def test_unknown_fields_and_provider_payloads_are_excluded(caplog):
    with caplog.at_level(logging.INFO, logger="brainrot"):
        event("publication_failed", platform="youtube", credentials={"access_token": "do-not-log"}, params={"topic": "private"})
    text = JsonFormatter().format(caplog.records[-1])
    assert "do-not-log" not in text and "private" not in text
    assert json.loads(text)["platform"] == "youtube"


def test_known_environment_secrets_are_redacted(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-role-secret-value")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dashboard-secret-value")
    assert "service-role-secret-value" not in safe_text("error: service-role-secret-value")
    assert "dashboard-secret-value" not in safe_text("dashboard-secret-value")


@pytest.mark.parametrize("value,secret", [
    ("Authorization: Bearer abc.def.ghi", "abc.def.ghi"),
    ("https://media.test/video?token=signed-secret&expires=10", "signed-secret"),
    ("postgresql://user:db-password@pooler.test/db", "db-password"),
    ('{"client_secret": "provider-secret"}', "provider-secret"),
    ("access_token=provider-token", "provider-token"),
])
def test_redaction_covers_common_credential_formats(value, secret):
    assert secret not in safe_text(value)


def test_formatter_redacts_plain_messages_and_exception_details():
    record = logging.LogRecord("brainrot", logging.ERROR, __file__, 1, "token=plain-secret", (), None)
    output = JsonFormatter().format(record)
    assert "plain-secret" not in output
    assert json.loads(output)["event"]

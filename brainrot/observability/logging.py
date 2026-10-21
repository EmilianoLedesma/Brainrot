"""JSON events with bounded execution fields and credential redaction."""

import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

LOGGER = logging.getLogger("brainrot")
FIELDS = frozenset({
    "job_id", "pipeline", "stage", "scope", "attempt", "worker_id", "event",
    "status", "error_type", "error_kind", "duration_seconds", "retry_at",
    "publication_id", "platform", "chapter_id",
})
_fields: ContextVar[dict] = ContextVar("log_fields", default={})
_secret_name = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|DATABASE_URL", re.I)
_bearer = re.compile(r"(?i)(bearer\s+)[^\s,;\"']+")
_url_auth = re.compile(r"([a-z][a-z0-9+.-]*://)[^/\s@]+@", re.I)
_credential = re.compile(
    r"""(?i)(["']?(?:access_token|refresh_token|client_secret|api_key|service_role_key|password|token)["']?\s*[:=]\s*)(["']?)([^"'&\s,}\]]+)(["']?)"""
)


def safe_text(value: object) -> str:
    text = str(value)
    for name, secret in os.environ.items():
        if secret and len(secret) >= 4 and _secret_name.search(name):
            text = text.replace(secret, "[REDACTED]")
    text = _bearer.sub(r"\1[REDACTED]", text)
    text = _url_auth.sub(r"\1[REDACTED]@", text)
    return _credential.sub(lambda m: m[1] + m[2] + "[REDACTED]" + m[4], text)


@contextmanager
def bind(**fields):
    token = _fields.set({**_fields.get(), **{k: v for k, v in fields.items() if k in FIELDS}})
    try:
        yield
    finally:
        _fields.reset(token)


def event(name: str, level: int = logging.INFO, **fields) -> None:
    payload = {**_fields.get(), **{k: v for k, v in fields.items() if k in FIELDS}, "event": name}
    LOGGER.log(level, name, extra={"execution": payload})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            **{k: v for k, v in getattr(record, "execution", {}).items() if k in FIELDS},
        }
        for key, value in payload.items():
            if isinstance(value, str):
                payload[key] = safe_text(value)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False)


def configure() -> None:
    if not any(getattr(handler, "_brainrot_json", False) for handler in LOGGER.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler._brainrot_json = True
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False

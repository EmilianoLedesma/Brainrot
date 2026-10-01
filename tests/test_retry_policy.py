import subprocess
from datetime import datetime, timedelta, timezone

import anthropic
import httpx2
import pytest
import requests

from brainrot.application.retry import RetryPolicy, classify, decide
from brainrot.domain.jobs import PermanentError, TransientError

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
POLICY = RetryPolicy(base=timedelta(seconds=30), max_delay=timedelta(minutes=30))


def http_error(status: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"{status}", response=response)


def anthropic_error(cls, status: int):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("x", response=httpx2.Response(status, request=request), body=None)


def test_transient_error_schedules_a_retry():
    decision = decide(TimeoutError("slow"), attempt=1, max_attempts=3, now=NOW, policy=POLICY)
    assert decision.kind == "transient"
    assert decision.retry_at == NOW + timedelta(seconds=30)


def test_permanent_error_ends_the_job():
    decision = decide(PermanentError("no backgrounds"), attempt=1, max_attempts=3, now=NOW, policy=POLICY)
    assert decision.kind == "permanent"
    assert decision.retry_at is None


def test_running_out_of_attempts_ends_the_job():
    decision = decide(TimeoutError(), attempt=3, max_attempts=3, now=NOW, policy=POLICY)
    assert decision.kind == "transient"
    assert decision.retry_at is None


def test_backoff_doubles_and_is_bounded():
    assert [POLICY.delay(n).total_seconds() for n in (1, 2, 3, 4)] == [30, 60, 120, 240]
    assert POLICY.delay(7) == timedelta(minutes=30)
    assert POLICY.delay(10_000) == timedelta(minutes=30)  # no overflow
    with pytest.raises(ValueError):
        POLICY.delay(0)


@pytest.mark.parametrize(
    "exc",
    [
        TransientError("edge-tts returned no audio"),
        TimeoutError(),
        ConnectionResetError(),
        requests.ConnectionError(),
        requests.Timeout(),
        http_error(429),
        http_error(503),
        httpx2.ConnectError("refused"),
        anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com")),
        anthropic_error(anthropic.RateLimitError, 429),
        anthropic_error(anthropic.InternalServerError, 500),
        anthropic_error(anthropic.OverloadedError, 529),
    ],
    ids=lambda e: type(e).__name__,
)
def test_transient_classification(exc):
    assert classify(exc) == "transient"


@pytest.mark.parametrize(
    "exc",
    [
        PermanentError("Claude declined"),
        http_error(400),
        http_error(404),
        anthropic_error(anthropic.BadRequestError, 400),
        anthropic_error(anthropic.AuthenticationError, 401),
        subprocess.CalledProcessError(1, ["ffmpeg"]),
        KeyError("topic"),
        ValueError("bad"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_permanent_classification(exc):
    # Unknown errors are permanent: retrying a bug would just pay for the same
    # Claude call three times.
    assert classify(exc) == "permanent"


def test_classification_follows_the_cause_chain():
    try:
        try:
            raise TimeoutError("socket")
        except TimeoutError as inner:
            raise RuntimeError("upload failed") from inner
    except RuntimeError as outer:
        assert classify(outer) == "transient"


def test_an_explicit_permanent_marker_wins_over_its_cause():
    try:
        try:
            raise TimeoutError()
        except TimeoutError as inner:
            raise PermanentError("gave up") from inner
    except PermanentError as outer:
        assert classify(outer) == "permanent"


def test_a_bug_raised_while_handling_a_timeout_is_still_a_bug():
    try:
        try:
            raise TimeoutError()
        except TimeoutError:
            raise KeyError("oops")  # implicit context, not a cause
    except KeyError as exc:
        assert classify(exc) == "permanent"

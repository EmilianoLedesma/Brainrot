"""Whether a failed attempt is worth another try, and when.

Pure policy: it never touches the database. The worker asks `decide` and
records the answer with db.fail_job.

Errors are permanent unless recognised as transient. A bug retried three times
just pays for the same Claude call three times, so only failures that a later
attempt can plausibly get past (network, timeouts, rate limits, 5xx) are retried.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..domain.jobs import PermanentError, TransientError

TRANSIENT_STATUS = frozenset({408, 425, 429}) | frozenset(range(500, 600))


@dataclass(frozen=True)
class RetryPolicy:
    base: timedelta = timedelta(seconds=30)
    max_delay: timedelta = timedelta(minutes=30)

    def delay(self, attempt: int) -> timedelta:
        """min(base * 2^(attempt-1), max_delay) for the attempt that just failed."""
        if attempt < 1:
            raise ValueError("attempts are numbered from 1")
        # Cap the exponent: past ~2^20 the delay is far beyond any sane max anyway.
        return min(self.base * (2 ** min(attempt - 1, 20)), self.max_delay)


DEFAULT_POLICY = RetryPolicy()


@dataclass(frozen=True)
class Decision:
    kind: str  # "transient" or "permanent", stored as jobs.error_kind
    retry_at: datetime | None  # None ends the job as failed


def _transient_types() -> tuple[type, ...]:
    types: list[type] = [TransientError, TimeoutError, ConnectionError]
    try:
        import requests

        types += [requests.ConnectionError, requests.Timeout]
    except ImportError:
        pass
    for http in ("httpx", "httpx2"):  # supabase uses httpx, anthropic 1.x httpx2
        try:
            module = __import__(http)
            types.append(module.TransportError)
        except ImportError:
            pass
    try:
        import anthropic

        types += [anthropic.APIConnectionError, anthropic.RateLimitError]
    except ImportError:
        pass
    try:
        from edge_tts import exceptions as edge

        types += [edge.NoAudioReceived, edge.WebSocketError]
    except ImportError:
        pass
    return tuple(types)


_TRANSIENT = _transient_types()


def _status(exc: BaseException) -> int | None:
    """HTTP status carried by requests, httpx and anthropic errors, if any."""
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _classify_one(exc: BaseException) -> str | None:
    if isinstance(exc, PermanentError):
        return "permanent"
    if isinstance(exc, _TRANSIENT):
        return "transient"
    status = _status(exc)
    if status is not None:
        return "transient" if status in TRANSIENT_STATUS else "permanent"
    return None


def classify(exc: BaseException) -> str:
    """"transient" or "permanent". Follows `raise ... from` chains to the root cause.

    Only explicit causes count: a bug raised while handling a timeout is a bug.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        verdict = _classify_one(current)
        if verdict is not None:
            return verdict
        current = current.__cause__
    return "permanent"


def decide(
    exc: BaseException,
    attempt: int,
    max_attempts: int,
    now: datetime,
    policy: RetryPolicy = DEFAULT_POLICY,
) -> Decision:
    kind = classify(exc)
    if kind == "transient" and attempt < max_attempts:
        return Decision(kind, now + policy.delay(attempt))
    return Decision(kind, None)

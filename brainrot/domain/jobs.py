"""Job lifecycle rules. Pure: nothing here touches Supabase, ffmpeg or the network.

The states are exactly the `job_status` enum in migrations/001_init.sql. The
spec's names map onto them like this:

    processing  -> running
    completed   -> done
    retry_wait  -> pending, with jobs.run_after in the future

so waiting for a retry needs no extra enum value: a claim simply skips pending
rows whose run_after has not arrived yet.
"""

from enum import StrEnum


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL = frozenset({JobState.DONE, JobState.FAILED, JobState.CANCELLED})

_ALLOWED: dict[JobState, frozenset[JobState]] = {
    JobState.PENDING: frozenset({JobState.RUNNING, JobState.CANCELLED}),
    # Back to pending covers both a scheduled retry and recovery of a lease
    # whose worker disappeared.
    JobState.RUNNING: frozenset({JobState.DONE, JobState.FAILED, JobState.PENDING}),
}


class InvalidTransition(ValueError):
    pass


def transition(current: JobState, target: JobState) -> JobState:
    if target not in _ALLOWED.get(current, frozenset()):
        raise InvalidTransition(f"job cannot go from {current} to {target}")
    return target


class TransientError(Exception):
    """Worth retrying: the same input may well succeed later (network, rate limits)."""


class PermanentError(Exception):
    """Retrying cannot help: bad input, missing setup, a model refusal."""


class LeaseLost(Exception):
    """This worker no longer owns the job, so it must not record an outcome."""

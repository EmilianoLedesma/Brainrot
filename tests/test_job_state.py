import pytest

from brainrot.domain.jobs import TERMINAL, InvalidTransition, JobState, transition


def test_processing_can_complete():
    state = transition(JobState.PENDING, JobState.RUNNING)
    assert transition(state, JobState.DONE) == JobState.DONE


def test_processing_can_fail():
    assert transition(JobState.RUNNING, JobState.FAILED) == JobState.FAILED


def test_running_returns_to_pending_for_retry_or_recovery():
    # retry_wait in the spec is `pending` with run_after in the future, and
    # recovery of an abandoned lease is the same transition.
    assert transition(JobState.RUNNING, JobState.PENDING) == JobState.PENDING


def test_pending_can_be_cancelled():
    assert transition(JobState.PENDING, JobState.CANCELLED) == JobState.CANCELLED


def test_failed_job_can_be_explicitly_retried():
    assert transition(JobState.FAILED, JobState.PENDING) == JobState.PENDING


@pytest.mark.parametrize(
    "current,target",
    [
        (JobState.PENDING, JobState.DONE),  # never completes without running
        (JobState.PENDING, JobState.FAILED),
        (JobState.RUNNING, JobState.RUNNING),
        (JobState.DONE, JobState.RUNNING),
        (JobState.FAILED, JobState.RUNNING),
        (JobState.CANCELLED, JobState.RUNNING),
    ],
)
def test_invalid_transitions_are_rejected(current, target):
    with pytest.raises(InvalidTransition):
        transition(current, target)


def test_terminal_states_only_allow_explicit_retry_from_failed():
    assert TERMINAL == {JobState.DONE, JobState.FAILED, JobState.CANCELLED}
    for state in TERMINAL:
        for target in JobState:
            if state == JobState.FAILED and target == JobState.PENDING:
                continue
            with pytest.raises(InvalidTransition):
                transition(state, target)


def test_states_match_the_database_enum():
    # migrations/001_init.sql: job_status
    assert {s.value for s in JobState} == {"pending", "running", "done", "failed", "cancelled"}
    assert JobState("running") is JobState.RUNNING

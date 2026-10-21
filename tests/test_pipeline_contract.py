import dataclasses

import pytest

from brainrot.domain.pipelines import Pipeline, PipelineContext, PipelineResult


def context(**overrides) -> PipelineContext:
    fields = {
        "job_id": "job-1",
        "kind": "brainrot",
        "params": {"topic": "octopuses"},
        "attempt": 1,
        "worker_id": "worker-a",
    }
    return PipelineContext(**{**fields, **overrides})


class Echo:
    name = "echo"

    def execute(self, ctx: PipelineContext) -> PipelineResult:
        return PipelineResult(outputs={"topic": ctx.params["topic"]})


def test_a_plain_class_satisfies_the_pipeline_protocol():
    assert isinstance(Echo(), Pipeline)
    assert Echo().execute(context()).outputs == {"topic": "octopuses"}


def test_context_and_result_are_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        context().attempt = 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        PipelineResult().outputs = {}


def test_context_params_cannot_be_mutated_by_a_pipeline():
    ctx = context()
    with pytest.raises(TypeError):
        ctx.params["topic"] = "changed"


def test_context_exposes_the_legacy_job_row():
    # Existing handlers take the job row dict; the context can still produce it.
    row = context().job_row()
    assert row == {"id": "job-1", "kind": "brainrot", "params": {"topic": "octopuses"}}
    row["params"]["topic"] = "changed"
    assert context().params["topic"] == "octopuses"


def test_result_defaults_to_no_outputs():
    assert PipelineResult().outputs == {}

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from brainrot import pipeline, reddit, repurpose, worker
from brainrot.application.registry import PipelineRegistry, UnknownPipeline
from brainrot.domain.jobs import PermanentError
from brainrot.domain.pipelines import Pipeline, PipelineContext, PipelineResult
from brainrot.pipelines import create_registry


@pytest.mark.parametrize(
    "name,module,handler,output",
    [
        ("repurpose", repurpose, "run_repurpose", "source_video_id"),
        ("brainrot", pipeline, "run_brainrot", "story_id"),
        ("reddit", reddit, "run_reddit", "story_id"),
    ],
)
def test_registered_pipelines_preserve_handlers_and_return_record_ids(monkeypatch, name, module, handler, output):
    run = Mock(return_value="record-1")
    monkeypatch.setattr(module, handler, run)
    context = PipelineContext("job-1", name, {"input": "value"}, 2, "worker-a")

    resolved = create_registry().get(name)
    result = resolved.execute(context)

    assert isinstance(resolved, Pipeline)
    assert resolved.name == name
    assert isinstance(result, PipelineResult)
    assert result.outputs == {output: "record-1"}
    run.assert_called_once_with(context.job_row())


def test_unknown_pipeline_is_a_clear_permanent_error():
    with pytest.raises(UnknownPipeline, match="unknown pipeline: missing") as exc:
        create_registry().get("missing")
    assert isinstance(exc.value, PermanentError)


@dataclass
class ExamplePipeline:
    name: str = "example"

    def execute(self, context):
        return PipelineResult({"job_id": context.job_id})


def test_registration_rejects_duplicate_names():
    registry = PipelineRegistry([ExamplePipeline()])
    with pytest.raises(ValueError, match="already registered: example"):
        registry.register(ExamplePipeline())


def test_registries_are_independent():
    registry = PipelineRegistry()
    registry.register(ExamplePipeline())
    assert registry.get("example").name == "example"
    with pytest.raises(UnknownPipeline):
        PipelineRegistry().get("example")


@pytest.fixture
def claimed_job():
    return {"id": "job-1", "kind": "example", "params": {"input": "value"},
            "attempts": 2, "max_attempts": 3}


def test_worker_executes_newly_registered_pipeline_with_execution_context(monkeypatch, claimed_job):
    seen = []

    class CustomPipeline:
        name = "example"

        def execute(self, context):
            seen.append(context)
            return PipelineResult({"record_id": "record-1"})

    monkeypatch.setattr(worker, "REGISTRY", PipelineRegistry([CustomPipeline()]))
    complete = Mock(return_value=True)
    monkeypatch.setattr(worker.db, "complete_job", complete)

    assert worker.execute(claimed_job, worker_id="worker-a") == "done"
    assert seen == [PipelineContext("job-1", "example", {"input": "value"}, 2, "worker-a")]
    complete.assert_called_once_with("job-1", "worker-a")


def test_worker_records_unknown_pipeline_as_permanent_failure(monkeypatch, claimed_job):
    monkeypatch.setattr(worker, "REGISTRY", PipelineRegistry())
    fail = Mock(return_value="failed")
    complete = Mock()
    monkeypatch.setattr(worker.db, "fail_job", fail)
    monkeypatch.setattr(worker.db, "complete_job", complete)

    assert worker.execute(claimed_job, worker_id="worker-a") == "failed"
    args = fail.call_args.args
    assert args[:2] == ("job-1", "worker-a")
    assert "unknown pipeline: example" in args[2]
    assert args[3:] == ("permanent", None)
    complete.assert_not_called()


def test_worker_keeps_transient_retry_policy_for_registered_pipelines(monkeypatch, claimed_job):
    class Flaky:
        name = "example"

        def execute(self, context):
            raise TimeoutError("provider timed out")

    monkeypatch.setattr(worker, "REGISTRY", PipelineRegistry([Flaky()]))
    fail = Mock(return_value="pending")
    monkeypatch.setattr(worker.db, "fail_job", fail)

    assert worker.execute(claimed_job, worker_id="worker-a") == "pending"
    assert fail.call_args.args[3] == "transient"
    assert fail.call_args.args[4] is not None

"""The contract every content pipeline (H1, H2, H2b, and later ones) satisfies.

The worker only knows this interface: it claims a job, builds a context, calls
`execute`, and records the outcome. Nothing pipeline-specific lives in the worker.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


def _frozen(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class PipelineContext:
    job_id: str
    kind: str
    params: Mapping[str, Any]
    attempt: int
    worker_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "params", _frozen(self.params))

    def job_row(self) -> dict:
        """The job dict the pre-registry handlers were written against."""
        return {"id": self.job_id, "kind": self.kind, "params": dict(self.params)}


@dataclass(frozen=True)
class PipelineResult:
    """What a run produced, keyed by kind of record (e.g. {"story_id": ...})."""

    outputs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", _frozen(self.outputs))


@runtime_checkable
class Pipeline(Protocol):
    name: str

    def execute(self, context: PipelineContext) -> PipelineResult: ...

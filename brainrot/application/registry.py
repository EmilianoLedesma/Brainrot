"""Resolve stable job kinds to pipeline implementations without doing I/O."""

from collections.abc import Iterable

from ..domain.jobs import PermanentError
from ..domain.pipelines import Pipeline


class UnknownPipeline(PermanentError):
    """A job kind has no registered implementation; retrying cannot help."""


class PipelineRegistry:
    def __init__(self, pipelines: Iterable[Pipeline] = ()):
        self._pipelines: dict[str, Pipeline] = {}
        for pipeline in pipelines:
            self.register(pipeline)

    def register(self, pipeline: Pipeline) -> None:
        if pipeline.name in self._pipelines:
            raise ValueError(f"pipeline already registered: {pipeline.name}")
        self._pipelines[pipeline.name] = pipeline

    def get(self, name: str) -> Pipeline:
        try:
            return self._pipelines[name]
        except KeyError:
            raise UnknownPipeline(f"unknown pipeline: {name}") from None

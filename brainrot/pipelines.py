"""Register adapters for the existing H1, H2 and H2b entry points.

Keep composition here so adding a pipeline does not change the worker loop.
The existing functions remain usable by callers outside the worker.
"""

from collections.abc import Callable
from dataclasses import dataclass

from . import pipeline, reddit, repurpose
from .application.registry import PipelineRegistry
from .domain.pipelines import PipelineContext, PipelineResult


@dataclass(frozen=True)
class FunctionPipeline:
    name: str
    handler: Callable[[dict], str]
    output_key: str

    def execute(self, context: PipelineContext) -> PipelineResult:
        record_id = self.handler(context.job_row())
        return PipelineResult({self.output_key: record_id})


def create_registry() -> PipelineRegistry:
    return PipelineRegistry([
        FunctionPipeline("repurpose", repurpose.run_repurpose, "source_video_id"),
        FunctionPipeline("brainrot", pipeline.run_brainrot, "story_id"),
        FunctionPipeline("reddit", reddit.run_reddit, "story_id"),
    ])

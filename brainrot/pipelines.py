"""Register adapters for the existing H1, H2 and H2b entry points.

Keep composition here so adding a pipeline does not change the worker loop.
The existing functions remain usable by callers outside the worker.
"""

from collections.abc import Callable
from dataclasses import dataclass

from . import llm, pipeline, reddit, repurpose
from .application.registry import PipelineRegistry
from .application import stages
from .domain.pipelines import PipelineContext, PipelineResult


@dataclass(frozen=True)
class FunctionPipeline:
    name: str
    handler: Callable[[dict], str]
    output_key: str

    def execute(self, context: PipelineContext) -> PipelineResult:
        with stages.tracking(context), llm.using_provider(context.params.get("llm_provider")):
            record_id = self.handler(context.job_row())
        return PipelineResult({self.output_key: record_id})


def create_registry() -> PipelineRegistry:
    return PipelineRegistry([
        FunctionPipeline("repurpose", repurpose.run_repurpose, "source_video_id"),
        FunctionPipeline("brainrot", pipeline.run_brainrot, "story_id"),
        FunctionPipeline("reddit", reddit.run_reddit, "story_id"),
    ])

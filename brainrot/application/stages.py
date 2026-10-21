"""Track major operations inside a pipeline's leased execution context."""

from contextlib import contextmanager
from contextvars import ContextVar
import time

from .. import db
from ..domain.jobs import LeaseLost
from ..domain.pipelines import PipelineContext
from ..observability.logging import bind, event, safe_text

_context: ContextVar[PipelineContext | None] = ContextVar("pipeline_execution", default=None)


@contextmanager
def tracking(context: PipelineContext):
    token = _context.set(context)
    try:
        with bind(job_id=context.job_id, pipeline=context.kind, attempt=context.attempt, worker_id=context.worker_id):
            yield
    finally:
        _context.reset(token)


@contextmanager
def stage(name: str, scope: str = ""):
    with bind(stage=name, scope=scope):
        with _stage(name, scope):
            yield


@contextmanager
def _stage(name: str, scope: str):
    context = _context.get()
    if context is None:
        # Legacy direct calls and offline helpers have no leased job attempt.
        yield
        return

    execution_id = db.start_stage(context, name, scope)
    if execution_id is None:
        raise LeaseLost(f"cannot start stage {name}: job lease lost")
    started = time.monotonic()
    event("stage_started")
    try:
        yield
    except BaseException as exc:
        recorded = None
        try:
            recorded = db.finish_stage(execution_id, context.worker_id, "failed", safe_text(f"{type(exc).__name__}: {exc}"))
        except Exception as recording_error:
            # Keep the original error classification: a tracking outage must not
            # turn a permanent provider failure into another paid attempt.
            exc.add_note(f"stage outcome could not be recorded ({type(recording_error).__name__})")
            event("stage_recording_failed", error_type=type(recording_error).__name__)
        event("stage_failed", error_type=type(exc).__name__, duration_seconds=time.monotonic() - started)
        if recorded is False and isinstance(exc, Exception):
            raise LeaseLost(f"cannot fail stage {name}: job lease lost") from exc
        raise
    else:
        if not db.finish_stage(execution_id, context.worker_id, "done"):
            raise LeaseLost(f"cannot finish stage {name}: job lease lost")
        event("stage_completed", duration_seconds=time.monotonic() - started)

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Concatenate, cast

from mpt_extension_sdk.observability.tracing import (
    TRACER,
    get_business_attributes,
    set_attributes,
)

if TYPE_CHECKING:
    from mpt_extension_sdk.pipeline import BasePipeline, BaseStep, EventBaseContext

type PipelineCallable[PipelineT: "BasePipeline", CtxT: "EventBaseContext", ReturnT, **ParamT] = (
    Callable[Concatenate[PipelineT, CtxT, ParamT], Awaitable[ReturnT]]
)

type StepCallable[
    PipelineT: "BasePipeline",
    StepT: "BaseStep",
    CtxT: "EventBaseContext",
    ReturnT,
    **ParamT,
] = Callable[Concatenate[PipelineT, StepT, CtxT, ParamT], Awaitable[ReturnT]]


def start_pipeline_span[PipelineT: "BasePipeline", CtxT: "EventBaseContext", ReturnT, **ParamT](
    func: PipelineCallable[PipelineT, CtxT, ReturnT, ParamT],
) -> PipelineCallable[PipelineT, CtxT, ReturnT, ParamT]:
    """Start a child span for a pipeline execution."""

    @wraps(func)
    async def wrapper(
        self: PipelineT, ctx: CtxT, *args: ParamT.args, **kwargs: ParamT.kwargs
    ) -> ReturnT:
        with TRACER.start_as_current_span(f"pipeline: {self.name}") as span:
            set_attributes(
                span,
                {
                    "mpt.extension.pipeline_name": self.name,
                    "mpt.event.id": ctx.meta.event_id,
                    "mpt.task.id": ctx.meta.task_id,
                    **get_business_attributes(ctx),
                },
            )
            return await func(self, ctx, *args, **kwargs)

    return cast(PipelineCallable[PipelineT, CtxT, ReturnT, ParamT], wrapper)


def start_step_span[
    PipelineT: "BasePipeline",
    StepT: "BaseStep",
    CtxT: "EventBaseContext",
    ReturnT,
    **ParamT,
](
    func: StepCallable[PipelineT, StepT, CtxT, ReturnT, ParamT],
) -> StepCallable[PipelineT, StepT, CtxT, ReturnT, ParamT]:
    """Start and yield a child span for a step execution."""

    @wraps(func)
    async def wrapper(
        self: PipelineT, step: StepT, ctx: CtxT, *args: ParamT.args, **kwargs: ParamT.kwargs
    ) -> ReturnT:
        with TRACER.start_as_current_span(f"step: {step.name}") as span:
            set_attributes(
                span,
                {
                    "mpt.extension.step_name": step.name,
                    "mpt.event.id": ctx.meta.event_id,
                    "mpt.task.id": ctx.meta.task_id,
                    **get_business_attributes(ctx),
                },
            )
            return await func(self, step, ctx, *args, **kwargs)

    return cast(StepCallable[PipelineT, StepT, CtxT, ReturnT, ParamT], wrapper)

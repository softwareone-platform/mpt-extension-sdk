import asyncio
from logging import Logger

import pytest

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError
from mpt_extension_sdk.errors.step import DeferStepError, SkipStepError, StopStepError
from mpt_extension_sdk.pipeline.base import BasePipeline


def step_event(step, ctx, error):
    return step, ctx, error


class FakePipelineStep:
    def __init__(self, name, side_effect=None):
        self.name = name
        self.side_effect = side_effect
        self.run_calls = []

    async def run(self, ctx):
        self.run_calls.append(ctx)
        if self.side_effect is not None:
            raise self.side_effect


class FakePipeline(BasePipeline):
    def __init__(self, steps):
        self._steps = steps
        self.deferred = []
        self.failed = []
        self.skipped = []
        self.stopped = []
        self.succeeded = []

    @property
    def steps(self):
        return self._steps

    async def on_step_deferred(self, step, ctx, error):
        self.deferred.append(step_event(step, ctx, error))

    async def on_step_failed(self, step, ctx, error):
        self.failed.append(step_event(step, ctx, error))

    async def on_step_skipped(self, step, ctx, error):
        self.skipped.append(step_event(step, ctx, error))

    async def on_step_stopped(self, step, ctx, error):
        self.stopped.append(step_event(step, ctx, error))

    async def on_step_succeeded(self, step, ctx):
        self.succeeded.append((step, ctx))


class FakeLoggingPipeline(BasePipeline):
    def __init__(self, steps):
        self._steps = steps

    @property
    def steps(self):
        return self._steps


def test_pipeline_name():
    result = FakePipeline([]).name

    assert result == "FakePipeline"


@pytest.fixture
def pipeline_ctx(mocker):
    logger = mocker.Mock(spec=Logger)
    return mocker.Mock(logger=logger)


def test_execute_runs_all_steps(pipeline_ctx):
    steps = [FakePipelineStep("first"), FakePipelineStep("second")]
    pipeline = FakePipeline(steps)

    asyncio.run(pipeline.execute(pipeline_ctx))  # act

    assert steps[0].run_calls == [pipeline_ctx]
    assert steps[1].run_calls == [pipeline_ctx]
    assert pipeline.succeeded[0] == (steps[0], pipeline_ctx)
    assert pipeline.succeeded[1] == (steps[1], pipeline_ctx)


def test_execute_logs_pipeline_and_steps(pipeline_ctx):
    steps = [FakePipelineStep("first"), FakePipelineStep("second")]
    pipeline = FakePipeline(steps)

    asyncio.run(pipeline.execute(pipeline_ctx))  # act

    pipeline_ctx.logger.info.assert_any_call("Starting pipeline %s", pipeline.name)
    pipeline_ctx.logger.info.assert_any_call("Running step %s", "first")
    pipeline_ctx.logger.info.assert_any_call("Running step %s", "second")


def test_execute_defers_pipeline(pipeline_ctx):
    error = DeferStepError("later", delay_seconds=42)
    step = FakePipelineStep("defer", side_effect=error)
    pipeline = FakePipeline([step])

    with pytest.raises(DeferError, match="later") as exc_info:
        asyncio.run(pipeline.execute(pipeline_ctx))

    assert exc_info.value.delay_seconds == 42
    assert pipeline.deferred == [step_event(step, pipeline_ctx, error)]


def test_execute_skips_step(pipeline_ctx):
    error = SkipStepError("skip")
    step = FakePipelineStep("skip", side_effect=error)
    pipeline = FakePipeline([step])

    asyncio.run(pipeline.execute(pipeline_ctx))  # act

    assert pipeline.skipped == [step_event(step, pipeline_ctx, error)]


def test_execute_stops_pipeline(pipeline_ctx):
    error = StopStepError("stop")
    step = FakePipelineStep("stop", side_effect=error)
    pipeline = FakePipeline([step])

    with pytest.raises(CancelError, match="stop"):
        asyncio.run(pipeline.execute(pipeline_ctx))

    assert pipeline.stopped == [step_event(step, pipeline_ctx, error)]


def test_execute_fails_pipeline(pipeline_ctx):
    error = RuntimeError("boom")
    step = FakePipelineStep("fail", side_effect=error)
    pipeline = FakePipeline([step])

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(pipeline.execute(pipeline_ctx))

    assert pipeline.failed == [step_event(step, pipeline_ctx, error)]


@pytest.mark.parametrize(
    ("method_name", "step_name", "error", "message"),
    [
        (
            "on_step_deferred",
            "defer",
            DeferStepError("later", delay_seconds=3),
            "Step %s deferred - reason: %s",
        ),
        (
            "on_step_skipped",
            "skip",
            SkipStepError("skip"),
            "Step %s skipped - reason: %s",
        ),
        (
            "on_step_stopped",
            "stop",
            StopStepError("stop"),
            "Step %s stopped - reason: %s",
        ),
    ],
)
def test_default_error_callbacks_log(pipeline_ctx, method_name, step_name, error, message):
    pipeline = FakeLoggingPipeline([])
    step = FakePipelineStep(step_name)
    method = getattr(pipeline, method_name)

    asyncio.run(method(step, pipeline_ctx, error))  # act

    pipeline_ctx.logger.info.assert_called_once_with(message, step_name, error)


def test_default_succeeded_callback_logs(pipeline_ctx):
    pipeline = FakeLoggingPipeline([])
    step = FakePipelineStep("done")

    asyncio.run(pipeline.on_step_succeeded(step, pipeline_ctx))  # act

    pipeline_ctx.logger.info.assert_called_once_with("Step %s completed", step.name)


def test_default_failed_callback_logs_exception(pipeline_ctx):
    pipeline = FakeLoggingPipeline([])
    step = FakePipelineStep("fail")
    error = RuntimeError("boom")

    asyncio.run(pipeline.on_step_failed(step, pipeline_ctx, error))  # act

    pipeline_ctx.logger.error.assert_called_once_with(
        "Step %s - unhandled exception", step.name, exc_info=error
    )

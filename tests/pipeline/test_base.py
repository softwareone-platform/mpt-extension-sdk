from logging import Logger

import pytest

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError
from mpt_extension_sdk.errors.step import DeferStepError, SkipStepError, StopStepError
from mpt_extension_sdk.pipeline.base import BasePipeline
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.step import BaseStep


class FakeDemoPipeline(BasePipeline):
    def __init__(self, steps):
        self._steps = steps

    @property
    def steps(self):
        return self._steps


@pytest.fixture
def pipeline_ctx(mocker):
    ctx = mocker.create_autospec(EventBaseContext, instance=True)
    ctx.logger = mocker.create_autospec(Logger, instance=True)
    ctx.meta = EventMetadata(
        event_id="EVT-0001", object_id="ORD-0001", object_type="Order", task_id="TSK-0001"
    )
    return ctx


@pytest.fixture
def step_factory(mocker):
    def factory(name, side_effect=None):
        step = mocker.create_autospec(BaseStep, instance=True)
        step.name = name
        step.run.side_effect = side_effect
        return step

    return factory


def test_pipeline_name():
    result = FakeDemoPipeline([]).name

    assert result == "FakeDemoPipeline"


async def test_execute_runs_all_steps(mocker, pipeline_ctx, step_factory):
    steps = [step_factory("first"), step_factory("second")]
    pipeline = FakeDemoPipeline(steps)
    on_step_succeeded = mocker.patch.object(pipeline, "on_step_succeeded", autospec=True)

    await pipeline.execute(pipeline_ctx)  # act

    assert on_step_succeeded.await_args_list == [
        mocker.call(steps[0], pipeline_ctx),
        mocker.call(steps[1], pipeline_ctx),
    ]


async def test_execute_awaits_each_step(mocker, pipeline_ctx, step_factory):
    steps = [step_factory("first"), step_factory("second")]
    pipeline = FakeDemoPipeline(steps)

    await pipeline.execute(pipeline_ctx)  # act

    assert [step.run.await_args_list for step in steps] == [
        [mocker.call(pipeline_ctx)],
        [mocker.call(pipeline_ctx)],
    ]


async def test_execute_logs_pipeline_and_steps(pipeline_ctx, step_factory):
    pipeline = FakeDemoPipeline([step_factory("first"), step_factory("second")])

    await pipeline.execute(pipeline_ctx)  # act

    pipeline_ctx.logger.info.assert_any_call("Starting pipeline %s", pipeline.name)
    pipeline_ctx.logger.info.assert_any_call("Running step %s", "first")
    pipeline_ctx.logger.info.assert_any_call("Running step %s", "second")


async def test_execute_defers_pipeline(mocker, pipeline_ctx, step_factory):
    error = DeferStepError("later", delay_seconds=42)
    step = step_factory("defer", side_effect=error)
    pipeline = FakeDemoPipeline([step])
    on_step_deferred = mocker.patch.object(pipeline, "on_step_deferred", autospec=True)

    with pytest.raises(DeferError, match="later") as exc_info:
        await pipeline.execute(pipeline_ctx)

    assert exc_info.value.delay_seconds == 42
    on_step_deferred.assert_awaited_once_with(step, pipeline_ctx, error)


async def test_execute_skips_step(mocker, pipeline_ctx, step_factory):
    error = SkipStepError("skip")
    step = step_factory("skip", side_effect=error)
    pipeline = FakeDemoPipeline([step])
    on_step_skipped = mocker.patch.object(pipeline, "on_step_skipped", autospec=True)

    await pipeline.execute(pipeline_ctx)  # act

    on_step_skipped.assert_awaited_once_with(step, pipeline_ctx, error)


async def test_execute_stops_pipeline(mocker, pipeline_ctx, step_factory):
    error = StopStepError("stop")
    step = step_factory("stop", side_effect=error)
    pipeline = FakeDemoPipeline([step])
    on_step_stopped = mocker.patch.object(pipeline, "on_step_stopped", autospec=True)

    with pytest.raises(CancelError, match="stop"):
        await pipeline.execute(pipeline_ctx)

    on_step_stopped.assert_awaited_once_with(step, pipeline_ctx, error)


async def test_execute_fails_pipeline(mocker, pipeline_ctx, step_factory):
    error = RuntimeError("boom")
    step = step_factory("fail", side_effect=error)
    pipeline = FakeDemoPipeline([step])
    on_step_failed = mocker.patch.object(pipeline, "on_step_failed", autospec=True)

    with pytest.raises(RuntimeError, match="boom"):
        await pipeline.execute(pipeline_ctx)

    on_step_failed.assert_awaited_once_with(step, pipeline_ctx, error)


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
async def test_default_error_callbacks_log(
    pipeline_ctx, step_factory, method_name, step_name, error, message
):
    method = getattr(FakeDemoPipeline([]), method_name)

    await method(step_factory(step_name), pipeline_ctx, error)  # act

    pipeline_ctx.logger.info.assert_called_once_with(message, step_name, error)


async def test_default_succeeded_callback_logs(pipeline_ctx, step_factory):
    pipeline = FakeDemoPipeline([])

    await pipeline.on_step_succeeded(step_factory("done"), pipeline_ctx)  # act

    pipeline_ctx.logger.info.assert_called_once_with("Step %s completed", "done")


async def test_default_failed_callback_logs_exception(pipeline_ctx, step_factory):
    pipeline = FakeDemoPipeline([])
    error = RuntimeError("boom")

    await pipeline.on_step_failed(step_factory("fail"), pipeline_ctx, error)  # act

    pipeline_ctx.logger.error.assert_called_once_with(
        "Step %s - unhandled exception", "fail", exc_info=error
    )

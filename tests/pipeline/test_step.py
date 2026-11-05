import pytest

from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.pipeline.step import BaseStep


class FakeDemoStep(BaseStep):
    async def process(self, ctx):
        ctx.logger.info("Processing %s", self.name)


@pytest.fixture
def context_mock(mocker):
    return mocker.create_autospec(BaseContext, instance=True)


@pytest.fixture
def step():
    return FakeDemoStep()


@pytest.fixture
def lifecycle(mocker, step):
    manager = mocker.Mock()
    for hook_name in ("pre", "process", "post"):
        hook = mocker.patch.object(step, hook_name, autospec=True)
        manager.attach_mock(hook, hook_name)
    return manager


def test_step_name(step):
    result = step.name

    assert result == "FakeDemoStep"


async def test_run_calls_pre_process_post(mocker, step, lifecycle, context_mock):
    await step.run(context_mock)  # act

    assert lifecycle.mock_calls == [
        mocker.call.pre(context_mock),
        mocker.call.process(context_mock),
        mocker.call.post(context_mock),
    ]


async def test_run_raises_process_error_after_post(mocker, step, lifecycle, context_mock):
    lifecycle.process.side_effect = RuntimeError("process failed")

    with pytest.raises(RuntimeError, match="process failed"):
        await step.run(context_mock)

    assert lifecycle.mock_calls == [
        mocker.call.pre(context_mock),
        mocker.call.process(context_mock),
        mocker.call.post(context_mock),
    ]


async def test_run_raises_post_error(mocker, step, lifecycle, context_mock):
    lifecycle.post.side_effect = RuntimeError("post failed")

    with pytest.raises(RuntimeError, match="post failed"):
        await step.run(context_mock)

    assert lifecycle.mock_calls == [
        mocker.call.pre(context_mock),
        mocker.call.process(context_mock),
        mocker.call.post(context_mock),
    ]


async def test_run_chains_post_error_from_process_error(step, lifecycle, context_mock):
    process_error = RuntimeError("process failed")
    lifecycle.process.side_effect = process_error
    lifecycle.post.side_effect = RuntimeError("post failed")

    with pytest.raises(RuntimeError, match="post failed") as exc_info:
        await step.run(context_mock)

    assert exc_info.value.__cause__ is process_error


async def test_run_uses_default_pre_and_post_hooks(mocker, step, context_mock):
    process = mocker.patch.object(step, "process", autospec=True)

    await step.run(context_mock)  # act

    process.assert_awaited_once_with(context_mock)

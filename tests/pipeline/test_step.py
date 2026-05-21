import pytest

from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.pipeline.step import BaseStep


class FakeStep(BaseStep):
    def __init__(self, process_error=None, post_error=None):
        self.process_error = process_error
        self.post_error = post_error
        self.calls = []

    async def pre(self, context_mock):
        self.calls.append(("pre", context_mock))

    async def process(self, context_mock):
        self.calls.append(("process", context_mock))
        if self.process_error is not None:
            raise self.process_error

    async def post(self, context_mock):
        self.calls.append(("post", context_mock))
        if self.post_error is not None:
            raise self.post_error


class FakeMinimalStep(BaseStep):
    def __init__(self):
        self.calls = []

    async def process(self, context_mock):
        self.calls.append(("process", context_mock))


@pytest.fixture
def context_mock(mocker):
    return mocker.Mock(spec=BaseContext)


def test_step_name():
    result = FakeStep().name

    assert result == "FakeStep"


async def test_run_calls_pre_process_post(context_mock):
    step = FakeStep()

    await step.run(context_mock)  # act

    assert step.calls == [("pre", context_mock), ("process", context_mock), ("post", context_mock)]


async def test_run_raises_process_error_after_post(context_mock):
    error = RuntimeError("process failed")
    step = FakeStep(process_error=error)

    with pytest.raises(RuntimeError, match="process failed"):
        await step.run(context_mock)

    assert step.calls == [("pre", context_mock), ("process", context_mock), ("post", context_mock)]


async def test_run_raises_post_error(context_mock):
    error = RuntimeError("post failed")
    step = FakeStep(post_error=error)

    with pytest.raises(RuntimeError, match="post failed"):
        await step.run(context_mock)

    assert step.calls == [("pre", context_mock), ("process", context_mock), ("post", context_mock)]


async def test_run_chains_post_error_from_process_error(context_mock):
    process_error = RuntimeError("process failed")
    post_error = RuntimeError("post failed")
    step = FakeStep(process_error=process_error, post_error=post_error)

    with pytest.raises(RuntimeError, match="post failed") as exc_info:
        await step.run(context_mock)

    assert exc_info.value.__cause__ is process_error
    assert step.calls == [("pre", context_mock), ("process", context_mock), ("post", context_mock)]


async def test_run_uses_default_pre_and_post_hooks(context_mock):
    step = FakeMinimalStep()

    await step.run(context_mock)  # act

    assert step.calls == [("process", context_mock)]

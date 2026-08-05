import asyncio

import pytest

from mpt_extension_sdk.errors.pipeline import CancelError, DeferError, FailError
from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError
from mpt_extension_sdk.runtime.async_tasks import (
    PROCESSING_TIMEOUT_REASON,
    SHUTDOWN_INTERRUPTION_REASON,
    AsyncTaskRunner,
    TaskExecution,
)

DEFAULT_DEADLINE_SECONDS = 60


@pytest.fixture
def submit(task_service, logger):
    def factory(runner, task_callback, deadline=DEFAULT_DEADLINE_SECONDS):
        return runner.submit(
            execution=TaskExecution(
                task_id="TSK-1",
                task_callback=task_callback,
                task_service=task_service,
                handler_logger=logger,
                deadline_seconds=deadline,
            ),
        )

    return factory


@pytest.fixture
def reserve_holder():
    def factory(runner, acquired, release):
        async def wrapper():
            with runner.reserve("TSK-1"):
                acquired.set()
                await release.wait()

        return wrapper()

    return factory


@pytest.fixture
def failing_create_task(mocker):
    def factory(coro, **kwargs):
        coro.close()
        raise RuntimeError("no running loop")

    return mocker.patch("asyncio.create_task", side_effect=factory, autospec=True)


@pytest.mark.parametrize(
    ("error", "expected_action", "expected_kwargs"),
    [
        (DeferError("later"), "reschedule", {}),
        (CancelError("cancelled"), "fail", {"reason": "cancelled"}),
        (FailError("failed"), "fail", {"reason": "failed"}),
        (RuntimeError("unexpected"), "fail", {"reason": "Unexpected error"}),
    ],
)
async def test_runner_maps_handler_errors(
    mocker, task_service, submit, error, expected_action, expected_kwargs
):
    runner = AsyncTaskRunner()
    task_callback = mocker.AsyncMock(side_effect=error)
    submit(runner, task_callback)

    await asyncio.sleep(0)  # act

    getattr(task_service, expected_action).assert_awaited_once_with("TSK-1", **expected_kwargs)


async def test_runner_completes_task(mocker, task_service, submit):
    runner = AsyncTaskRunner()
    submit(runner, mocker.AsyncMock())

    await asyncio.sleep(0)  # act

    task_service.complete.assert_awaited_once_with("TSK-1")


async def test_runner_rejects_duplicate(mocker, submit):
    runner = AsyncTaskRunner()
    submit(runner, mocker.AsyncMock())

    duplicate = submit(runner, mocker.AsyncMock())  # act

    assert duplicate is False
    await asyncio.sleep(0)


async def test_submit_rejected_when_reserved_elsewhere(mocker, submit, reserve_holder):
    runner = AsyncTaskRunner()
    acquired, release = asyncio.Event(), asyncio.Event()
    holder = asyncio.create_task(reserve_holder(runner, acquired, release))
    await acquired.wait()

    result = submit(runner, mocker.AsyncMock())
    release.set()
    await holder

    assert result is False


def test_submit_raises_when_creation_fails(mocker, submit, failing_create_task):
    runner = AsyncTaskRunner()

    with pytest.raises(AsyncTasksRunnerError, match="Failed to submit task"):
        submit(runner, mocker.AsyncMock())


def test_runner_reserves_task_atomically():
    runner = AsyncTaskRunner()

    with runner.reserve("TSK-1") as first, runner.reserve("TSK-1") as duplicate:
        first_and_duplicate = (first, duplicate)  # act

    assert first_and_duplicate == (True, False)


async def test_runner_shutdown_fails_interrupted_task(mocker, task_service, submit):
    runner = AsyncTaskRunner()
    submit(runner, mocker.AsyncMock(side_effect=asyncio.Event().wait))
    await asyncio.sleep(0)

    await runner.shutdown()  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason=SHUTDOWN_INTERRUPTION_REASON)


async def test_runner_rejects_submit_after_shutdown(mocker, submit):
    runner = AsyncTaskRunner()
    await runner.shutdown()

    result = submit(runner, mocker.AsyncMock())

    assert result is False


async def test_runner_fails_expired_processing(mocker, task_service, submit):
    runner = AsyncTaskRunner()
    submit(runner, mocker.AsyncMock(side_effect=asyncio.Event().wait), deadline=0.001)

    await asyncio.sleep(0.01)  # act

    task_service.fail.assert_awaited_once_with("TSK-1", reason=PROCESSING_TIMEOUT_REASON)

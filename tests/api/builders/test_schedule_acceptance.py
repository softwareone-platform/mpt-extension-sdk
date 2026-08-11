import pytest
from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.builders.schedule_acceptance import ScheduleTaskAcceptance
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.models.task import Task


@pytest.fixture
def acceptance(task_service, logger):
    return ScheduleTaskAcceptance(task_service=task_service, handler_logger=logger)


async def test_fetch_task_returns_task(acceptance, task_service, mocker):
    task = mocker.Mock(spec=Task)
    task_service.get.return_value = task

    result = await acceptance.fetch_task("TSK-1")

    assert result is task


async def test_fetch_task_returns_none_on_error(acceptance, task_service):
    task_service.get.side_effect = MPTError("boom")

    result = await acceptance.fetch_task("TSK-1")

    assert result is None


async def test_reschedule_lost_returns_none(acceptance, task_service):
    result = await acceptance.reschedule_lost_task("TSK-1")

    assert result is None


async def test_reschedule_lost_defers_on_error(acceptance, task_service):
    task_service.reschedule.side_effect = MPTError("boom")

    result = await acceptance.reschedule_lost_task("TSK-1")

    assert result == EventResponse.reschedule()


async def test_start_task_returns_none(acceptance, task_service):
    result = await acceptance.start_task("TSK-1")

    assert result is None


async def test_start_task_defers_on_error(acceptance, task_service):
    task_service.start.side_effect = MPTError("boom")

    result = await acceptance.start_task("TSK-1")

    assert result == EventResponse.reschedule()


async def test_reschedule_after_submit_swallows(acceptance, task_service):
    task_service.reschedule.side_effect = MPTError("boom")

    await acceptance.reschedule_after_failed_submit("TSK-1")  # act

    task_service.reschedule.assert_awaited_once_with("TSK-1")


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (AuthenticationError("bad"), "Authentication failed"),
        (ConfigError("bad"), "Non-recoverable context error"),
    ],
)
def test_map_context_error_cancels(acceptance, error, expected_reason):
    result = acceptance.map_context_error(error)

    assert result == EventResponse.cancel(reason=expected_reason)


def test_map_context_error_defers(acceptance):
    result = acceptance.map_context_error(RuntimeError("transient"))

    assert result == EventResponse.reschedule()

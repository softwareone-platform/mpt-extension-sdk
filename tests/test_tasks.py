import pytest
from mpt_api_client.exceptions import MPTError
from pydantic import ValidationError

from mpt_extension_sdk.models.task import TaskLog, TaskLogSeverity
from mpt_extension_sdk.tasks import TaskHandle


async def test_task_reports_progress(task_service):
    task = TaskHandle(id="TSK-1", task_service=task_service)

    await task.progress(0.5)  # act

    task_service.progress.assert_awaited_once_with("TSK-1", 0.5)


async def test_task_ignores_progress_errors(mocker, task_service):
    task_service.progress.side_effect = MPTError("MPT unavailable")
    task = TaskHandle(id="TSK-1", task_service=task_service)
    logger = mocker.patch("mpt_extension_sdk.tasks.logger")

    await task.progress(0.5)  # act

    logger.warning.assert_called_once()


async def test_task_writes_info_log(task_service):
    task = TaskHandle(id="TSK-1", task_service=task_service)

    await task.log("Synchronizing agreements")  # act

    task_service.create_log.assert_awaited_once_with(
        "TSK-1", TaskLog(message="Synchronizing agreements", severity=TaskLogSeverity.INFO)
    )


async def test_task_writes_log_with_parameters(task_service):
    task = TaskHandle(id="TSK-1", task_service=task_service)

    await task.log(  # act
        "Starting buyer '{{BuyerId}}' transfer",
        severity=TaskLogSeverity.WARNING,
        parameters={"BuyerId": "BUY-4230-6788"},
    )

    task_service.create_log.assert_awaited_once_with(
        "TSK-1",
        TaskLog(
            message="Starting buyer '{{BuyerId}}' transfer",
            severity=TaskLogSeverity.WARNING,
            parameters={"BuyerId": "BUY-4230-6788"},
        ),
    )


@pytest.mark.parametrize(
    "error",
    [
        MPTError("MPT unavailable"),
        ValidationError.from_exception_data("TaskLog", []),
    ],
)
async def test_task_ignores_log_errors(mocker, task_service, error):
    task_service.create_log.side_effect = error
    task = TaskHandle(id="TSK-1", task_service=task_service)
    logger = mocker.patch("mpt_extension_sdk.tasks.logger")

    await task.log("Synchronizing agreements")  # act

    logger.warning.assert_called_once()

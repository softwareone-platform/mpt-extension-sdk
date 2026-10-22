import pytest
from mpt_api_client.exceptions import MPTError
from pydantic import ValidationError

from mpt_extension_sdk.models.task import Task, TaskLog, TaskLogSeverity, TaskParameters
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


@pytest.fixture
def task_with_parameters(task_service):
    task_service.get.return_value = Task.from_payload({
        "id": "TSK-1",
        "status": "Processing",
        "parameters": {"extensionId": "EXT-1", "syncCursor": "AGR-0001"},
    })
    return TaskHandle(id="TSK-1", task_service=task_service)


async def test_task_sets_parameter_keeping_others(task_service, task_with_parameters):
    await task_with_parameters.set_parameter("instanceId", "EXI-1")  # act

    task_service.set_parameters.assert_awaited_once_with(
        "TSK-1",
        TaskParameters.from_payload({
            "extensionId": "EXT-1",
            "syncCursor": "AGR-0001",
            "instanceId": "EXI-1",
        }),
    )


async def test_task_sets_first_parameter(task_service):
    task_service.get.return_value = Task.from_payload({"id": "TSK-1", "status": "Processing"})
    task = TaskHandle(id="TSK-1", task_service=task_service)

    await task.set_parameter("instanceId", "EXI-1")  # act

    task_service.set_parameters.assert_awaited_once_with(
        "TSK-1", TaskParameters.from_payload({"instanceId": "EXI-1"})
    )


async def test_task_removes_parameter_keeping_others(task_service, task_with_parameters):
    await task_with_parameters.remove_parameter("syncCursor")  # act

    task_service.set_parameters.assert_awaited_once_with(
        "TSK-1", TaskParameters.from_payload({"extensionId": "EXT-1"})
    )


async def test_task_skips_unchanged_set(task_service, task_with_parameters):
    await task_with_parameters.set_parameter("syncCursor", "AGR-0001")  # act

    task_service.set_parameters.assert_not_awaited()


async def test_task_skips_missing_removal(task_service, task_with_parameters):
    await task_with_parameters.remove_parameter("instanceId")  # act

    task_service.set_parameters.assert_not_awaited()


@pytest.mark.parametrize("failing_method", ["get", "set_parameters"])
async def test_task_set_parameter_raises_errors(task_service, task_with_parameters, failing_method):
    getattr(task_service, failing_method).side_effect = MPTError("MPT unavailable")

    with pytest.raises(MPTError):
        await task_with_parameters.set_parameter("instanceId", "EXI-1")  # act


@pytest.mark.parametrize("failing_method", ["get", "set_parameters"])
async def test_task_remove_parameter_raises_errors(
    task_service, task_with_parameters, failing_method
):
    getattr(task_service, failing_method).side_effect = MPTError("MPT unavailable")

    with pytest.raises(MPTError):
        await task_with_parameters.remove_parameter("syncCursor")  # act


async def test_task_refuses_to_set_reserved(task_service, task_with_parameters):
    with pytest.raises(ValueError, match="reserved"):
        await task_with_parameters.set_parameter("extensionId", "EXT-2")  # act

    task_service.set_parameters.assert_not_awaited()


async def test_task_refuses_to_remove_reserved(task_service, task_with_parameters):
    with pytest.raises(ValueError, match="reserved"):
        await task_with_parameters.remove_parameter("extensionId")  # act

    task_service.set_parameters.assert_not_awaited()

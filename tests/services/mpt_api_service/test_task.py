import warnings

import pytest

from mpt_extension_sdk.models.task import Task, TaskStatus, UnknownTaskStatusWarning
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.api_client_v2.system.system import AsyncSystem
from mpt_extension_sdk.services.api_client_v2.system.system_tasks import AsyncTasksService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def tasks_client(mocker):
    return mocker.AsyncMock(spec=AsyncTasksService)


@pytest.fixture
def service(mocker, tasks_client):
    client = mocker.Mock(spec=AsyncMPTClient, system=mocker.Mock(spec=AsyncSystem))
    client.system.tasks = tasks_client
    return TaskService(client)


@pytest.mark.parametrize(
    ("method_name", "args", "client_method", "client_args"),
    [
        ("complete", ("TASK-1",), "complete", ("TASK-1", {})),
        ("fail", ("TASK-1",), "fail", ("TASK-1",)),
        ("fail", ("TASK-1", "Timed out"), "fail", ("TASK-1", {"reason": "Timed out"})),
        ("progress", ("TASK-1", 0.5), "update", ("TASK-1", {"progress": 0.5})),
        ("reschedule", ("TASK-1",), "reschedule", ("TASK-1",)),
        ("start", ("TASK-1",), "execute", ("TASK-1",)),
    ],
)
async def test_task_service_actions(
    service, tasks_client, method_name, args, client_method, client_args
):
    method = getattr(service, method_name)

    await method(*args)  # act

    mock_method = getattr(tasks_client, client_method)
    mock_method.assert_awaited_once_with(*client_args)


async def test_task_service_get(service, tasks_client):
    tasks_client.get.return_value = {
        "id": "TASK-1",
        "status": "Processing",
        "audit": {"created": {"at": "2026-07-14T10:00:00Z"}},
    }

    task = await service.get("TASK-1")  # act

    tasks_client.get.assert_awaited_once_with("TASK-1")
    assert task.id == "TASK-1"
    assert task.is_processing is True
    assert task.is_final is False
    assert task.created_at is not None


@pytest.mark.parametrize(
    ("status", "is_final", "is_processing"),
    [
        ("Completed", True, False),
        ("Failed", True, False),
        ("Processing", False, True),
        ("Queued", False, False),
        ("Rescheduled", False, False),
        ("Waiting", False, False),
    ],
)
@pytest.mark.filterwarnings("ignore::mpt_extension_sdk.models.task.UnknownTaskStatusWarning")
def test_task_status_helpers(status, is_final, is_processing):
    task = Task(id="TASK-1", status=status)  # act

    assert task.is_final is is_final
    assert task.is_processing is is_processing


def test_task_status_parses_known_status_as_enum():
    task = Task(id="TASK-1", status="Completed")  # act

    assert task.status == TaskStatus.COMPLETED


@pytest.mark.filterwarnings("ignore::mpt_extension_sdk.models.task.UnknownTaskStatusWarning")
def test_task_status_keeps_unknown_as_string():
    task = Task(id="TASK-1", status="Waiting")  # act

    assert task.status == "Waiting"
    assert task.is_final is False


def test_task_warns_on_unknown_status():
    with pytest.warns(UnknownTaskStatusWarning, match="TASK-1"):
        Task(id="TASK-1", status="Waiting")  # act


def test_task_does_not_warn_on_known_status():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownTaskStatusWarning)

        Task(id="TASK-1", status="Completed")  # act

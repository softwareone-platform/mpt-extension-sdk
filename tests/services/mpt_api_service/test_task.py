import asyncio

import pytest

from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.api_client_v2.system.system import AsyncSystem
from mpt_extension_sdk.services.api_client_v2.system.system_tasks import AsyncTasksService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.mark.parametrize(
    ("method_name", "args", "client_method", "client_args"),
    [
        ("complete", ("TASK-1",), "complete", ("TASK-1", {})),
        ("fail", ("TASK-1",), "fail", ("TASK-1",)),
        ("progress", ("TASK-1", 0.5), "update", ("TASK-1", {"progress": 0.5})),
        ("reschedule", ("TASK-1",), "reschedule", ("TASK-1",)),
        ("start", ("TASK-1",), "execute", ("TASK-1",)),
    ],
)
def test_task_service_actions(mocker, method_name, args, client_method, client_args):
    tasks_client = mocker.AsyncMock(spec=AsyncTasksService)
    client = mocker.Mock(spec=AsyncMPTClient, system=mocker.Mock(spec=AsyncSystem))
    client.system.tasks = tasks_client
    service = TaskService(client)
    method = getattr(service, method_name)

    asyncio.run(method(*args))  # act

    mock_method = getattr(tasks_client, client_method)
    mock_method.assert_awaited_once_with(*client_args)

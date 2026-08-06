import pytest

from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def task_service(mocker):
    return mocker.AsyncMock(spec=TaskService)

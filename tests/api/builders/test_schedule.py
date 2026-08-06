import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mpt_extension_sdk.api.builders import schedule as schedule_builder
from mpt_extension_sdk.api.builders.dependencies import get_tasks_service
from mpt_extension_sdk.api.models.events import ResponseEnum
from mpt_extension_sdk.extension_app import ExtensionApp


@pytest.fixture
def task_headers():
    return {"MPT-Task-Id": "TSK-001"}


@pytest.fixture
def schedule_client(schedule_route, task_service, async_task_runner):
    app = FastAPI()
    app.state.async_task_runner = async_task_runner
    app.include_router(schedule_builder.create_schedule_route(schedule_route, ExtensionApp()))
    app.dependency_overrides[get_tasks_service] = lambda: task_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def patch_context(mocker, schedule_context):
    mocker.patch(
        "mpt_extension_sdk.api.builders.schedule_executor.RequestAuthenticationService.authenticate",
        autospec=True,
    )
    factory = mocker.patch(
        "mpt_extension_sdk.api.builders.schedule_executor.RouteContextFactory.from_service_type",
        autospec=True,
    )
    factory.return_value.build_schedule_context = mocker.AsyncMock(return_value=schedule_context)
    return factory.return_value.build_schedule_context


def test_route_defers_queued_task(patch_context, schedule_client, schedule_route, task_headers):
    result = schedule_client.post(schedule_route.path, headers=task_headers)

    assert result.json()["response"] == ResponseEnum.DEFER


def test_route_requires_task_id_header(patch_context, schedule_client, schedule_route):
    result = schedule_client.post(schedule_route.path)

    assert result.status_code == 422

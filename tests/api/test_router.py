import asyncio
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mpt_extension_sdk.api.models.events import ResponseEnum
from mpt_extension_sdk.api.router import (
    create_non_task_route,
    create_task_route,
    get_tasks_service,
    run_handler,
)
from mpt_extension_sdk.errors.pipeline import CancelError, DeferError, FailError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline.context.base import ExecutionContext
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def mock_callable(mocker):
    return mocker.Mock(spec=Callable)


@pytest.fixture
def task_event_payload():
    return {
        "id": "EVT-001",
        "details": {
            "enqueue_time": "2024-01-01T12:00:00Z",
            "event_type": "OrderPurchased",
            "delivery_time": "2024-01-01T12:01:00Z",
        },
        "object": {
            "id": "ORD-001",
            "object_type": "Order",
            "name": "OrderName",
        },
        "task": {"id": "TASK-001"},
    }


@pytest.fixture
def event_payload():
    return {
        "id": "EVT-002",
        "details": {
            "enqueue_time": "2024-01-01T12:00:00Z",
            "event_type": "OrderPurchased",
            "delivery_time": "2024-01-01T12:01:00Z",
        },
        "object": {
            "id": "ORD-001",
            "object_type": "Order",
            "name": "OrderName",
        },
    }


@pytest.fixture
def app_instance():
    return ExtensionApp()


@pytest.fixture
def fake_task_service(mocker):
    return mocker.AsyncMock(spec=TaskService)


@pytest.fixture
def fake_context(mocker):
    return mocker.Mock(spec=ExecutionContext)


@pytest.fixture
def patched_router_deps(mocker, fake_context):
    mocker.patch(
        "mpt_extension_sdk.api.router.build_context",
        autospec=True,
        return_value=fake_context,
    )
    mocker.patch(
        "mpt_extension_sdk.api.router.get_business_attributes",
        autospec=True,
        return_value={},
    )
    mocker.patch("mpt_extension_sdk.api.router.set_attributes", autospec=True)
    mocker.patch("mpt_extension_sdk.api.router.record_exception", autospec=True)
    mocker.patch("mpt_extension_sdk.api.router.set_event_context", autospec=True)
    mocker.patch("mpt_extension_sdk.api.router.start_event_span", autospec=True)


@pytest.fixture
def task_client(patched_router_deps, fake_task_service, app_instance):
    def factory(mock_callable):
        router = create_task_route("/test/task", mock_callable, app_instance)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_tasks_service] = lambda: fake_task_service
        return TestClient(app, raise_server_exceptions=False)

    return factory


@pytest.fixture
def non_task_client(patched_router_deps, app_instance):
    def factory(mock_callable):
        router = create_non_task_route("/test/event", mock_callable, app_instance)
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    return factory


def test_run_handler(mocker, fake_context, mock_callable):
    mock_callable = mocker.AsyncMock(spec=Callable, side_effect=mock_callable)

    asyncio.run(run_handler(mock_callable, "evt", fake_context))  # act

    mock_callable.assert_awaited_once_with("evt", fake_context)


def test_run_handler_propagates_async_exception(mocker, fake_context, mock_callable):
    mock_callable = mocker.AsyncMock(spec=Callable, side_effect=ValueError("async boom"))

    with pytest.raises(ValueError, match="async boom"):
        asyncio.run(run_handler(mock_callable, "evt", fake_context))


def test_get_tasks_service(mocker, runtime_settings):
    fake_api = mocker.Mock(spec=["tasks"])
    mock_mpt_api_service = mocker.patch(
        "mpt_extension_sdk.api.router.MPTAPIService",
        autospec=True,
    )
    mock_mpt_api_service.from_config.return_value = fake_api

    result = get_tasks_service(runtime_settings)

    assert result is fake_api.tasks
    mock_mpt_api_service.from_config.assert_called_once_with(
        base_url=runtime_settings.mpt_api_base_url,
        api_token=runtime_settings.ext_api_key,
    )


def test_create_task_route(mock_callable):
    router = create_task_route("/events/orders/purchase", mock_callable, ExtensionApp())

    result = router.routes

    assert len(result) == 1
    api_route = result[0]
    assert api_route.name == "handle_task_event"
    assert api_route.path == "/events/orders/purchase"
    assert api_route.methods == {"POST"}


def test_task_route_success(
    task_client, task_event_payload, mock_callable, fake_task_service, fake_context
):
    result = task_client(mock_callable).post("/test/task", json=task_event_payload)

    assert result.json()["response"] == ResponseEnum.OK
    fake_task_service.start.assert_awaited_once()
    fake_task_service.complete.assert_awaited_once()
    fake_task_service.fail.assert_not_awaited()
    mock_callable.assert_called_once_with(mock_callable.call_args.args[0], fake_context)


def test_task_route_cancel_error(fake_task_service, task_client, task_event_payload, mock_callable):
    mock_callable.side_effect = CancelError("not allowed")

    result = task_client(mock_callable).post("/test/task", json=task_event_payload)

    assert result.json()["response"] == ResponseEnum.CANCEL
    fake_task_service.fail.assert_awaited_once()
    fake_task_service.complete.assert_not_awaited()


def test_task_route_defer_error(fake_task_service, task_client, task_event_payload, mock_callable):
    mock_callable.side_effect = DeferError("retry later", delay_seconds=60)

    result = task_client(mock_callable).post("/test/task", json=task_event_payload)  # act

    assert result.json()["response"] == ResponseEnum.DEFER
    fake_task_service.reschedule.assert_awaited_once()
    fake_task_service.complete.assert_not_awaited()


def test_task_route_fail(fake_task_service, task_client, task_event_payload, mock_callable):
    mock_callable.side_effect = FailError("processing failed")

    result = task_client(mock_callable).post("/test/task", json=task_event_payload)

    assert result.json()["response"] == ResponseEnum.CANCEL
    fake_task_service.fail.assert_awaited_once()
    fake_task_service.complete.assert_not_awaited()


def test_task_route_unexpected_error(
    fake_task_service, task_client, task_event_payload, mock_callable
):
    mock_callable.side_effect = RuntimeError("unexpected")

    result = task_client(mock_callable).post("/test/task", json=task_event_payload)

    assert result.json()["response"] == ResponseEnum.CANCEL
    fake_task_service.fail.assert_awaited_once()
    fake_task_service.complete.assert_not_awaited()


def test_create_non_task_route(mock_callable):
    router = create_non_task_route("/events/orders/purchase", mock_callable, ExtensionApp())

    result = router.routes

    assert len(result) == 1
    api_route = result[0]
    assert api_route.name == "handle_event"
    assert api_route.path == "/events/orders/purchase"
    assert api_route.methods == {"POST"}


def test_non_task_route_success(fake_context, non_task_client, event_payload, mock_callable):
    result = non_task_client(mock_callable).post("/test/event", json=event_payload)

    assert result.json()["response"] == ResponseEnum.OK
    mock_callable.assert_called_once_with(mock_callable.call_args.args[0], fake_context)


@pytest.mark.parametrize(
    ("error", "expected_response"),
    [
        (CancelError("cancelled"), ResponseEnum.CANCEL),
        (DeferError("retry", delay_seconds=120), ResponseEnum.DEFER),
        (FailError("failed"), ResponseEnum.CANCEL),
        (RuntimeError("boom"), ResponseEnum.CANCEL),
    ],
)
def test_non_task_route_error(
    error, expected_response, non_task_client, event_payload, mock_callable
):
    mock_callable.side_effect = error

    result = non_task_client(mock_callable).post("/test/event", json=event_payload)

    assert result.json()["response"] == expected_response

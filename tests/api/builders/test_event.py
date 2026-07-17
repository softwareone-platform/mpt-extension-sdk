import base64
import json
from collections.abc import Callable
from unittest.mock import call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mpt_extension_sdk import routing
from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.auth import constants as auth_constants
from mpt_extension_sdk.api.builders import event as event_builder
from mpt_extension_sdk.api.models.events import ResponseEnum
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.errors import pipeline as pipeline_errors
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


@pytest.fixture
def mock_callable(mocker):
    return mocker.Mock(spec=Callable)


@pytest.fixture
def auth_token():
    claims = {
        auth_constants.CLAIM_ACCOUNT_ID: "ACC-001",
        auth_constants.CLAIM_ACCOUNT_TYPE: "Client",
        auth_constants.CLAIM_EXTENSION_ID: "EXT-001",
        auth_constants.CLAIM_MODULES: {"billing": ["edit"]},
        "exp": 4102444800,
    }
    payload = json.dumps(claims).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    return f"header.{encoded_payload}."


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


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
    return mocker.Mock(spec=BaseContext)


@pytest.fixture
def make_event_route():
    def factory(path, callback, *, delivery_mode):
        return routing.EventRouteDefinition(
            name=path,
            path=path,
            route_type=routing.RouteType.EVENT,
            callback=callback,
            event="OrderPurchased",
            delivery_mode=delivery_mode,
        )

    return factory


@pytest.fixture
def build_context_mock(mocker, fake_context):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.event.build_context",
        autospec=True,
        return_value=fake_context,
    )


@pytest.fixture
def business_attributes():
    return {"order.id": "ORD-001", "agreement.id": "AGR-001"}


@pytest.fixture
def get_business_attributes_mock(mocker, business_attributes):
    return mocker.patch(
        "mpt_extension_sdk.api.builders.event.get_business_attributes",
        autospec=True,
        return_value=business_attributes,
    )


@pytest.fixture
def set_attributes_mock(mocker):
    return mocker.patch("mpt_extension_sdk.api.builders.event.set_attributes", autospec=True)


@pytest.fixture
def record_exception_mock(mocker):
    return mocker.patch("mpt_extension_sdk.api.builders.event.record_exception", autospec=True)


@pytest.fixture
def set_event_context_mock(mocker):
    return mocker.patch("mpt_extension_sdk.api.builders.event.set_event_context", autospec=True)


@pytest.fixture
def event_span(mocker):
    return mocker.sentinel.span


@pytest.fixture
def start_event_span_mock(mocker, event_span):
    start_event_span = mocker.patch(
        "mpt_extension_sdk.api.builders.event.start_event_span", autospec=True
    )
    start_event_span.return_value.__enter__.return_value = event_span
    return start_event_span


@pytest.fixture
def task_client(
    build_context_mock,
    get_business_attributes_mock,
    set_attributes_mock,
    record_exception_mock,
    set_event_context_mock,
    start_event_span_mock,
    fake_task_service,
    app_instance,
    make_event_route,
):
    def factory(mock_callable):
        route = make_event_route(
            "/test/task", mock_callable, delivery_mode=routing.EventDeliveryMode.TASK
        )
        router = event_builder.create_task_event_route(route, app_instance)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[event_builder.get_tasks_service] = lambda: fake_task_service
        return TestClient(app, raise_server_exceptions=False)

    return factory


@pytest.fixture
def event_client(
    build_context_mock,
    get_business_attributes_mock,
    set_attributes_mock,
    record_exception_mock,
    set_event_context_mock,
    start_event_span_mock,
    app_instance,
    make_event_route,
):
    def factory(mock_callable):
        route = make_event_route(
            "/test/event", mock_callable, delivery_mode=routing.EventDeliveryMode.EVENT
        )
        router = event_builder.create_non_task_event_route(route, app_instance)
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    return factory


def test_create_event_route_dispatches_task(mock_callable, make_event_route):
    route = make_event_route(
        "/events/orders/purchase", mock_callable, delivery_mode=routing.EventDeliveryMode.TASK
    )

    result = event_builder.create_event_route(route, ExtensionApp())

    assert result.routes[0].name == "handle_task_event"


def test_create_event_route_dispatches_non_task(mock_callable, make_event_route):
    route = make_event_route(
        "/events/orders/purchase", mock_callable, delivery_mode=routing.EventDeliveryMode.EVENT
    )

    result = event_builder.create_event_route(route, ExtensionApp())

    assert result.routes[0].name == "handle_event"


def test_create_event_route(mock_callable, make_event_route):
    route = make_event_route(
        "/events/orders/purchase", mock_callable, delivery_mode=routing.EventDeliveryMode.EVENT
    )
    router = event_builder.create_non_task_event_route(route, ExtensionApp())

    result = router.routes

    assert len(result) == 1
    api_route = result[0]
    assert api_route.name == "handle_event"
    assert api_route.path == "/events/orders/purchase"
    assert api_route.methods == {"POST"}


def test_event_route_success(
    auth_headers,
    auth_token,
    fake_context,
    event_client,
    event_payload,
    mock_callable,
    build_context_mock,
    start_event_span_mock,
    set_attributes_mock,
    set_event_context_mock,
    event_span,
    business_attributes,
):
    result = event_client(mock_callable).post(
        "/test/event", json=event_payload, headers=auth_headers
    )

    response = result.json()
    assert response["response"] == ResponseEnum.OK
    mock_callable.assert_called_once_with(mock_callable.call_args.args[0], fake_context)
    auth = build_context_mock.call_args.kwargs["auth"]
    assert auth.token == auth_token
    assert auth.account.id == "ACC-001"
    start_event_span_mock.assert_called_once_with(
        "/test/event", task_based=False, event=mock_callable.call_args.args[0]
    )
    set_attributes_mock.assert_called_once_with(event_span, business_attributes)
    assert set_event_context_mock.call_args_list == [
        call(),
        call(order_id="ORD-001", agreement_id="AGR-001"),
    ]


@pytest.mark.parametrize(
    ("error", "expected_response"),
    [
        (pipeline_errors.CancelError("cancelled"), ResponseEnum.CANCEL),
        (pipeline_errors.DeferError("retry", delay_seconds=120), ResponseEnum.DEFER),
        (pipeline_errors.FailError("failed"), ResponseEnum.CANCEL),
        (RuntimeError("boom"), ResponseEnum.CANCEL),
    ],
)
def test_event_route_error(
    auth_headers,
    error,
    expected_response,
    event_client,
    event_payload,
    mock_callable,
    record_exception_mock,
    event_span,
):
    mock_callable.side_effect = error

    result = event_client(mock_callable).post(
        "/test/event", json=event_payload, headers=auth_headers
    )

    response = result.json()
    assert response["response"] == expected_response
    record_exception_mock.assert_called_once_with(event_span, error)


def test_event_route_authentication_error(
    build_context_mock, event_client, event_payload, mock_callable
):
    result = event_client(mock_callable).post("/test/event", json=event_payload)

    response = result.json()
    assert response["response"] == ResponseEnum.CANCEL
    build_context_mock.assert_not_called()
    mock_callable.assert_not_called()


def test_event_route_context_authentication_error(
    auth_headers, build_context_mock, event_client, event_payload, mock_callable
):
    build_context_mock.side_effect = AuthenticationError

    result = event_client(mock_callable).post(
        "/test/event", json=event_payload, headers=auth_headers
    )

    response = result.json()
    assert response.get("response") == ResponseEnum.CANCEL
    mock_callable.assert_not_called()


def test_create_task_event_route(mock_callable, make_event_route):
    route = make_event_route(
        "/events/orders/purchase", mock_callable, delivery_mode=routing.EventDeliveryMode.TASK
    )
    router = event_builder.create_task_event_route(route, ExtensionApp())

    result = router.routes

    assert len(result) == 1
    api_route = result[0]
    assert api_route.name == "handle_task_event"
    assert api_route.path == "/events/orders/purchase"
    assert api_route.methods == {"POST"}


def test_task_route_success(
    auth_headers,
    auth_token,
    task_client,
    task_event_payload,
    mock_callable,
    fake_task_service,
    fake_context,
    build_context_mock,
    start_event_span_mock,
    set_event_context_mock,
):
    result = task_client(mock_callable).post(
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    response = result.json()
    assert response["response"] == ResponseEnum.OK
    fake_task_service.start.assert_awaited_once()
    fake_task_service.complete.assert_awaited_once()
    fake_task_service.fail.assert_not_awaited()
    mock_callable.assert_called_once_with(mock_callable.call_args.args[0], fake_context)
    auth = build_context_mock.call_args.kwargs["auth"]
    assert auth.token == auth_token
    assert auth.account.id == "ACC-001"
    start_event_span_mock.assert_called_once_with(
        "/test/task", task_based=True, event=mock_callable.call_args.args[0]
    )
    assert set_event_context_mock.call_args_list == [
        call(task_id="TASK-001"),
        call(order_id="ORD-001", agreement_id="AGR-001"),
    ]


def test_task_route_authentication_error(
    build_context_mock, fake_task_service, task_client, task_event_payload, mock_callable
):
    result = task_client(mock_callable).post("/test/task", json=task_event_payload)

    response = result.json()
    assert response["response"] == ResponseEnum.CANCEL
    build_context_mock.assert_not_called()
    fake_task_service.start.assert_not_awaited()
    fake_task_service.fail.assert_not_awaited()
    mock_callable.assert_not_called()


def test_task_route_context_authentication_error(
    auth_headers,
    build_context_mock,
    fake_task_service,
    task_client,
    task_event_payload,
    mock_callable,
):
    build_context_mock.side_effect = AuthenticationError

    result = task_client(mock_callable).post(
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    response = result.json()
    assert response.get("response") == ResponseEnum.CANCEL
    fake_task_service.start.assert_not_awaited()
    fake_task_service.fail.assert_not_awaited()
    mock_callable.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected_response", "expected_task_action"),
    [
        (pipeline_errors.CancelError("not allowed"), ResponseEnum.CANCEL, "fail"),
        (
            pipeline_errors.DeferError("retry later", delay_seconds=60),
            ResponseEnum.DEFER,
            "reschedule",
        ),
        (pipeline_errors.FailError("processing failed"), ResponseEnum.CANCEL, "fail"),
        (RuntimeError("unexpected"), ResponseEnum.CANCEL, "fail"),
    ],
)
def test_task_route_error(
    auth_headers,
    error,
    expected_response,
    expected_task_action,
    fake_task_service,
    task_client,
    task_event_payload,
    mock_callable,
    record_exception_mock,
    event_span,
):
    mock_callable.side_effect = error

    result = task_client(mock_callable).post(
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    response = result.json()
    assert response["response"] == expected_response
    getattr(fake_task_service, expected_task_action).assert_awaited_once()
    fake_task_service.complete.assert_not_awaited()
    record_exception_mock.assert_called_once_with(event_span, error)


async def test_run_handler(mocker, fake_context, mock_callable):
    mock_callable = mocker.AsyncMock(spec=Callable, side_effect=mock_callable)

    await event_builder.run_handler(mock_callable, "evt", fake_context)  # act

    mock_callable.assert_awaited_once_with("evt", fake_context)


async def test_run_handler_supports_sync_handler(fake_context, mock_callable):
    await event_builder.run_handler(mock_callable, "evt", fake_context)  # act

    mock_callable.assert_called_once_with("evt", fake_context)


async def test_run_handler_propagates_async_exception(mocker, fake_context, mock_callable):
    mock_callable = mocker.AsyncMock(spec=Callable, side_effect=ValueError("async boom"))

    with pytest.raises(ValueError, match="async boom"):
        await event_builder.run_handler(mock_callable, "evt", fake_context)

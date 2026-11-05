from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mpt_extension_sdk import routing
from mpt_extension_sdk.api.auth import AuthenticationError
from mpt_extension_sdk.api.builders import event as event_builder
from mpt_extension_sdk.api.models.events import ResponseEnum
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.errors import pipeline as pipeline_errors
from mpt_extension_sdk.extension_app import ExtensionApp


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
        "task": {"id": "TSK-001"},
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
        "mpt_extension_sdk.pipeline.factory.RouteContextFactory.build",
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
    authenticate,
    build_context_mock,
    task_service,
    async_task_runner,
    app_instance,
    make_event_route,
):
    def factory(mock_callable):
        route = make_event_route(
            "/test/task", mock_callable, delivery_mode=routing.EventDeliveryMode.TASK
        )
        router = event_builder.create_task_event_route(route, app_instance)
        app = FastAPI()
        app.state.async_task_runner = async_task_runner
        app.include_router(router)
        app.dependency_overrides[event_builder.get_instance_id] = lambda: None
        app.dependency_overrides[event_builder.get_tasks_service] = lambda: task_service
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
    mocker,
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
    auth = build_context_mock.call_args.args[2]
    assert auth.token == auth_token
    assert auth.account.id == "ACC-1"
    start_event_span_mock.assert_called_once_with(
        "/test/event", task_based=False, event=mock_callable.call_args.args[0]
    )
    set_attributes_mock.assert_called_once_with(event_span, business_attributes)
    assert set_event_context_mock.call_args_list == [
        mocker.call(),
        mocker.call(order_id="ORD-001", agreement_id="AGR-001"),
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


def test_task_route_defers_queued_task(
    auth_headers, task_client, task_event_payload, mock_callable
):
    result = task_client(mock_callable).post(
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    assert result.json()["response"] == ResponseEnum.DEFER


def test_task_route_fetches_event_task(
    auth_headers, task_client, task_event_payload, mock_callable, task_service
):
    task_client(mock_callable).post(  # act
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    task_service.get.assert_awaited_once_with("TSK-001")


def test_task_route_submits_to_runner(
    auth_headers, task_client, task_event_payload, mock_callable, async_task_runner
):
    task_client(mock_callable).post(  # act
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    execution = async_task_runner.submit.call_args.kwargs["execution"]
    assert execution.task_id == "TSK-001"


def test_task_route_does_not_run_handler_inline(
    auth_headers, task_client, task_event_payload, mock_callable
):
    task_client(mock_callable).post(  # act
        "/test/task", json=task_event_payload, headers=auth_headers
    )

    mock_callable.assert_not_called()


def test_task_route_requires_task_event_body(
    auth_headers, task_client, event_payload, mock_callable
):
    result = task_client(mock_callable).post("/test/task", json=event_payload, headers=auth_headers)

    assert result.status_code == 422

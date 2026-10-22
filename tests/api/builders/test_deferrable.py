from http import HTTPStatus

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from mpt_extension_sdk.api import APIResponse, ForbiddenError
from mpt_extension_sdk.api.builders import deferrable as deferrable_builder
from mpt_extension_sdk.api.builders.dependencies import get_instance_id, get_tasks_service
from mpt_extension_sdk.api.builders.execution import APIRequestExecutor
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.routing import APIRouteDefinition, HTTPMethod, RouteType, only_deferrable


@pytest.fixture
def deferrable_route_factory():
    def factory(callback):
        return APIRouteDefinition(
            name="agreements-sync",
            path="/agreements/sync",
            route_type=RouteType.API,
            callback=callback,
            method=HTTPMethod.POST,
            deferrable=True,
        )

    return factory


@pytest.fixture
def deferrable_route(deferrable_route_factory):
    return deferrable_route_factory(lambda ctx: APIResponse.no_content())


@pytest.fixture
def only_deferrable_route(deferrable_route_factory):
    return deferrable_route_factory(only_deferrable(lambda ctx: None))


@pytest.fixture
def deferred_call_handler(mocker):
    handler_type = mocker.patch.object(deferrable_builder, "DeferredCallHandler", autospec=True)
    handler_type.return_value.execute.return_value = EventResponse.reschedule(60)
    return handler_type


@pytest.fixture
def deferrable_client_factory(
    api_route_dependencies,
    task_service,
    async_task_runner,
    api_service_type_factory,
    mock_api_service,
):
    def factory(route):
        extension_app = ExtensionApp(
            mpt_api_service_type=api_service_type_factory(mock_api_service)
        )
        app = FastAPI()
        app.state.async_task_runner = async_task_runner
        app.include_router(deferrable_builder.create_deferrable_route(route, extension_app))
        app.dependency_overrides[get_instance_id] = lambda: "EXI-1"
        app.dependency_overrides[get_tasks_service] = lambda: task_service
        return TestClient(app, raise_server_exceptions=False)

    return factory


@pytest.fixture
def deferrable_client(deferrable_client_factory, deferrable_route):
    return deferrable_client_factory(deferrable_route)


def test_direct_call_runs_request_executor(mocker, deferrable_client, deferred_call_handler):
    execute = mocker.patch.object(
        APIRequestExecutor,
        "execute",
        autospec=True,
        return_value=Response(content="created", status_code=HTTPStatus.CREATED),
    )

    result = deferrable_client.post("/agreements/sync")

    assert result.status_code == HTTPStatus.CREATED
    assert result.text == "created"
    execute.assert_awaited_once()
    deferred_call_handler.assert_not_called()


def test_direct_call_maps_auth_error(deferrable_client, deferred_call_handler):
    result = deferrable_client.post("/agreements/sync")  # act

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert result.headers["content-type"] == "application/problem+json"
    deferred_call_handler.assert_not_called()


def forbidden_handler(ctx):
    raise ForbiddenError("Only client accounts are supported")


def test_direct_call_maps_handler_error(
    auth_headers,
    deferrable_client_factory,
    deferrable_route_factory,
    deferred_call_handler,
):
    client = deferrable_client_factory(deferrable_route_factory(forbidden_handler))

    result = client.post("/agreements/sync", headers=auth_headers)

    assert result.status_code == HTTPStatus.FORBIDDEN
    assert result.json()["detail"] == "Only client accounts are supported"
    deferred_call_handler.assert_not_called()


def test_deferred_delivery_answers_event_response(
    mocker,
    deferrable_client,
    deferrable_route,
    deferred_call_handler,
    task_service,
    async_task_runner,
):
    result = deferrable_client.post("/agreements/sync", headers={"MPT-Task-Id": "TSK-001"})

    assert result.json() == {"response": "Delay", "cancelReason": None, "delay": 60}
    deferred_call_handler.assert_called_once_with(
        route=deferrable_route,
        context_factory=mocker.ANY,
        task_service=task_service,
        runner=async_task_runner,
        handler_logger=mocker.ANY,
        instance_id="EXI-1",
    )
    deferred_call_handler.return_value.execute.assert_awaited_once_with(
        request=mocker.ANY, task_id="TSK-001", delivery=None
    )


def test_deferred_delivery_sets_log_context(mocker, deferrable_client, deferred_call_handler):
    set_event_context = mocker.patch.object(deferrable_builder, "set_event_context", autospec=True)

    deferrable_client.post("/agreements/sync", headers={"MPT-Task-Id": "TSK-001"})  # act

    set_event_context.assert_called_once_with(task_id="TSK-001")


def test_only_deferrable_refuses_direct_call(
    mocker, deferrable_client_factory, only_deferrable_route, deferred_call_handler
):
    execute = mocker.patch.object(APIRequestExecutor, "execute", autospec=True)
    client = deferrable_client_factory(only_deferrable_route)

    result = client.post("/agreements/sync")

    assert result.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert result.headers["content-type"] == "application/problem+json"
    assert result.headers["allow"] == "POST"
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {
        "type": "about:blank",
        "status": HTTPStatus.METHOD_NOT_ALLOWED,
        "title": "Method not allowed",
        "detail": (
            "This endpoint only accepts a deferred call: send the request with the "
            "MPT-Async: true header"
        ),
        "instance": "/agreements/sync",
    }
    execute.assert_not_called()
    deferred_call_handler.assert_not_called()


def test_only_deferrable_runs_deferred_delivery(
    mocker, deferrable_client_factory, only_deferrable_route, deferred_call_handler
):
    client = deferrable_client_factory(only_deferrable_route)

    result = client.post("/agreements/sync", headers={"MPT-Task-Id": "TSK-001"})

    assert result.json() == {"response": "Delay", "cancelReason": None, "delay": 60}
    deferred_call_handler.return_value.execute.assert_awaited_once_with(
        request=mocker.ANY, task_id="TSK-001", delivery=None
    )

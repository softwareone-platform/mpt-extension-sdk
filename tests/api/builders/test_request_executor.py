from contextlib import nullcontext
from http import HTTPStatus
from typing import override

import pytest
from fastapi import Request, Response
from opentelemetry import trace

from mpt_extension_sdk.api.auth import AuthenticationError, RequestAuthenticationService
from mpt_extension_sdk.api.builders.errors import APIErrorResponseBuilder, RequestRejectedError
from mpt_extension_sdk.api.builders.request_executor import RouteRequestExecutor
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing import RouteType
from mpt_extension_sdk.routing.models import BaseRouteDefinition


class FakeRouteRequestExecutor(RouteRequestExecutor):
    @override
    async def _build_context(self, request, auth_context):
        return await self.context_factory.build(None, auth_context)

    @override
    async def _run(self, context, request, span):
        return self.route.callback(context)

    @override
    def _start_span(self, context, auth_context):
        return nullcontext(trace.INVALID_SPAN)


@pytest.fixture
def route(mocker):
    return BaseRouteDefinition(
        name="sync", path="/sync", route_type=RouteType.API, callback=mocker.Mock()
    )


@pytest.fixture
def executor(mocker, logger, route):
    return FakeRouteRequestExecutor(
        auth_service=mocker.create_autospec(RequestAuthenticationService, instance=True),
        context_factory=mocker.create_autospec(RouteContextFactory, instance=True),
        error_responses=APIErrorResponseBuilder(),
        handler_logger=logger,
        route=route,
    )


@pytest.fixture
def sync_request():
    return Request({"type": "http", "method": "POST", "path": "/sync", "headers": []})


async def test_execute_returns_handler_response(executor, route, sync_request):
    route.callback.return_value = Response(status_code=HTTPStatus.NO_CONTENT)

    result = await executor.execute(sync_request)

    assert result.status_code == HTTPStatus.NO_CONTENT


async def test_execute_rejects_unauthenticated(executor, sync_request, caplog):
    executor.auth_service.authenticate.side_effect = AuthenticationError("bad token")

    result = await executor.execute(sync_request)

    assert result.status_code == HTTPStatus.UNAUTHORIZED
    assert caplog.messages == ["Route sync authentication failed"]


async def test_execute_returns_rejected_response(executor, sync_request):
    response = Response(status_code=HTTPStatus.BAD_REQUEST)
    executor.context_factory.build.side_effect = RequestRejectedError(response)

    result = await executor.execute(sync_request)

    assert result is response


async def test_execute_answers_unexpected_error(executor, route, sync_request, caplog):
    route.callback.side_effect = ValueError("boom")

    result = await executor.execute(sync_request)

    assert result.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert caplog.messages == ["Unhandled api route error"]

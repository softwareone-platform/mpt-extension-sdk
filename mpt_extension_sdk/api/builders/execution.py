import logging
from contextlib import AbstractContextManager
from typing import override

from fastapi import Request, Response
from opentelemetry.trace import Span

from mpt_extension_sdk.api.auth import AuthContext, RequestAuthenticationService
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.errors import APIErrorResponseBuilder
from mpt_extension_sdk.api.builders.handlers import resolve_handler_result
from mpt_extension_sdk.api.builders.request_executor import RouteRequestExecutor
from mpt_extension_sdk.api.context import APIContext, AuthenticatedRequestContext
from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.responses import APIResponse
from mpt_extension_sdk.observability.tracing import (
    RouteSpanAttributes,
    record_exception,
    start_route_span,
)
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.pipeline.builders import APIContextBuilder
from mpt_extension_sdk.routing.models import APIRouteDefinition


class APIRequestExecutor(RouteRequestExecutor[APIContext, APIRouteDefinition]):
    """Execute an authenticated API request for a route definition."""

    def __init__(
        self,
        *,
        arguments_builder: APIHandlerArgumentsBuilder,
        auth_service: RequestAuthenticationService,
        context_factory: RouteContextFactory,
        handler_logger: logging.Logger,
        route: APIRouteDefinition,
    ) -> None:
        super().__init__(
            auth_service=auth_service,
            context_factory=context_factory,
            error_responses=APIErrorResponseBuilder(),
            handler_logger=handler_logger,
            route=route,
        )
        self.arguments_builder = arguments_builder

    @override
    async def _build_context(self, request: Request, auth_context: AuthContext) -> APIContext:
        return await self.context_factory.build(
            APIContextBuilder(
                handler_logger=self.handler_logger,
                request_context=AuthenticatedRequestContext.from_request(request),
            ),
            auth_context,
        )

    @override
    async def _run(self, context: APIContext, request: Request, span: Span) -> Response:
        try:
            response = await self._call_handler(context, request)
        except APIError as error:
            record_exception(span, error)
            return APIErrorResponseBuilder.build(error, instance=request.url.path)
        return response.to_http_response()

    @override
    def _start_span(
        self, context: APIContext, auth_context: AuthContext
    ) -> AbstractContextManager[Span]:
        method = self.route.method.value
        path = self.route.path
        return start_route_span(
            f"API {method} {path}",
            RouteSpanAttributes.from_route(self.route, auth_context, method=method),
        )

    async def _call_handler(self, context: APIContext, request: Request) -> APIResponse:
        request_body = await self.arguments_builder.parse_request_body(request)
        context.request = context.request.with_body(request_body)
        handler_arguments = await self.arguments_builder.build(request=request, context=context)
        response = await resolve_handler_result(self.route.callback(**handler_arguments))
        if not isinstance(response, APIResponse):
            raise TypeError("API handlers must return APIResponse")
        return response

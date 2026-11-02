import logging
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from fastapi import Request, Response
from opentelemetry.trace import Span, Status, StatusCode

from mpt_extension_sdk.api.auth import (
    AuthContext,
    AuthenticationError,
    RequestAuthenticationService,
)
from mpt_extension_sdk.api.builders.errors import RequestRejectedError, RouteErrorResponseBuilder
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.observability.tracing import record_exception
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing.models import BaseRouteDefinition


class RouteRequestExecutor[ContextT: BaseContext, RouteT: BaseRouteDefinition](ABC):
    """Run an authenticated HTTP request through the handler of a route."""

    def __init__(
        self,
        *,
        auth_service: RequestAuthenticationService,
        context_factory: RouteContextFactory,
        error_responses: RouteErrorResponseBuilder,
        handler_logger: logging.Logger,
        route: RouteT,
    ) -> None:
        self.auth_service = auth_service
        self.context_factory = context_factory
        self.error_responses = error_responses
        self.handler_logger = handler_logger
        self.route = route

    async def execute(self, request: Request) -> Response:
        """Execute the request and return the HTTP response of the route."""
        try:
            auth_context, context = await self._prepare(request)
        except AuthenticationError:
            self.handler_logger.warning("Route %s authentication failed", self.route.name)
            return self.error_responses.unauthorized(request)
        except RequestRejectedError as error:
            return error.response

        with self._start_span(context, auth_context) as span:
            try:
                return await self._run(context, request, span)
            except Exception as error:
                record_exception(span, error)
                span.set_status(Status(StatusCode.ERROR))
                self.handler_logger.exception("Unhandled %s route error", self.route.route_type)
                return self.error_responses.unexpected(request)

    async def _prepare(self, request: Request) -> tuple[AuthContext, ContextT]:
        auth_context = self.auth_service.authenticate(request)
        return auth_context, await self._build_context(request, auth_context)

    @abstractmethod
    async def _build_context(self, request: Request, auth_context: AuthContext) -> ContextT:
        """Build the handler context, raising `RequestRejectedError` to answer early."""
        raise NotImplementedError

    @abstractmethod
    async def _run(self, context: ContextT, request: Request, span: Span) -> Response:
        """Run the handler inside the route span and return its HTTP response."""
        raise NotImplementedError

    @abstractmethod
    def _start_span(
        self, context: ContextT, auth_context: AuthContext
    ) -> AbstractContextManager[Span]:
        """Start the route span of the request."""
        raise NotImplementedError

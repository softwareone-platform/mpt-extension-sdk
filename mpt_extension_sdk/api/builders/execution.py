import logging
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from fastapi import Request, Response, status
from opentelemetry.trace import Span

from mpt_extension_sdk.api.auth import AuthenticationError, RequestAuthenticationService
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.errors import APIErrorResponseBuilder
from mpt_extension_sdk.api.context import APIContext, AuthenticatedRequestContext
from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.responses import APIResponse
from mpt_extension_sdk.observability.tracing import record_exception, start_api_span
from mpt_extension_sdk.pipeline import build_api_context
from mpt_extension_sdk.runtime.logging import correlation_id_ctx

if TYPE_CHECKING:
    from mpt_extension_sdk.extension_app import ExtensionApp
    from mpt_extension_sdk.routing.models import APIRouteDefinition


class APIRequestExecutor:  # noqa: WPS214
    """Execute an authenticated API request for a route definition."""

    def __init__(
        self,
        *,
        arguments_builder: APIHandlerArgumentsBuilder,
        auth_service: RequestAuthenticationService,
        extension_app: "ExtensionApp",
        handler_logger: logging.Logger,
        route: "APIRouteDefinition",
    ) -> None:
        self._arguments_builder = arguments_builder
        self._auth_service = auth_service
        self._extension_app = extension_app
        self._handler_logger = handler_logger
        self._route = route

    async def execute(self, request: Request) -> Response:
        """Execute the API route request and return an HTTP response."""
        try:
            auth_context = self._auth_service.authenticate(request)
        except AuthenticationError:
            return self._build_api_error_response(
                APIError(status_code=status.HTTP_401_UNAUTHORIZED), request=request
            )

        request_context = AuthenticatedRequestContext.from_request(request)
        try:
            context = await build_api_context(
                auth_context=auth_context,
                request_context=request_context,
                handler_logger=self._handler_logger,
                mpt_api_service_type=self._extension_app.mpt_api_service_type,
            )
        except AuthenticationError:
            return self._build_api_error_response(
                APIError(status_code=status.HTTP_401_UNAUTHORIZED), request=request
            )

        with start_api_span(
            route_name=self._route.name,
            route_path=self._route.path,
            method=self._route.method.value,
            account_id=auth_context.account.id,
            extension_id=auth_context.extension_id,
            correlation_id=correlation_id_ctx.get(),
        ) as span:
            return await self._execute_in_span(context=context, request=request, span=span)

    def _build_api_error_response(
        self, error: APIError, *, request: Request, correlation_id: str | None = None
    ) -> Response:
        """Build an API error response."""
        return APIErrorResponseBuilder.build(
            error,
            instance=request.url.path,
            correlation_id=correlation_id,
        )

    async def _build_handler_arguments(
        self, *, context: APIContext, request: Request, span: Span
    ) -> tuple[dict[str, Any], Response | None]:
        """Build handler arguments or return the mapped API error response."""
        try:
            return await self._arguments_builder.build(request=request, context=context), None
        except APIError as error:
            return {}, self._record_api_error(error, request=request, span=span)

    async def _execute_handler(
        self, *, handler_arguments: dict[str, Any], request: Request, span: Span
    ) -> Response:
        """Run the extension handler and map handled or unhandled errors."""
        try:
            response = await self._run_api_handler(handler_arguments)
        except APIError as error:
            return self._record_api_error(error, request=request, span=span)
        except Exception as error:
            record_exception(span, error)
            self._handler_logger.exception("Unhandled API route error", exc_info=error)
            error_detail = (
                "An unexpected error occurred. Contact support with the correlation id below."
            )
            return self._build_api_error_response(
                APIError(
                    error_detail,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    title="Internal Server Error",
                ),
                request=request,
                correlation_id=correlation_id_ctx.get(),
            )
        return response.to_http_response()

    async def _execute_in_span(
        self, *, context: APIContext, request: Request, span: Span
    ) -> Response:
        """Run the authenticated API request inside the active route span."""
        error_response = await self._parse_body_into_context(
            context=context, request=request, span=span
        )
        if error_response is not None:
            return error_response

        handler_arguments, error_response = await self._build_handler_arguments(
            context=context, request=request, span=span
        )
        if error_response is not None:
            return error_response

        return await self._execute_handler(
            handler_arguments=handler_arguments, request=request, span=span
        )

    async def _parse_body_into_context(
        self, *, context: APIContext, request: Request, span: Span
    ) -> Response | None:
        """Parse request body into the API context."""
        try:
            request_body = await self._arguments_builder.parse_request_body(request)
        except APIError as error:
            return self._record_api_error(error, request=request, span=span)
        context.request = context.request.with_body(request_body)
        return None

    def _record_api_error(self, error: APIError, *, request: Request, span: Span) -> Response:
        """Record and map an API error."""
        record_exception(span, error)
        return self._build_api_error_response(error, request=request)

    async def _run_api_handler(self, kwargs: dict[str, Any]) -> APIResponse:
        """Invoke an API handler and return the resulting SDK response."""
        response = self._route.callback(**kwargs)
        if isawaitable(response):
            response = await response
        if not isinstance(response, APIResponse):
            raise TypeError("API handlers must return APIResponse")
        return response

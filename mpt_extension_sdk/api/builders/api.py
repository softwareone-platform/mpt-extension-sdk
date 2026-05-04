# flake8: noqa: WPS202
import logging
from dataclasses import replace
from http import HTTPStatus
from inspect import isawaitable
from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import Response

from mpt_extension_sdk.api.auth import (
    AuthContext,
    AuthenticatedRequestContext,
    RequestAuthenticationService,
)
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.errors import APIErrorResponseBuilder
from mpt_extension_sdk.api.builders.validation import APIRequestValidator
from mpt_extension_sdk.api.context import APIContext
from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.responses import APIResponse
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.observability.tracing import record_exception, start_api_span
from mpt_extension_sdk.pipeline import build_api_context
from mpt_extension_sdk.routing.models import APIRouteDefinition
from mpt_extension_sdk.runtime.logging import correlation_id_ctx
from mpt_extension_sdk.services.mpt_api_service import AccountScopedMPTAPIService

logger = logging.getLogger(__name__)


def create_api_route(route: APIRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router for an authenticated API route definition."""
    handler_logger = logging.getLogger(route.callback.__module__)
    auth_service = RequestAuthenticationService()
    arguments_builder = APIHandlerArgumentsBuilder(route)
    router = APIRouter()

    @router.api_route(route.path, methods=[route.method.value], name=route.name)
    async def handle_api_request(request: Request) -> Response:  # noqa: WPS210, WPS430
        logger.debug("Received API request: %s - %s ", request.url.path, request.__dict__)
        auth_context, error_response = authenticate_request(auth_service, request)
        if error_response is not None:
            return error_response
        if auth_context is None:
            return APIErrorResponseBuilder.build(
                APIError(status_code=HTTPStatus.UNAUTHORIZED), instance=request.url.path
            )

        request_context = AuthenticatedRequestContext.from_request(request)
        context = build_api_context(
            auth_context=auth_context,
            request_context=request_context,
            handler_logger=handler_logger,
            mpt_api_service_type=extension_app.mpt_api_service_type,
        )
        error_response = validate_request_context(auth_context, context, request)
        if error_response is not None:
            return error_response

        with start_api_span(
            route_name=route.name,
            route_path=route.path,
            method=route.method.value,
            account_id=context.auth.account.id,
            extension_id=context.auth.extension_id,
            correlation_id=correlation_id_ctx.get(),
        ) as span:
            return await handle_api_span_request(
                request=request,
                route=route,
                context=context,
                arguments_builder=arguments_builder,
                handler_logger=handler_logger,
                span=span,
            )

    return router


def authenticate_request(
    auth_service: RequestAuthenticationService, request: Request
) -> tuple[AuthContext | None, Response | None]:
    """Authenticate an API request or return the mapped API error response."""
    try:
        return auth_service.authenticate(request), None
    except APIError as error:
        return None, APIErrorResponseBuilder.build(error, instance=request.url.path)


def validate_request_context(
    auth_context: AuthContext, context: APIContext, request: Request
) -> Response | None:
    """Validate API request context invariants."""
    try:
        APIRequestValidator.assert_extension_id_matches(auth_context, context)
    except APIError as error:
        return APIErrorResponseBuilder.build(error, instance=request.url.path)
    return None


async def handle_api_span_request(  # noqa: WPS211
    *,
    request: Request,
    route: APIRouteDefinition,
    context: APIContext,
    arguments_builder: APIHandlerArgumentsBuilder,
    handler_logger: logging.Logger,
    span: Any,
) -> Response:
    """Run the authenticated API request inside the active route span."""
    error_response = await parse_body_into_context(arguments_builder, request, context, span)
    if error_response is not None:
        return error_response

    handler_arguments, error_response = await build_handler_arguments(
        arguments_builder, request, context, span
    )
    if error_response is not None:
        return error_response

    error_response = await refresh_api_service(context, request, span)
    if error_response is not None:
        return error_response

    return await run_api_handler_response(
        route=route,
        request=request,
        handler_arguments=handler_arguments,
        handler_logger=handler_logger,
        span=span,
    )


async def parse_body_into_context(
    arguments_builder: APIHandlerArgumentsBuilder,
    request: Request,
    context: APIContext,
    span: Any,
) -> Response | None:
    """Parse request body into the API context."""
    try:
        request_body = await arguments_builder.parse_request_body(request)
    except APIError as error:
        return record_api_error(span, error, request)
    context.request = replace(context.request, body=request_body)
    return None


async def build_handler_arguments(
    arguments_builder: APIHandlerArgumentsBuilder,
    request: Request,
    context: APIContext,
    span: Any,
) -> tuple[dict[str, Any], Response | None]:
    """Build handler arguments or return the mapped API error response."""
    try:
        return await arguments_builder.build(request=request, context=context), None
    except APIError as error:
        return {}, record_api_error(span, error, request)


async def refresh_api_service(context: APIContext, request: Request, span: Any) -> Response | None:
    """Refresh the account scoped API service."""
    api_service = cast(AccountScopedMPTAPIService, context.mpt_api_service)
    try:
        await api_service.refresh()
    except APIError as error:
        return record_api_error(span, error, request)
    return None


async def run_api_handler_response(  # noqa: WPS211
    *,
    route: APIRouteDefinition,
    request: Request,
    handler_arguments: dict[str, Any],
    handler_logger: logging.Logger,
    span: Any,
) -> Response:
    """Run the extension handler and map handled or unhandled errors."""
    try:
        response = await run_api_handler(route.callback, handler_arguments)
    except APIError as error:
        return record_api_error(span, error, request)
    except Exception as error:
        record_exception(span, error)
        handler_logger.exception("Unhandled API route error", exc_info=error)
        error_detail = (
            "An unexpected error occurred. Contact support with the correlation id below."
        )
        return APIErrorResponseBuilder.build(
            APIError(
                error_detail,
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                title="Internal Server Error",
            ),
            instance=request.url.path,
            correlation_id=correlation_id_ctx.get(),
        )
    return response.to_http_response(request_url=str(request.url))


def record_api_error(span: Any, error: APIError, request: Request) -> Response:
    """Record and map an API error."""
    record_exception(span, error)
    return APIErrorResponseBuilder.build(error, instance=request.url.path)


async def run_api_handler(route_handler: Any, kwargs: dict[str, Any]) -> APIResponse:
    """Invoke an API handler and return the resulting SDK response."""
    response = route_handler(**kwargs)
    if isawaitable(response):
        response = await response
    if not isinstance(response, APIResponse):
        raise TypeError("API handlers must return APIResponse")
    return response

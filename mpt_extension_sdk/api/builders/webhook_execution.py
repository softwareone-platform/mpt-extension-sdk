import logging
from contextlib import AbstractContextManager
from typing import Any, override

from fastapi import Request, Response
from opentelemetry.trace import Span

from mpt_extension_sdk.api.auth import AuthContext, RequestAuthenticationService
from mpt_extension_sdk.api.builders.errors import RequestRejectedError, WebhookErrorResponseBuilder
from mpt_extension_sdk.api.builders.handlers import resolve_handler_result
from mpt_extension_sdk.api.builders.request_executor import RouteRequestExecutor
from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.observability.tracing import (
    RouteSpanAttributes,
    record_exception,
    start_route_span,
)
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.pipeline.builders import WebhookContextBuilder
from mpt_extension_sdk.routing.models import WebhookRouteDefinition
from mpt_extension_sdk.webhooks import WebhookContext, WebhookError, WebhookResponse


class WebhookRequestExecutor(RouteRequestExecutor[WebhookContext, WebhookRouteDefinition]):
    """Execute a synchronous webhook call for a route definition."""

    def __init__(
        self,
        *,
        auth_service: RequestAuthenticationService,
        context_factory: RouteContextFactory,
        extension_app: ExtensionApp,
        handler_logger: logging.Logger,
        route: WebhookRouteDefinition,
    ) -> None:
        super().__init__(
            auth_service=auth_service,
            context_factory=context_factory,
            error_responses=WebhookErrorResponseBuilder(),
            handler_logger=handler_logger,
            route=route,
        )
        self.extension_app = extension_app

    @override
    async def _build_context(self, request: Request, auth_context: AuthContext) -> WebhookContext:
        payload = await self._read_payload(request)
        try:
            return await self.context_factory.build(
                WebhookContextBuilder(
                    handler_logger=self.handler_logger,
                    payload=payload,
                    request_context=AuthenticatedRequestContext.from_request(request, body=payload),
                    webhook_type=self.route.webhook_type,
                ),
                auth_context,
            )
        except WebhookError as error:
            raise RequestRejectedError(WebhookErrorResponseBuilder.build(error))

    @override
    async def _run(self, context: WebhookContext, request: Request, span: Span) -> Response:
        try:
            webhook_response = await self._call_handler(context)
        except WebhookError as error:
            record_exception(span, error)
            self.handler_logger.info(
                "Webhook %s answered an error: %s", self.route.webhook_type, error
            )
            return WebhookErrorResponseBuilder.build(error)
        if not isinstance(webhook_response, WebhookResponse):
            raise TypeError("Webhook handlers must return WebhookResponse")
        return webhook_response.to_http_response()

    @override
    def _start_span(
        self, context: WebhookContext, auth_context: AuthContext
    ) -> AbstractContextManager[Span]:
        webhook_type = self.route.webhook_type
        return start_route_span(
            f"Webhook {webhook_type}",
            RouteSpanAttributes.from_route(self.route, auth_context),
        )

    async def _call_handler(self, context: WebhookContext) -> object:
        handler_context = self.extension_app.build_context(self.route, context)
        return await resolve_handler_result(self.route.callback(handler_context))

    async def _read_payload(self, request: Request) -> dict[str, Any]:
        try:
            payload = await request.json()
        except ValueError:
            raise self._request_reject_error("The webhook body is not valid JSON")
        if not isinstance(payload, dict):
            raise self._request_reject_error("The webhook body must be a JSON object")
        return payload

    def _request_reject_error(self, message: str) -> RequestRejectedError:
        return RequestRejectedError(WebhookErrorResponseBuilder.invalid_payload(message))

import logging

from fastapi import APIRouter, Request, Response

from mpt_extension_sdk.api.auth import RequestAuthenticationService
from mpt_extension_sdk.api.builders.webhook_execution import WebhookRequestExecutor
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing.models import WebhookRouteDefinition


def create_webhook_route(route: WebhookRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router for a webhook route definition."""
    executor = WebhookRequestExecutor(
        auth_service=RequestAuthenticationService(),
        context_factory=RouteContextFactory(extension_app.mpt_api_service_type),
        handler_logger=logging.getLogger(route.callback.__module__),
        route=route,
    )
    router = APIRouter()

    @router.post(route.path, name=route.name)
    async def handle_webhook(request: Request) -> Response:  # noqa: WPS430
        return await executor.execute(request)

    return router

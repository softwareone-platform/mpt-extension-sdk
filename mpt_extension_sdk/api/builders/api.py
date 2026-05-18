import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from mpt_extension_sdk.api.auth import RequestAuthenticationService
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.execution import APIRequestExecutor
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.routing.models import APIRouteDefinition

logger = logging.getLogger(__name__)


def create_api_route(route: APIRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router for an authenticated API route definition."""
    executor = APIRequestExecutor(
        arguments_builder=APIHandlerArgumentsBuilder(route),
        auth_service=RequestAuthenticationService(),
        extension_app=extension_app,
        handler_logger=logging.getLogger(route.callback.__module__),
        route=route,
    )
    router = APIRouter()

    @router.api_route(route.path, methods=[route.method.value], name=route.name)
    async def handle_api_request(request: Request) -> Response:  # noqa: WPS430
        logger.debug("Received API request: %s %s", request.method, request.url.path)
        return await executor.execute(request)

    return router

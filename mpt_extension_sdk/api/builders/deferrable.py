import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, Response

from mpt_extension_sdk.api.auth import RequestAuthenticationService
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.deferred_delivery import DeferredCallHandler
from mpt_extension_sdk.api.builders.dependencies import get_tasks_service
from mpt_extension_sdk.api.builders.execution import APIRequestExecutor
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing.models import APIRouteDefinition
from mpt_extension_sdk.runtime.logging import set_event_context
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

logger = logging.getLogger(__name__)


def create_deferrable_route(route: APIRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router that serves a direct call or a deferred delivery.

    A request without the `MPT-Task-Id` header runs as a direct API call. A request
    with it is a deferred delivery of that platform task, answered with an
    `EventResponse`.
    """
    handler_logger = logging.getLogger(route.callback.__module__)
    executor = APIRequestExecutor(
        arguments_builder=APIHandlerArgumentsBuilder(route),
        auth_service=RequestAuthenticationService(),
        extension_app=extension_app,
        handler_logger=handler_logger,
        route=route,
    )
    router = APIRouter()

    @router.api_route(route.path, methods=[route.method.value], name=route.name)
    async def handle_deferrable_request(  # noqa: WPS430
        request: Request,
        task_service: Annotated[TaskService, Depends(get_tasks_service)],
        task_id: Annotated[str | None, Header(alias="MPT-Task-Id")] = None,
    ) -> Response:
        if not task_id:
            logger.debug("Received API request: %s %s", request.method, request.url.path)
            return await executor.execute(request)

        set_event_context(task_id=task_id)
        handler_logger.info(
            "Received deferred call task (%s): %s %s", task_id, request.method, request.url.path
        )
        event_response = await DeferredCallHandler(
            route=route,
            context_factory=RouteContextFactory.from_service_type(
                extension_app.mpt_api_service_type
            ),
            task_service=task_service,
            runner=request.app.state.async_task_runner,
            handler_logger=handler_logger,
        ).execute(request=request, task_id=task_id, delivery=None)
        return JSONResponse(content=event_response.model_dump(mode="json"))

    return router

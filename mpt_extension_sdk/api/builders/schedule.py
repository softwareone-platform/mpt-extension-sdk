import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from mpt_extension_sdk.api.builders.dependencies import get_tasks_service
from mpt_extension_sdk.api.builders.schedule_executor import ScheduleTaskExecutor
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.routing import ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskRunner
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


def create_schedule_route(route: ScheduleRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router for a schedule route definition."""
    router = APIRouter()
    handler_logger = logging.getLogger(route.callback.__module__)

    @router.post(route.path, status_code=status.HTTP_200_OK, response_model=EventResponse)
    async def handle_schedule_task(  # noqa: WPS430
        request: Request,
        task_id: Annotated[str, Header(alias="MPT-Task-Id")],
        task_service: Annotated[TaskService, Depends(get_tasks_service)],
    ) -> EventResponse:
        handler_logger.info(
            "Received schedule task (%s): %s",
            task_id,
            request.headers.get("x-envoy-original-path", request.url.path),
        )
        runner: AsyncTaskRunner = request.app.state.async_task_runner
        return await ScheduleTaskExecutor(
            route=route,
            extension_app=extension_app,
            task_service=task_service,
            runner=runner,
            handler_logger=handler_logger,
        ).execute(request=request, task_id=task_id)

    return router

import logging
from typing import override

from fastapi import Request

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.builders.task_delivery import TaskEventDeliveryHandler, TaskHandlerType
from mpt_extension_sdk.api.models.events import TaskEvent
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.pipeline.builders import ScheduleContextBuilder
from mpt_extension_sdk.routing import ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler, AsyncTaskRunner
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


class ScheduleDeliveryHandler(TaskEventDeliveryHandler):
    """Answer schedule deliveries."""

    def __init__(  # noqa: WPS211
        self,
        *,
        route: ScheduleRouteDefinition,
        context_factory: RouteContextFactory,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
        instance_id: str | None = None,
    ) -> None:
        super().__init__(
            handler_type=TaskHandlerType.SCHEDULE,
            task_service=task_service,
            runner=runner,
            handler_logger=handler_logger,
            instance_id=instance_id,
        )
        self.route = route
        self.context_factory = context_factory

    @override
    async def build_callback(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: TaskEvent
    ) -> AsyncTaskHandler:
        """Return a call to the schedule handler with its schedule context."""
        context = await self.context_factory.build(
            ScheduleContextBuilder(
                event=delivery,
                handler_logger=self.handler_logger,
                schedule_id=self.route.id,
                task_id=task.id,
                task_service=self.task_service,
            ),
            auth,
        )
        return lambda: self.route.callback(context)

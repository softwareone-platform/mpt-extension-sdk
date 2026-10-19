import datetime as dt
import logging
from typing import override

from fastapi import Request

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.builders.task_delivery import TaskDeliveryHandler, TaskHandlerType
from mpt_extension_sdk.api.builders.task_timing import (
    EVENT_RETENTION_SECONDS,
    TASK_TIMEOUT_SAFETY_MARGIN,
)
from mpt_extension_sdk.api.models.events import EventResponse, TaskEvent
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.routing import ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler, AsyncTaskRunner
from mpt_extension_sdk.runtime.logging import set_event_context
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


class ScheduleDeliveryHandler(TaskDeliveryHandler[TaskEvent]):
    """Answer schedule deliveries."""

    def __init__(
        self,
        *,
        route: ScheduleRouteDefinition,
        extension_app: ExtensionApp,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
    ) -> None:
        super().__init__(
            handler_type=TaskHandlerType.SCHEDULE,
            task_service=task_service,
            runner=runner,
            handler_logger=handler_logger,
        )
        self.route = route
        self.extension_app = extension_app

    @override
    async def build_callback(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: TaskEvent
    ) -> AsyncTaskHandler:
        """Return a call to the schedule handler with its schedule context."""
        factory = RouteContextFactory.from_service_type(self.extension_app.mpt_api_service_type)
        context = await factory.build_schedule_context(
            schedule_id=self.route.id,
            task_id=task.id,
            handler_logger=self.handler_logger,
            auth=auth,
            task_service=self.task_service,
            event=delivery,
        )
        return lambda: self.route.callback(context)

    @override
    async def execute(
        self, *, request: Request, task_id: str, delivery: TaskEvent
    ) -> EventResponse:
        """Answer a schedule delivery with its event in the logging context."""
        set_event_context(task_id=task_id, event_id=delivery.id)
        return await super().execute(request=request, task_id=task_id, delivery=delivery)

    @override
    def watchdog_delay(self, task: Task, delivery: TaskEvent) -> int:
        """Return the watchdog delay, capped so the redelivery stays within the event retention."""
        retained = (dt.datetime.now(dt.UTC) - delivery.details.enqueue_time).total_seconds()
        schedulable = EVENT_RETENTION_SECONDS - retained - TASK_TIMEOUT_SAFETY_MARGIN
        delay = min(super().watchdog_delay(task, delivery), schedulable)
        return max(int(delay), 1)

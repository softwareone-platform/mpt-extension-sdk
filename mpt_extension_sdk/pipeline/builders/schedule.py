import logging
from typing import override

from mpt_extension_sdk.api.models.events import TaskEvent
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.pipeline.context.schedule import ScheduleContext, ScheduleMetadata
from mpt_extension_sdk.runtime.logging import correlation_id_ctx
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.tasks import TaskHandle


class ScheduleContextBuilder(ContextBuilder[ScheduleContext]):
    """Build the execution context of a schedule task."""

    def __init__(  # noqa: WPS211
        self,
        *,
        event: TaskEvent,
        handler_logger: logging.Logger,
        schedule_id: str,
        task_id: str,
        task_service: TaskService,
    ) -> None:
        self.event = event
        self.handler_logger = handler_logger
        self.schedule_id = schedule_id
        self.task_id = task_id
        self.task_service = task_service

    @override
    async def build(self, resources: ContextResources) -> ScheduleContext:
        """Build the schedule context with its platform task."""
        return ScheduleContext(
            logger=self.handler_logger,
            meta=ScheduleMetadata(
                enqueue_time=self.event.details.enqueue_time,
                event_id=self.event.id,
                schedule_id=self.schedule_id,
                task_id=self.task_id,
                correlation_id=correlation_id_ctx.get(),
            ),
            task=TaskHandle(id=self.task_id, task_service=self.task_service),
            **resources.base_fields(),
        )

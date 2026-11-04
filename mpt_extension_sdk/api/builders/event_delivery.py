import logging
from typing import override

from fastapi import Request

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.builders.handlers import resolve_handler_result
from mpt_extension_sdk.api.builders.task_delivery import TaskEventDeliveryHandler, TaskHandlerType
from mpt_extension_sdk.api.models.events import TaskEvent
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.observability.tracing import (
    get_business_attributes,
    record_exception,
    set_attributes,
    start_event_span,
)
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.pipeline.builders import EventContextBuilder
from mpt_extension_sdk.routing import EventRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler, AsyncTaskRunner
from mpt_extension_sdk.runtime.logging import set_event_context
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


class EventDeliveryHandler(TaskEventDeliveryHandler):
    """Answer task-based event deliveries."""

    def __init__(  # noqa: WPS211
        self,
        *,
        route: EventRouteDefinition,
        extension_app: ExtensionApp,
        context_factory: RouteContextFactory,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
        instance_id: str | None = None,
    ) -> None:
        super().__init__(
            handler_type=TaskHandlerType.EVENT,
            task_service=task_service,
            runner=runner,
            handler_logger=handler_logger,
            instance_id=instance_id,
        )
        self.route = route
        self.extension_app = extension_app
        self.context_factory = context_factory

    @override
    async def build_callback(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: TaskEvent
    ) -> AsyncTaskHandler:
        """Return a traced call to the event handler with its route context."""
        context = await self.context_factory.build(
            EventContextBuilder(event=delivery, handler_logger=self.handler_logger), auth
        )
        context = self.extension_app.build_context(self.route, context)

        async def run_task_event_handler() -> None:  # noqa: WPS430
            with start_event_span(self.route.path, task_based=True, event=delivery) as span:
                business_attributes = get_business_attributes(context)
                set_event_context(
                    event_id=delivery.id,
                    task_id=task.id,
                    order_id=str(business_attributes.get("order.id", "")),
                    agreement_id=str(business_attributes.get("agreement.id", "")),
                )
                set_attributes(span, business_attributes)
                try:
                    await resolve_handler_result(self.route.callback(delivery, context))
                except Exception as error:
                    record_exception(span, error)
                    raise

        return run_task_event_handler

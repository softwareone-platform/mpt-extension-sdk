import logging
from typing import override

from mpt_extension_sdk.api.models.events import Event, EventObjectType
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import EventBaseContext, EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx


class EventContextBuilder(ContextBuilder[EventBaseContext]):
    """Build the fully hydrated execution context of an incoming event."""

    def __init__(self, *, event: Event, handler_logger: logging.Logger) -> None:
        self.event = event
        self.handler_logger = handler_logger

    @override
    async def build(self, resources: ContextResources) -> EventBaseContext:
        """Build the order or agreement context of the event object."""
        object_id = self.event.object.id
        object_type = self.event.object.object_type
        if object_type == EventObjectType.ORDER:
            return OrderContext(
                logger=self.handler_logger,
                meta=self._metadata(),
                order=await resources.mpt_api_service.orders.get_by_id(object_id),
                **resources.base_fields(),
            )

        if object_type == EventObjectType.AGREEMENT:
            return AgreementContext(
                agreement=await resources.mpt_api_service.agreements.get_by_id(object_id),
                logger=self.handler_logger,
                meta=self._metadata(),
                **resources.base_fields(),
            )

        raise RuntimeError(f"Unsupported context type: {object_type}")

    def _metadata(self) -> EventMetadata:
        return EventMetadata(
            event_id=self.event.id,
            object_id=self.event.object.id,
            object_type=self.event.object.object_type,
            correlation_id=correlation_id_ctx.get(),
            task_id=task_id_ctx.get(),
        )

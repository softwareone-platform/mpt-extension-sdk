import logging

from mock_app.context import MockContext
from mock_app.pipelines import PurchasePipeline
from mpt_extension_sdk.api.models.events import Event, TaskEvent
from mpt_extension_sdk.routing import EventRouter

logger = logging.getLogger(__name__)
orders_router = EventRouter(prefix="/events/orders")


@orders_router.event(
    path="/purchase",
    name="orders-purchase",
    event="platform.commerce.order.status_changed",
    condition="and(eq(status,Processing),eq(product.id,PRD-5516-5707))",
    context_adapter_type=MockContext,
)
async def handle_purchase_order(event: Event, context: MockContext) -> None:
    """Handle purchase order event."""
    logger.info("Processing purchase order id=%s object_id=%s", event.id, event.object.id)
    await PurchasePipeline().execute(context)


@orders_router.task(
    path="/change",
    name="orders-change",
    event="platform.commerce.order.created",
    condition="eq(product.id,PRD-5516-5707)",
    context_adapter_type=MockContext,
)
async def handle_order_change(event: TaskEvent, context: MockContext) -> None:
    """Handle a task-based order event.

    The SDK claims the platform task, runs this handler on its async task runner and
    answers the delivery with Defer until the task is final, so the handler can take
    longer than the delivery request allows.
    """
    logger.info(
        "Processing order change id=%s object_id=%s task_id=%s",
        event.id,
        event.object.id,
        context.meta.task_id,
    )
    await PurchasePipeline().execute(context)

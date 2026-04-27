import logging

from mock_app.context import MockContext
from mock_app.pipelines import PurchasePipeline
from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.api.models.events import Event

logger = logging.getLogger(__name__)
orders_router = EventRouter(prefix="/events/orders")


@orders_router.event(
    path="/purchase",
    name="orders-purchase",
    event="platform.commerce.order.created",
    condition="eq(product.id,PRD-5516-5707)",
    context_adapter_type=MockContext,
)
async def handle_purchase_order(event: Event, context: MockContext) -> None:
    """Handle purchase order event."""
    logger.info("Processing purchase order id=%s object_id=%s", event.id, event.object.id)
    await PurchasePipeline().execute(context)

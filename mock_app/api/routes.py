import logging

from mock_app.api.pipelines import PurchasePipeline
from mpt_extension_sdk import ExtensionRouter
from mpt_extension_sdk.api.models.events import Event
from mpt_extension_sdk.pipeline import OrderContext

logger = logging.getLogger(__name__)
orders_router = ExtensionRouter(prefix="/events/orders")


@orders_router.route(
    "/purchase",
    name="orders-purchase",
    event="platform.commerce.order.created",
    condition="eq(product.id,PRD-5516-5707)",
)
async def handle_purchase_order(event: Event, context: OrderContext) -> None:
    """Handle purchase order event."""
    logger.info("Processing purchase order id=%s object_id=%s", event.id, event.object.id)

    await PurchasePipeline().execute(context)

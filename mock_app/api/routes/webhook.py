from mpt_extension_sdk import WebhookRouter
from mpt_extension_sdk.webhooks import OrderWebhookContext, WebhookResponse, WebhookType

VALID_ACCOUNT_TYPES = frozenset(("NewAccount", "ExistingAccount"))

webhooks_router = WebhookRouter(prefix="/webhooks")


@webhooks_router.webhook(
    "/orders/validate",
    type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
    description="Validate purchase orders in Draft status",
    criteria=[{"product.id": "PRD-5516-5707"}, {"product.id": "PRD-5516-5708"}],
)
def validate_purchase_order_draft(ctx: OrderWebhookContext) -> WebhookResponse:
    """Validate the account type of a draft purchase order."""
    order = ctx.order.without_errors()
    account_type = order.parameters.get_ordering_value("accountType")
    if isinstance(account_type, str) and account_type in VALID_ACCOUNT_TYPES:
        return WebhookResponse.ok(order)

    return WebhookResponse.ok(
        order.with_ordering_error(
            "accountType",
            {"id": "MOCK001", "message": f"Invalid account type: {account_type}"},
        )
    )

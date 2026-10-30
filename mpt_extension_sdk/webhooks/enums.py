from enum import StrEnum
from types import MappingProxyType
from typing import Self

from mpt_extension_sdk.models.status import CaseInsensitiveStrEnum


class WebhookObjectType(StrEnum):
    """Platform object types a webhook call can carry."""

    ACCOUNT = "Account"
    ORDER = "Order"
    REQUEST = "Request"


class WebhookType(CaseInsensitiveStrEnum):
    """Platform webhook types known by the SDK.

    Routes also accept a plain string, so a type the platform adds later can be
    used before the SDK knows it.
    """

    SELECT_ORDER_LINES = "selectOrderLines"
    VALIDATE_ACCOUNT = "validateAccount"
    VALIDATE_CHANGE_ORDER_DRAFT = "validateChangeOrderDraft"
    VALIDATE_PURCHASE_ORDER_DRAFT = "validatePurchaseOrderDraft"
    VALIDATE_PURCHASE_ORDER_QUERYING = "validatePurchaseOrderQuerying"
    VALIDATE_REQUEST = "validateRequest"
    VALIDATE_TERMINATE_ORDER = "validateTerminateOrder"

    @property
    def object_type(self) -> WebhookObjectType:
        """The platform object type carried by this webhook type."""
        return WEBHOOK_OBJECT_TYPES[self]

    @classmethod
    def resolve(cls, webhook_type: "WebhookType | str") -> "Self | str":
        """Return the known webhook type, or the stripped string when it is unknown."""
        try:
            return cls(webhook_type)
        except ValueError:
            return webhook_type.strip()


WEBHOOK_OBJECT_TYPES = MappingProxyType({
    WebhookType.SELECT_ORDER_LINES: WebhookObjectType.ORDER,
    WebhookType.VALIDATE_ACCOUNT: WebhookObjectType.ACCOUNT,
    WebhookType.VALIDATE_CHANGE_ORDER_DRAFT: WebhookObjectType.ORDER,
    WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT: WebhookObjectType.ORDER,
    WebhookType.VALIDATE_PURCHASE_ORDER_QUERYING: WebhookObjectType.ORDER,
    WebhookType.VALIDATE_REQUEST: WebhookObjectType.REQUEST,
    WebhookType.VALIDATE_TERMINATE_ORDER: WebhookObjectType.ORDER,
})

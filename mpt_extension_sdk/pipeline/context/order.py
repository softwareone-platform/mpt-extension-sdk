from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mpt_extension_sdk.models import Order
from mpt_extension_sdk.pipeline.context.event import EventBaseContext


class OrderStatusActionType(StrEnum):
    """Supported order transitions requested by business logic."""

    FAIL = "Failed"
    QUERY = "Querying"


@dataclass(frozen=True)
class OrderStatusAction:
    """Structured order transition intent declared by business logic."""

    target_status: OrderStatusActionType
    message: str
    status_notes: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)  # noqa: WPS110


@dataclass
class OrderState:
    """Mutable order state transition data shared across pipeline steps."""

    action: OrderStatusAction | None = None
    handled: bool = False


@dataclass(kw_only=True)
class OrderContext(EventBaseContext):
    """Execution context specialized for order events."""

    order: Order
    order_state: OrderState = field(default_factory=OrderState)

    @property
    def order_id(self) -> str:
        """Order ID."""
        return self.order.id

    async def refresh_order(self) -> None:
        """Reload the current order from Marketplace."""
        self.order = await self.mpt_api_service.orders.get_by_id(self.order_id)

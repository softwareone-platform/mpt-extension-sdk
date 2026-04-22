from collections.abc import Mapping
from typing import Any

from mpt_extension_sdk.models import Subscription
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class SubscriptionService(BaseService[Subscription]):
    """Subscription service."""

    async def create(self, subscription: Mapping[str, Any] | BaseModel) -> Subscription:
        """Create a subscription."""
        return Subscription.from_payload(
            await self._client.commerce.subscriptions.create(
                self._serialize_attributes(subscription)
            )
        )

    async def create_order_subscription(
        self, order_id: str, subscription: Mapping[str, Any] | BaseModel
    ) -> Subscription:
        """Create a subscription inside an order."""
        return Subscription.from_payload(
            await self._client.commerce.orders.subscriptions(order_id).create(
                self._serialize_attributes(subscription)
            )
        )

    async def get_by_id(self, subscription_id: str) -> Subscription:
        """Fetch a subscription by ID."""
        return Subscription.from_payload(
            await self._client.commerce.subscriptions.get(subscription_id)
        )

    async def update(self, subscription_id: str, attributes: Mapping[str, Any] | BaseModel) -> None:
        """Update a subscription."""
        await self._client.commerce.subscriptions.update(
            subscription_id, self._serialize_attributes(attributes)
        )

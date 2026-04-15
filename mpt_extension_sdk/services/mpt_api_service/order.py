import logging
from collections.abc import Mapping
from typing import Any

from mpt_extension_sdk.models import Order
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.mpt_api_service.base import BaseService

logger = logging.getLogger(__name__)


class OrderService(BaseService[Order]):
    """Order service."""

    async def get_by_id(self, order_id: str) -> Order:
        """Fetch an order from Marketplace API."""
        order = await self._client.commerce.orders.get(
            order_id,
            select=[
                "agreement",
                "agreement.authorizations",
                "agreement.client",
                "agreement.licensee",
                "agreement.lines",
                "agreement.parameters",
                "assets",
                "authorization",
                "externalIds",
                "lines",
                "lines.asset",
                "lines.subscription",
                "parameters",
                "product",
                "seller",
                "subscriptions",
                "template",
            ],
        )
        logger.debug("Fetched order %s: %s", order_id, order.to_dict())
        return Order.from_payload(order)

    async def complete(
        self,
        order_id: str,
        template: Mapping[str, Any] | BaseModel,
        attributes: Mapping[str, Any] | BaseModel | None = None,
    ) -> None:
        """Complete an order with a template and optional attributes."""
        payload = {} if attributes is None else self._serialize_attributes(attributes)
        payload["template"] = self._serialize_attributes(template)
        await self._client.commerce.orders.complete(order_id, payload)

    async def update(self, order_id: str, attributes: Mapping[str, Any] | BaseModel) -> None:
        """Update an order."""
        await self._client.commerce.orders.update(order_id, self._serialize_attributes(attributes))

    async def query(self, order_id: str, attributes: Mapping[str, Any] | BaseModel) -> None:
        """Switch an order to query with explicit attributes."""
        await self._client.commerce.orders.query(order_id, self._serialize_attributes(attributes))

    async def fail(
        self,
        order_id: str,
        status_notes: dict[str, Any],
        attributes: Mapping[str, Any] | BaseModel | None = None,
    ) -> None:
        """Fail an order with status notes."""
        payload = {} if attributes is None else self._serialize_attributes(attributes)
        payload["statusNotes"] = status_notes
        await self._client.commerce.orders.fail(order_id, payload)

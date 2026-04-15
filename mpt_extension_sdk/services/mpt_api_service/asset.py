from collections.abc import Mapping
from typing import Any

from mpt_extension_sdk.models import Asset
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class AssetService(BaseService[Asset]):
    """Asset service."""

    async def create(self, asset: Mapping[str, Any] | BaseModel) -> Asset:
        """Create an asset."""
        return Asset.from_payload(
            await self._client.commerce.assets.create(self._serialize_attributes(asset))
        )

    async def create_order_asset(
        self, order_id: str, asset: Mapping[str, Any] | BaseModel
    ) -> Asset:
        """Create an asset inside an order."""
        return Asset.from_payload(
            await self._client.commerce.orders.assets(order_id).create(
                self._serialize_attributes(asset)
            )
        )

    async def get_by_id(self, asset_id: str) -> Asset:
        """Fetch an asset by ID."""
        return Asset.from_payload(await self._client.commerce.assets.get(asset_id))

    async def update(self, asset_id: str, attributes: Mapping[str, Any] | BaseModel) -> Asset:
        """Update an asset."""
        return Asset.from_payload(
            await self._client.commerce.assets.update(
                asset_id, self._serialize_attributes(attributes)
            )
        )

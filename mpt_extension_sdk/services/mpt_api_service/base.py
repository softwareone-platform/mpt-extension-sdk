from collections.abc import Mapping
from typing import Any

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient


class BaseService[Model: BaseModel]:
    """Base service class for all services."""

    _batch_size = 100

    def __init__(self, client: AsyncMPTClient) -> None:
        """Initialize service with an MPT client."""
        self._client = client

    def _serialize_attributes(self, attributes: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
        """Serialize update or create attributes for the Marketplace client."""
        if isinstance(attributes, BaseModel):
            return attributes.to_dict()
        return dict(attributes)

    async def _iterate_all(
        self, collection: Any, model: type[Model], batch_size: int | None = None
    ) -> list[Model]:
        """Collect all resources from an iterable collection query."""
        effective_batch_size = self._batch_size if batch_size is None else batch_size
        return [
            model.from_payload(element)
            async for element in collection.iterate(batch_size=effective_batch_size)
        ]

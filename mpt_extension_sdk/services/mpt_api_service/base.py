from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient


@dataclass(frozen=True)
class PaginatedCollection[Model: BaseModel]:
    """Paginated collection returned by Marketplace services."""

    limit: int
    offset: int
    resources: list[Model]
    total: int


class BaseService[Model: BaseModel]:
    """Base service class for all services."""

    def __init__(self, client: AsyncMPTClient) -> None:
        """Initialize service with an MPT client."""
        self._client = client

    def _serialize_attributes(self, attributes: Mapping[str, Any] | BaseModel) -> dict[str, Any]:
        """Serialize update or create attributes for the Marketplace client."""
        if isinstance(attributes, BaseModel):
            return attributes.to_dict()
        return dict(attributes)

    async def _paginate(
        self,
        collection: Any,
        model: type[Model],
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> PaginatedCollection[Model]:
        """Fetch and serialize one page from a Marketplace collection."""
        page = await collection.fetch_page(offset=offset, limit=limit)
        pagination = page.meta.pagination if page.meta else None
        resources = [model.from_payload(element) for element in page]
        return PaginatedCollection(
            limit=pagination.limit if pagination else limit,
            offset=pagination.offset if pagination else offset,
            resources=resources,
            total=pagination.total if pagination else offset + len(resources),
        )

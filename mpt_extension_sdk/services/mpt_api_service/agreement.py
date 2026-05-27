import logging
from collections.abc import Mapping
from typing import Any

from mpt_extension_sdk.models import Agreement
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.mpt_api_service.base import BaseService, PaginatedCollection

logger = logging.getLogger(__name__)


class AgreementService(BaseService[Agreement]):
    """Agreements service."""

    async def get_all(self, offset: int = 0, limit: int = 100) -> PaginatedCollection[Agreement]:
        """Fetch a page of agreements."""
        return await self._paginate(
            self._client.commerce.agreements,
            Agreement,
            offset=offset,
            limit=limit,
        )

    async def get_by_id(self, agreement_id: str) -> Agreement:
        """Fetch an agreement."""
        agreement = await self._client.commerce.agreements.get(
            agreement_id,
            select=[
                "assets",
                "buyer",
                "client",
                "licensee",
                "lines",
                "listing",
                "parameters",
                "product",
                "seller",
                "subscriptions",
            ],
        )
        logger.debug("Fetched agreement %s: %s", agreement_id, agreement.to_dict())
        return Agreement.from_payload(agreement)

    async def update(self, agreement_id: str, attributes: Mapping[str, Any] | BaseModel) -> None:
        """Update an agreement."""
        await self._client.commerce.agreements.update(
            agreement_id, self._serialize_attributes(attributes)
        )

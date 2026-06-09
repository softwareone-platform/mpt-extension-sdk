from mpt_api_client import RQLQuery

from mpt_extension_sdk.models.installation import Installation
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class InstallationService(BaseService[Installation]):
    """Integration installations service."""

    async def exists_for_account(self, extension_id: str, account_id: str) -> bool:
        """Return whether an installation exists for the given extension and account.

        Args:
            extension_id: Target extension id.
            account_id: Target Marketplace account id.

        Returns:
            ``True`` when at least one installation is returned by the API
            regardless of installation status; ``False`` only when the
            Marketplace API responds with an empty result set. Other API
            errors are propagated to the caller.
        """
        page = await self._client.integration.installations.filter(
            RQLQuery(extension__id=extension_id) & RQLQuery(account__id=account_id)
        ).fetch_page(limit=0)
        return page.meta.pagination.total != 0  # type: ignore[union-attr]

from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class InstallationService(BaseService[AccountToken]):
    """Installation service."""

    async def create_token(self, account_id: str) -> AccountToken:
        """Refresh the account-scoped token for an installation."""
        return AccountToken.from_payload(
            await self._client.integration.installations().create({"account_id": account_id})
        )

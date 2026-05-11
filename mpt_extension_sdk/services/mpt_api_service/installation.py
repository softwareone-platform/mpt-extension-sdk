from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class InstallationService(BaseService[AccountToken]):
    """Installation service."""

    async def create_token(self, account_id: str) -> AccountToken:
        """Create an account-scoped token for an installation."""
        installations = self._client.integration.installations()
        response = await installations.http_client.request(
            "post",
            installations.path,
            query_params={"account.id": account_id},
        )
        return AccountToken.from_payload(response.json())

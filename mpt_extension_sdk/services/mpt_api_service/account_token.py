from typing import cast

from mpt_extension_sdk.jwt import decode_unverified_jwt_claims
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class AccountTokenService(BaseService[AccountToken]):
    """Account-scoped token service."""

    async def create_token(self, account_id: str) -> AccountToken:
        """Create an account-scoped token for an installation."""
        installation_token = await self._client.integration.installations_token().token(account_id)
        claims = decode_unverified_jwt_claims(cast(str, installation_token.token))

        payload = {**installation_token.to_dict(), "exp": claims.get("exp")}
        return AccountToken.from_payload(payload)

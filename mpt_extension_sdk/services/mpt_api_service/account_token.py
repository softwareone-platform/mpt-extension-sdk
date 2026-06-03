from mpt_extension_sdk.jwt import decode_unverified_jwt_claims
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class AccountTokenService(BaseService[AccountToken]):
    """Account-scoped token service."""

    async def create_token(self, account_id: str) -> AccountToken:
        """Create an account-scoped token for an installation."""
        installations = self._client.integration.installations_token()
        response = await installations.http_client.request(
            "post", installations.path, query_params={"account.id": account_id}
        )
        payload = response.json()
        claims = decode_unverified_jwt_claims(payload["token"])
        payload = {**payload, "exp": claims.get("exp")}
        return AccountToken.from_payload(payload)

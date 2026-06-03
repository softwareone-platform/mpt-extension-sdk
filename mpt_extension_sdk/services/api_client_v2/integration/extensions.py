from mpt_api_client.resources.integration import AsyncIntegration as BaseAsyncIntegration

from mpt_extension_sdk.services.api_client_v2.integration.extensions_installations import (
    AsyncIntegrationInstallationsTokenService,
)


class AsyncIntegration(BaseAsyncIntegration):
    """Extensions service."""

    def installations_token(self) -> AsyncIntegrationInstallationsTokenService:
        """Installation service.

        Returns:
            Extension Installation service.
        """
        return AsyncIntegrationInstallationsTokenService(http_client=self.http_client)

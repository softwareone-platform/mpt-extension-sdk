from mpt_api_client.resources.integration import (
    AsyncIntegration as BaseAsyncIntegration,
)

from mpt_extension_sdk.services.api_client_v2.integration.extensions_installations import (
    AsyncIntegrationInstallationsService,
)


class AsyncIntegration(BaseAsyncIntegration):
    """Extensions service."""

    def installations(self) -> AsyncIntegrationInstallationsService:
        """Installation service.

        Returns:
            Extension Installation service.
        """
        return AsyncIntegrationInstallationsService(http_client=self.http_client)

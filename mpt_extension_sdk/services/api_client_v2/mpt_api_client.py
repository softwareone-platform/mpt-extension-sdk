from typing import override

from mpt_api_client.mpt_client import AsyncMPTClient as BaseAsyncMPTClient

from mpt_extension_sdk.services.api_client_v2.integration.extensions import AsyncIntegration
from mpt_extension_sdk.services.api_client_v2.system.system import AsyncSystem


class AsyncMPTClient(BaseAsyncMPTClient):
    """MPT client wrapper to implement endpoints that will be moved there."""

    @property
    def system(self) -> AsyncSystem:
        """System service."""
        return AsyncSystem(http_client=self.http_client)

    @override
    @property
    def integration(self) -> AsyncIntegration:
        """Integration service."""
        return AsyncIntegration(http_client=self.http_client)

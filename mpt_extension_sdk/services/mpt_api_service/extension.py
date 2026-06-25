from mpt_extension_sdk.models import Extension
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class ExtensionService(BaseService[Extension]):
    """Extension service."""

    async def get_by_id(self, extension_id: str) -> Extension:
        """Fetch an extension by ID."""
        return Extension.from_payload(await self._client.integration.extensions.get(extension_id))

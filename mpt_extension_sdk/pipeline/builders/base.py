from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings
from mpt_extension_sdk.settings.runtime import RuntimeSettings


@dataclass(frozen=True, kw_only=True)
class ContextResources:
    """Authentication, services and settings shared by every execution context."""

    auth: AuthContext
    ext_settings: BaseExtensionSettings
    mpt_api_service: MPTAPIService
    runtime_settings: RuntimeSettings
    vendor_mpt_api_service: MPTAPIService

    def base_fields(self) -> dict[str, Any]:
        """Return the `BaseContext` fields these resources fill."""
        return {
            "auth": self.auth,
            "ext_settings": self.ext_settings,
            "mpt_api_service": self.mpt_api_service,
            "runtime_settings": self.runtime_settings,
            "vendor_mpt_api_service": self.vendor_mpt_api_service,
        }


class ContextBuilder[ContextT: BaseContext](ABC):
    """Build the execution context of one route family."""

    @abstractmethod
    async def build(self, resources: ContextResources) -> ContextT:
        """Build the execution context from the shared resources."""
        raise NotImplementedError

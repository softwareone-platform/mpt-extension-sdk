from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Self

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.account import AccountSettings
from mpt_extension_sdk.settings.extension import BaseExtensionSettings
from mpt_extension_sdk.settings.runtime import RuntimeSettings


@dataclass(kw_only=True)
class BaseContext:
    """Base context."""

    logger: Logger
    mpt_api_service: MPTAPIService

    account_settings: AccountSettings = field(default_factory=AccountSettings)
    ext_settings: BaseExtensionSettings
    runtime_settings: RuntimeSettings
    auth: AuthContext | None = None


class ContextAdapter(ABC):
    """Interface for explicit context adapters."""

    @classmethod
    @abstractmethod
    def from_context(cls, ctx: Any) -> Self:
        """Build the custom context from the SDK base context."""

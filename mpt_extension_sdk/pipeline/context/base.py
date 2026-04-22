from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Self

from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.account import AccountSettings
from mpt_extension_sdk.settings.extension import BaseExtensionSettings
from mpt_extension_sdk.settings.runtime import RuntimeSettings


@dataclass(frozen=True)
class ExecutionMetadata:
    """Immutable event execution metadata."""

    event_id: str
    object_id: str
    object_type: str
    task_id: str

    correlation_id: str | None = None
    installation_id: str | None = None


@dataclass(kw_only=True)
class ExecutionContext:
    """Mutable context passed through pipeline steps."""

    logger: Logger
    meta: ExecutionMetadata
    mpt_api_service: MPTAPIService

    account_settings: AccountSettings = field(default_factory=AccountSettings)
    ext_settings: BaseExtensionSettings
    runtime_settings: RuntimeSettings

    state: dict[str, Any] = field(default_factory=dict)


class ContextAdapter(ABC):
    """Interface for explicit context adapters."""

    @classmethod
    @abstractmethod
    def from_context(cls, ctx: ExecutionContext) -> Self:
        """Build the custom context from the SDK base context."""

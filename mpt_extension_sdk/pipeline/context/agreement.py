from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from mpt_extension_sdk.models import Agreement
from mpt_extension_sdk.pipeline.context.base import ExecutionContext


class AgreementStatusActionType(StrEnum):
    """Supported agreement transitions requested by business logic."""

    FAIL = "Failed"


@dataclass(frozen=True)
class AgreementStatusAction:
    """Structured agreement transition intent declared by business logic."""

    target_status: AgreementStatusActionType
    message: str
    status_notes: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None  # noqa: WPS110


@dataclass
class AgreementState:
    """Mutable agreement state transition data shared across pipeline steps."""

    action: AgreementStatusAction | None = None
    handled: bool = False


@dataclass(kw_only=True)
class AgreementContext(ExecutionContext):
    """Execution context specialized for agreement events."""

    agreement: Agreement
    agreement_state: AgreementState = field(default_factory=AgreementState)

    @property
    def agreement_id(self) -> str:
        """Agreement ID."""
        return self.agreement.id

    async def refresh_agreement(self) -> None:
        """Reload the current agreement from Marketplace."""
        self.agreement = await self.mpt_api_service.agreements.get_by_id(self.agreement_id)

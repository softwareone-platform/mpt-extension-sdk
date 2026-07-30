from enum import StrEnum
from typing import Any, Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownInstallationStatusWarning(UnknownStatusWarning):
    """Signals that a platform installation reported a status outside the known set."""


class UnknownInstallationInvitationStatusWarning(UnknownStatusWarning):
    """Signals that a platform installation invitation reported a status outside the known set."""


class InstallationStatus(CaseInsensitiveStrEnum):
    """Installation status."""

    INVITED = "Invited"
    INSTALLED = "Installed"
    UNINSTALLED = "Uninstalled"
    EXPIRED = "Expired"


class InstallationInvitationStatus(CaseInsensitiveStrEnum):
    """Installation invitation status."""

    INVITED = "Invited"
    INSTALLED = "Installed"
    UNINSTALLED = "Uninstalled"
    EXPIRED = "Expired"


class InvitationValidityPeriod(StrEnum):
    """Installation invitation status."""

    SEVEN_DAYS = "7d"
    FOURTEEN_DAYS = "14d"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"


class InvitationValidity(BaseModel):
    """Installation invitation validity."""

    period: InvitationValidityPeriod


class InstallationInvitation(BaseModel):
    """Installation invitation."""

    message: str
    status: InstallationInvitationStatus | str = Field(union_mode="left_to_right")
    validity: InvitationValidity
    url: str

    external_id: str | None = Field(
        default=None, serialization_alias="externalId", validation_alias="externalId"
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known InstallationInvitationStatus."""
        warn_on_unknown_status(
            "Installation invitation",
            self.external_id or "",
            self.status,
            InstallationInvitationStatus,
            UnknownInstallationInvitationStatusWarning,
        )
        return self


class InstallationReference(BaseModel):
    """Installation reference."""

    id: str


class Installation(BaseModel):
    """Installation."""

    id: str | None = None
    account: InstallationReference
    extension: InstallationReference

    configuration: dict[str, Any] | None = Field(default_factory=dict, exclude=True)
    modules: list[InstallationReference] = Field(default_factory=list)
    invitation: InstallationInvitation | None = Field(default=None, exclude=True)
    status: InstallationStatus | str | None = Field(
        default=None, exclude=True, union_mode="left_to_right"
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known InstallationStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Installation",
                self.id or "",
                self.status,
                InstallationStatus,
                UnknownInstallationStatusWarning,
            )
        return self

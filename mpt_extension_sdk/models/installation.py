from enum import StrEnum
from typing import Any

from pydantic import Field

from mpt_extension_sdk.models.base import BaseModel


class InstallationStatus(StrEnum):
    """Installation status."""

    INVITED = "Invited"
    INSTALLED = "Installed"
    UNINSTALLED = "Uninstalled"
    EXPIRED = "Expired"


class InstallationInvitationStatus(StrEnum):
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
    status: InstallationInvitationStatus
    validity: InvitationValidity
    url: str

    external_id: str | None = Field(
        default=None, serialization_alias="externalId", validation_alias="externalId"
    )


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
    status: InstallationStatus | None = Field(default=None, exclude=True)

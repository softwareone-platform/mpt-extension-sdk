from enum import StrEnum

from mpt_extension_sdk.models.base import BaseModel


class InstallationStatus(StrEnum):
    """Lifecycle status of an extension installation in a Marketplace account."""

    INVITED = "Invited"
    INSTALLED = "Installed"
    UNINSTALLED = "Uninstalled"
    EXPIRED = "Expired"


class InstallationReference(BaseModel):
    """Reference to another resource embedded in an installation payload."""

    id: str


class Installation(BaseModel):
    """Installation of an extension in a Marketplace account."""

    id: str | None = None
    name: str | None = None
    status: InstallationStatus | None = None
    account: InstallationReference | None = None
    extension: InstallationReference | None = None

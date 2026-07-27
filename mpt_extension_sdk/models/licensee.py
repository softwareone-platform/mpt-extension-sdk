from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.address import Address
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.contact import Contact
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownLicenseeStatusWarning(UnknownStatusWarning):
    """Signals that a platform licensee reported a status outside the known set."""


class LicenseeStatus(CaseInsensitiveStrEnum):
    """Marketplace licensee status."""

    ENABLED = "Enabled"
    ACTIVE = "Active"
    DISABLED = "Disabled"
    DELETED = "Deleted"


class Licensee(BaseModel):
    """Licensee model."""

    id: str
    name: str
    status: LicenseeStatus | str = Field(union_mode="left_to_right")
    icon: str | None = None

    address: Address | None = None
    contact: Contact | None = None
    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known LicenseeStatus."""
        warn_on_unknown_status(
            "Licensee", self.id, self.status, LicenseeStatus, UnknownLicenseeStatusWarning
        )
        return self

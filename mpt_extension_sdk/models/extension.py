from typing import Any, Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models import Account
from mpt_extension_sdk.models.audit import Audit
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownExtensionStatusWarning(UnknownStatusWarning):
    """Signals that a platform extension reported a status outside the known set."""


class ExtensionStatusEnum(CaseInsensitiveStrEnum):
    """Extension status enum."""

    DELETED = "Deleted"
    DRAFT = "Draft"
    PRIVATE = "Private"
    PUBLIC = "Public"


class Extension(BaseModel):
    """Extension model."""

    id: str | None = None
    icon: str | None = None
    name: str | None = None
    revision: int | None = None
    status: ExtensionStatusEnum | str | None = Field(default=None, union_mode="left_to_right")
    website: str | None = None

    long_description: str | None = Field(
        default=None, serialization_alias="longDescription", validation_alias="longDescription"
    )
    short_description: str | None = Field(
        default=None, serialization_alias="shortDescription", validation_alias="shortDescription"
    )

    audit: Audit | None = None
    modules: list["Module"] = Field(default_factory=list)
    vendor: Account

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known ExtensionStatusEnum."""
        if self.status is not None:
            warn_on_unknown_status(
                "Extension",
                self.id or "",
                self.status,
                ExtensionStatusEnum,
                UnknownExtensionStatusWarning,
            )
        return self


class Module(BaseModel):
    """Module model."""

    id: str | None = None
    name: str
    revision: int | None = None
    description: str | None = None

    account_types: list[str] = Field(
        default_factory=list, serialization_alias="accountTypes", validation_alias="accountTypes"
    )
    filters: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)

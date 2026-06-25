from enum import StrEnum
from typing import Any

from pydantic import Field

from mpt_extension_sdk.models import Account
from mpt_extension_sdk.models.audit import Audit
from mpt_extension_sdk.models.base import BaseModel


class ExtensionStatusEnum(StrEnum):
    """Extension status enum."""

    DELETED = "Deleted"
    PRIVATE = "Private"
    PUBLIC = "Public"


class Extension(BaseModel):
    """Extension model."""

    id: str | None = None
    icon: str | None = None
    name: str | None = None
    revision: int | None = None
    status: ExtensionStatusEnum | None = None
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

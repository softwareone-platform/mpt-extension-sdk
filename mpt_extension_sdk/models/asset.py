from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.price import Price
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)
from mpt_extension_sdk.models.template import Template


class UnknownAssetStatusWarning(UnknownStatusWarning):
    """Signals that a platform asset reported a status outside the known set."""


class AssetStatus(CaseInsensitiveStrEnum):
    """Marketplace asset status."""

    NEW = "New"
    DRAFT = "Draft"
    ACTIVE = "Active"
    TERMINATED = "Terminated"


class AssetLine(BaseModel):
    """Asset line model."""

    id: str
    old_quantity: int = Field(
        default=0, serialization_alias="oldQuantity", validation_alias="oldQuantity"
    )
    quantity: int

    price: Price


class AssetSimple(BaseModel):
    """Asset model."""

    id: str
    name: str
    revision: int | None = None
    status: AssetStatus | str = Field(union_mode="left_to_right")

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known AssetStatus."""
        warn_on_unknown_status(
            "Asset", self.id, self.status, AssetStatus, UnknownAssetStatusWarning
        )
        return self


class Asset(AssetSimple):
    """Asset model."""

    external_id: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )
    price: Price
    lines: list[AssetLine] = Field(default_factory=list)
    parameters: ParameterBag = Field(default_factory=ParameterBag)  # noqa: WPS110
    template: Template | None = None

from pydantic import Field

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.price import Price
from mpt_extension_sdk.models.template import Template


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
    status: str


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

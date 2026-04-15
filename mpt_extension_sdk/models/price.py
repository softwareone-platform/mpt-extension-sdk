from pydantic import Field

from mpt_extension_sdk.models.base import BaseModel, FloatDecimal


class Price(BaseModel):
    """Price model."""

    currency: str
    default_markup: FloatDecimal | None = Field(
        default=None, serialization_alias="defaultMarkup", validation_alias="defaultMarkup"
    )
    ppxy: FloatDecimal | None = Field(
        default=None, serialization_alias="PPxY", validation_alias="PPxY"
    )
    ppxm: FloatDecimal | None = Field(
        default=None, serialization_alias="PPxM", validation_alias="PPxM"
    )
    ppx1: FloatDecimal | None = Field(
        default=None, serialization_alias="PPx1", validation_alias="PPx1"
    )
    spxy: FloatDecimal | None = Field(
        default=None, serialization_alias="SPxY", validation_alias="SPxY"
    )
    spxm: FloatDecimal | None = Field(
        default=None, serialization_alias="SPxM", validation_alias="SPxM"
    )
    spx1: FloatDecimal | None = Field(
        default=None, serialization_alias="SPx1", validation_alias="SPx1"
    )
    unit_pp: FloatDecimal | None = Field(
        default=None, serialization_alias="unitPP", validation_alias="unitPP"
    )
    unit_sp: FloatDecimal | None = Field(
        default=None, serialization_alias="unitSP", validation_alias="unitSP"
    )

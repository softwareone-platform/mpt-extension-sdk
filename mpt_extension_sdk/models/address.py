from pydantic import Field

from mpt_extension_sdk.models.base import BaseModel


class Address(BaseModel):
    """Address model."""

    address_line1: str = Field(serialization_alias="addressLine1", validation_alias="addressLine1")
    address_line2: str | None = Field(
        default=None, serialization_alias="addressLine2", validation_alias="addressLine2"
    )
    city: str
    country: str
    post_code: str = Field(serialization_alias="postCode", validation_alias="postCode")
    state: str

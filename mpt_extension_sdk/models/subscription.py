from pydantic import Field

from mpt_extension_sdk.models.base import BaseModel, ISODatetime
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.product import ProductItem


class SubscriptionLine(BaseModel):
    """Subscription line model."""

    id: str
    description: str | None = None
    status: str | None = None
    quantity: int

    product_item: ProductItem = Field(
        alias="item", serialization_alias="item", validation_alias="item"
    )


class SubscriptionSimple(BaseModel):
    """Subscription model with simple details."""

    id: str
    name: str
    revision: int | None = None


class Subscription(SubscriptionSimple):
    """Subscription model."""

    auto_renew: bool | None = Field(
        default=None, serialization_alias="autoRenew", validation_alias="autoRenew"
    )
    commitment_date: ISODatetime | None = Field(
        default=None, serialization_alias="commitmentDate", validation_alias="commitmentDate"
    )
    start_date: ISODatetime | None = Field(
        default=None, serialization_alias="startDate", validation_alias="startDate"
    )
    termination_date: ISODatetime | None = Field(
        default=None, serialization_alias="terminationDate", validation_alias="terminationDate"
    )

    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )
    lines: list[SubscriptionLine] = Field(default_factory=list)
    parameters: ParameterBag = Field(default_factory=ParameterBag)  # noqa: WPS110

from pydantic import Field

from mpt_extension_sdk.models.account import Account, SellerAccount
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.product import Product


class Authorization(BaseModel):
    """Authorization model."""

    id: str
    name: str
    revision: int | None = None
    currency: str

    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )
    owner: SellerAccount | None = None
    product: Product | None = None
    vendor: Account | None = None

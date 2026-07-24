from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.account import SellerAccount
from mpt_extension_sdk.models.agreement import Agreement
from mpt_extension_sdk.models.asset import Asset
from mpt_extension_sdk.models.authorization import Authorization
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.price import Price
from mpt_extension_sdk.models.product import Product, ProductItem
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)
from mpt_extension_sdk.models.subscription import Subscription
from mpt_extension_sdk.models.template import Template


class UnknownOrderStatusWarning(UnknownStatusWarning):
    """Signals that a platform order reported a status outside the known set."""


class OrderStatus(CaseInsensitiveStrEnum):
    """Marketplace order status."""

    DRAFT = "Draft"
    QUOTED = "Quoted"
    PROCESSING = "Processing"
    QUERYING = "Querying"
    COMPLETED = "Completed"
    FAILED = "Failed"
    DELETED = "Deleted"


class OrderLine(BaseModel):
    """Order line."""

    id: str
    description: str | None = None
    old_quantity: int = Field(
        default=0, serialization_alias="oldQuantity", validation_alias="oldQuantity"
    )
    quantity: int

    asset: Asset | None = None
    product_item: ProductItem = Field(
        alias="item", serialization_alias="item", validation_alias="item"
    )
    price: Price
    subscription: Subscription | None = None


class Order(BaseModel):  # noqa: WPS214
    """Order."""

    id: str
    revision: int | None = None
    status: OrderStatus | str = Field(union_mode="left_to_right")
    type: str

    agreement: Agreement
    assets: list[Asset] = Field(default_factory=list)
    authorization: Authorization
    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )
    lines: list[OrderLine] = Field(default_factory=list)
    parameters: ParameterBag = Field(default_factory=ParameterBag)  # noqa: WPS110
    product: Product
    seller: SellerAccount | None = None
    subscriptions: list[Subscription] = Field(default_factory=list)
    template: Template | None = None

    @property
    def agreement_id(self) -> str:
        """The agreement identifier."""
        return self.agreement.id

    @property
    def authorization_id(self) -> str:
        """The authorization identifier."""
        return self.authorization.id

    @property
    def customer_id(self) -> str | None:
        """The customer identifier from the agreement."""
        return self.agreement.external_ids.vendor

    @property
    def product_id(self) -> str:
        """The product identifier."""
        return self.product.id

    @property
    def seller_id(self) -> str | None:
        """The seller identifier when available."""
        return None if self.seller is None else self.seller.id

    @property
    def downsize_lines(self) -> list[OrderLine]:
        """Downsize lines from the order."""
        return [elem for elem in self.lines if elem.quantity < elem.old_quantity]

    @property
    def upsize_lines(self) -> list[OrderLine]:
        """Upsize lines from order."""
        return [elem for elem in self.lines if elem.quantity > elem.old_quantity > 0]  # noqa: WPS334

    @property
    def new_lines(self) -> list[OrderLine]:
        """New lines from the order."""
        return [elem for elem in self.lines if elem.old_quantity == 0]

    def get_line_by_sku(self, sku: str) -> OrderLine:
        """Return the line matching a SKU."""
        for elem in self.lines:
            vendor_sku = elem.product_item.external_ids.vendor
            if vendor_sku is not None and vendor_sku == sku:
                return elem

        raise ValueError(f"No line found for SKU: {sku}")

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known OrderStatus."""
        warn_on_unknown_status(
            "Order", self.id, self.status, OrderStatus, UnknownOrderStatusWarning
        )
        return self

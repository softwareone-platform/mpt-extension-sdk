from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.account import Account, BuyerAccount, SellerAccount
from mpt_extension_sdk.models.asset import AssetSimple
from mpt_extension_sdk.models.authorization import Authorization
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.licensee import Licensee
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.product import Product, ProductItem
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)
from mpt_extension_sdk.models.subscription import SubscriptionSimple


class UnknownAgreementStatusWarning(UnknownStatusWarning):
    """Signals that a platform agreement reported a status outside the known set."""


class AgreementStatus(CaseInsensitiveStrEnum):
    """Marketplace agreement status."""

    NEW = "New"
    DRAFT = "Draft"
    DELETED = "Deleted"
    PROVISIONING = "Provisioning"
    FAILED = "Failed"
    ACTIVE = "Active"
    UPDATING = "Updating"
    TERMINATED = "Terminated"


class AgreementLine(BaseModel):
    """Agreement line model."""

    id: str
    description: str | None = None
    quantity: int
    status: AgreementStatus | str | None = Field(default=None, union_mode="left_to_right")

    product_item: ProductItem = Field(
        alias="item", serialization_alias="item", validation_alias="item"
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known AgreementStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Agreement line",
                self.id,
                self.status,
                AgreementStatus,
                UnknownAgreementStatusWarning,
            )
        return self


class AgreementSimple(BaseModel):
    """Agreement with its own fields only, as embedded in webhook payloads."""

    id: str
    name: str | None = None
    revision: int | None = None
    status: AgreementStatus | str | None = Field(default=None, union_mode="left_to_right")

    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known AgreementStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Agreement", self.id, self.status, AgreementStatus, UnknownAgreementStatusWarning
            )
        return self


class Agreement(AgreementSimple):
    """Agreement model with its relations, as returned by the agreements API."""

    icon: str | None = None
    name: str

    authorization: Authorization | None = None
    assets: list[AssetSimple] = Field(default_factory=list)
    buyer: BuyerAccount | None = None
    client: Account
    licensee: Licensee
    lines: list[AgreementLine] = Field(default_factory=list)
    parameters: ParameterBag = Field(default_factory=ParameterBag)  # noqa: WPS110
    product: Product
    seller: SellerAccount | None = None
    subscriptions: list[SubscriptionSimple] = Field(default_factory=list)
    vendor: Account | None = None

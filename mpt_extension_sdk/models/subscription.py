from typing import Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel, ISODatetime
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.parameter import ParameterBag
from mpt_extension_sdk.models.product import ProductItem
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownSubscriptionStatusWarning(UnknownStatusWarning):
    """Signals that a platform subscription reported a status outside the known set."""


class SubscriptionStatus(CaseInsensitiveStrEnum):
    """Marketplace subscription status."""

    DRAFT = "Draft"
    ACTIVE = "Active"
    UPDATING = "Updating"
    TERMINATING = "Terminating"
    TERMINATED = "Terminated"
    EXPIRED = "Expired"
    DELETED = "Deleted"


class SubscriptionLine(BaseModel):
    """Subscription line model."""

    id: str
    description: str | None = None
    status: SubscriptionStatus | str | None = Field(default=None, union_mode="left_to_right")
    quantity: int

    product_item: ProductItem = Field(
        alias="item", serialization_alias="item", validation_alias="item"
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known SubscriptionStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Subscription line",
                self.id,
                self.status,
                SubscriptionStatus,
                UnknownSubscriptionStatusWarning,
            )
        return self


class SubscriptionSimple(BaseModel):
    """Subscription model with simple details."""

    id: str
    name: str
    revision: int | None = None
    status: SubscriptionStatus | str | None = Field(default=None, union_mode="left_to_right")

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known SubscriptionStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Subscription",
                self.id,
                self.status,
                SubscriptionStatus,
                UnknownSubscriptionStatusWarning,
            )
        return self


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

import datetime as dt
from typing import Any, Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownAccountStatusWarning(UnknownStatusWarning):
    """Signals that a platform account reported a status outside the known set."""


class AccountStatus(CaseInsensitiveStrEnum):
    """Marketplace account status."""

    ENABLED = "Enabled"
    ACTIVE = "Active"
    DISABLED = "Disabled"
    DELETED = "Deleted"
    UNASSIGNED = "Unassigned"
    CONFLICT = "Conflict"
    MISMATCH = "Mismatch"


class Account(BaseModel):
    """Account model."""

    id: str
    name: str
    icon: str | None = None


class BuyerExternalId(BaseModel):
    """Buyer external identifiers model."""

    account_external_id: str | None = Field(
        default=None, serialization_alias="accountExternalId", validation_alias="accountExternalId"
    )
    erp_company_contact: str | None = Field(
        default=None, serialization_alias="erpCompanyContact", validation_alias="erpCompanyContact"
    )
    erp_customer: str | None = Field(
        default=None, serialization_alias="erpCustomer", validation_alias="erpCustomer"
    )


class BuyerAccount(Account):
    """Buyer model."""

    external_ids: BuyerExternalId | None = Field(
        default=None, serialization_alias="externalIds", validation_alias="externalIds"
    )
    status: AccountStatus | str | None = Field(default=None, union_mode="left_to_right")

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        """Emit a warning when the status is not a known AccountStatus."""
        if self.status is not None:
            warn_on_unknown_status(
                "Account", self.id, self.status, AccountStatus, UnknownAccountStatusWarning
            )
        return self


class SellerAccount(Account):
    """Seller model."""

    currency: str | None = None


class AccountToken(BaseModel):
    """Account-scoped token returned by Marketplace."""

    token: str
    exp: int
    expires_at: dt.datetime

    @model_validator(mode="before")
    @classmethod
    def fill_expires_at(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Calculate the expiration datetime from the token expiration timestamp."""
        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise TypeError("Account token expiration claim is invalid")

        return {
            **payload,
            "exp": exp,
            "expires_at": dt.datetime.fromtimestamp(exp, tz=dt.UTC),
        }

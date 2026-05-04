import datetime as dt
from typing import Any

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel


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
    status: str | None = None


class SellerAccount(Account):
    """Seller model."""

    currency: str | None = None


class AccountToken(BaseModel):
    """Cached account token plus its expiration timestamp."""

    token: str
    exp: str
    expires_at: dt.datetime

    @model_validator(mode="before")
    @classmethod
    def fill_expires_at(cls, payload: Any) -> Any:
        """Calculate the expiration datetime from the token expiration timestamp."""
        if not isinstance(payload, dict) or payload.get("expires_at") is not None:
            return payload

        exp = payload.get("exp")
        if exp is None:
            return payload

        return {
            **payload,
            "expires_at": dt.datetime.fromtimestamp(int(exp), tz=dt.UTC),
        }

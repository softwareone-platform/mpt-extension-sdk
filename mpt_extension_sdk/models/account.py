from pydantic import Field

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

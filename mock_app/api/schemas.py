from mpt_extension_sdk.schemas import BaseSchema


class AgreementSchema(BaseSchema):
    """Schema used by the mock agreement creation endpoint."""

    id: str
    name: str
    client: dict[str, str]
    licensee: dict[str, str]
    parameters: dict[str, str]  # noqa: WPS110
    product: dict[str, str]

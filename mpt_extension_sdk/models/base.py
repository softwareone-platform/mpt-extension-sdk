import datetime as dt
from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, PlainSerializer

FloatDecimal = Annotated[Decimal, PlainSerializer(lambda el: float(el), return_type=float)]  # noqa: PLW0108, WPS506, WPS221
ISODatetime = Annotated[
    dt.datetime,
    PlainSerializer(lambda el: el.isoformat(), return_type=str, when_used="json-unless-none"),
]


class BaseModel(PydanticBaseModel):
    """Base schema."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="allow",
        serialize_by_alias=True,
        validate_by_name=True,
        frozen=True,
        validate_by_alias=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Dump the model using the alias field names."""
        return self.model_dump(exclude_none=True, mode="json")

    @classmethod
    def from_payload(cls, payload: Any) -> Self:
        """Build a model from an API payload."""
        # mpt_api_client returns ModelBase objects (dicts exposed as dynamic attributes),
        # whose nested values are also ModelBase. to_dict() turns them into plain nested
        # dicts so fields typed as dict (e.g. ``module.settings``) validate as expected.
        to_dict = getattr(payload, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()

        return cls.model_validate(payload, by_alias=True)

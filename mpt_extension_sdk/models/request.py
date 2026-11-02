from typing import Any, Self

from pydantic import Field, model_validator

from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.models.external_id import ExternalIds
from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class UnknownRequestStatusWarning(UnknownStatusWarning):
    """Signals that a platform request reported a status outside the known set."""


class RequestStatus(CaseInsensitiveStrEnum):
    """Marketplace request status."""

    COMPLETED = "Completed"
    DRAFT = "Draft"
    PROCESSING = "Processing"
    QUERYING = "Querying"


class Request(BaseModel):
    """Marketplace request model."""

    id: str
    status: RequestStatus | str = Field(union_mode="left_to_right")

    error: dict[str, Any] | None = None
    external_ids: ExternalIds = Field(
        default_factory=ExternalIds,
        serialization_alias="externalIds",
        validation_alias="externalIds",
    )

    @model_validator(mode="after")
    def _warn_on_unknown_status(self) -> Self:
        warn_on_unknown_status(
            "Request", self.id, self.status, RequestStatus, UnknownRequestStatusWarning
        )
        return self

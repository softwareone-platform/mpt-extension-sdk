from dataclasses import dataclass

from mpt_extension_sdk.api.models.base import APIBaseModel


@dataclass(frozen=True)
class ErrorDetail:
    """Single field-level error returned in a problem-details response."""

    pointer: str
    detail: str


class ProblemDetails(APIBaseModel):
    """Problem Details response payload."""

    type: str = "about:blank"
    status: int
    title: str
    detail: str
    instance: str
    errors: list[ErrorDetail] | None = None
    correlation_id: str | None = None

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.models.errors import ProblemDetails


class APIErrorResponseBuilder:
    """Build authenticated API error HTTP responses."""

    @classmethod
    def build(
        cls, error: APIError, *, instance: str, correlation_id: str | None = None
    ) -> JSONResponse:
        """Create a problem-details HTTP response."""
        payload = ProblemDetails(
            type=error.type,
            status=error.status_code,
            title=error.title,
            detail=error.detail,
            instance=instance,
            errors=error.errors or None,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            content=jsonable_encoder(payload, exclude_none=True),
            status_code=error.status_code,
            media_type="application/problem+json",
        )

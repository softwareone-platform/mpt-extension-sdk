from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Self

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class WebhookResponse:
    """Response returned by a webhook handler."""

    status_code: int
    payload: Any

    @classmethod
    def error(
        cls,
        error_id: str,
        message: str,
        *,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    ) -> Self:
        """Return an error object response, `500` unless `status_code` says otherwise."""
        return cls(status_code=status_code, payload={"id": error_id, "message": message})

    @classmethod
    def ok(cls, payload: Any) -> Self:
        """Return a 200 OK response with the business object."""
        return cls(status_code=HTTPStatus.OK, payload=payload)

    def to_http_response(self) -> JSONResponse:
        """Convert the webhook response to a FastAPI response.

        Model fields that were not in the platform payload are left out, so the
        object goes back with the same shape it arrived with.
        """
        return JSONResponse(
            content=jsonable_encoder(self.payload, exclude_unset=True),
            status_code=self.status_code,
        )

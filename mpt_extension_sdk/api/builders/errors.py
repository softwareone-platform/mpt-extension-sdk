from abc import ABC, abstractmethod
from typing import override

from fastapi import Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.models.errors import ProblemDetails
from mpt_extension_sdk.runtime.logging import correlation_id_ctx


class RequestRejectedError(Exception):
    """Ends a request with `response` before its handler runs."""

    def __init__(self, response: Response) -> None:
        super().__init__(response.status_code)
        self.response = response


class RouteErrorResponseBuilder(ABC):
    """Build the error responses a route family answers outside its handler."""

    @abstractmethod
    def unauthorized(self, request: Request) -> Response:
        """Return the response of a request that could not be authenticated."""
        raise NotImplementedError

    @abstractmethod
    def unexpected(self, request: Request) -> Response:
        """Return the response of an unexpected handler error."""
        raise NotImplementedError


class APIErrorResponseBuilder(RouteErrorResponseBuilder):
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

    @override
    def unauthorized(self, request: Request) -> Response:
        """Return a `401` problem-details response."""
        return self.build(
            APIError(status_code=status.HTTP_401_UNAUTHORIZED), instance=request.url.path
        )

    @override
    def unexpected(self, request: Request) -> Response:
        """Return a `500` problem-details response carrying the correlation id."""
        error = APIError(
            "An unexpected error occurred. Contact support with the correlation id below.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal Server Error",
        )
        return self.build(error, instance=request.url.path, correlation_id=correlation_id_ctx.get())

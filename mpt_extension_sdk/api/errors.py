from http import HTTPStatus

from mpt_extension_sdk.api.models.errors import ErrorDetail


class APIError(Exception):
    """Base exception raised by authenticated API handlers."""

    def __init__(
        self,
        detail: str = "",
        *,
        status_code: int,
        title: str | None = None,
        error_type: str = "about:blank",
        errors: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(detail)
        self.type = error_type
        self.status_code = status_code
        self.title = title or HTTPStatus(status_code).phrase
        self.detail = detail or self.title
        self.errors = errors or []


class ForbiddenError(APIError):
    """403 forbidden problem-details error."""

    def __init__(self, detail: str = "Forbidden") -> None:
        super().__init__(detail, status_code=HTTPStatus.FORBIDDEN, title="Forbidden")


class NotFoundError(APIError):
    """404 not found problem-details error."""

    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(detail, status_code=HTTPStatus.NOT_FOUND, title="Not found")


class UnauthorizedError(APIError):
    """401 unauthorized problem-details error."""

    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(detail, status_code=HTTPStatus.UNAUTHORIZED, title="Unauthorized")


class ValidationError(APIError):
    """422 validation problem-details error."""

    def __init__(
        self,
        detail: str = "The request payload is invalid",
        *,
        errors: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(
            detail,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            title="Validation failed",
            errors=errors,
        )


class UpstreamServiceError(APIError):
    """502 bad-gateway problem-details error for upstream MPT API failures."""

    def __init__(self, detail: str = "Upstream service unavailable") -> None:
        super().__init__(detail, status_code=HTTPStatus.BAD_GATEWAY, title="Bad Gateway")

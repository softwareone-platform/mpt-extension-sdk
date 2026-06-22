from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Self

from fastapi import Request
from starlette.datastructures import Headers, QueryParams

from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail
from mpt_extension_sdk.api.pagination import Pagination
from mpt_extension_sdk.context import BaseContext

if TYPE_CHECKING:
    from mpt_extension_sdk.services.mpt_api_service import MPTAPIService


@dataclass(kw_only=True)
class APIContext(BaseContext):
    """Execution context passed to authenticated API handlers."""

    mpt_api_service: "MPTAPIService"
    request: "AuthenticatedRequestContext"

    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthenticatedRequestContext:
    """Subset of request-derived data exposed to authenticated handlers."""

    query: "RequestQueryParams"
    headers: Headers
    method: str
    url: str
    body: Any | None = None

    @property
    def pagination(self) -> Pagination:
        """Lazily parsed pagination parameters from the query string."""
        return Pagination.from_query(self.query)

    @classmethod
    def from_request(cls, request: Request, body: Any | None = None) -> Self:
        """Build the request context from an incoming FastAPI request."""
        return cls(
            query=RequestQueryParams(request.query_params),
            headers=request.headers,
            method=request.method,
            url=str(request.url),
            body=body,
        )

    def with_body(self, body: Any | None) -> Self:
        """Return a copy of this request context with the parsed body."""
        return replace(self, body=body)


@dataclass(frozen=True)
class RequestQueryParams:
    """Query parameters exposed to handlers with typed access helpers."""

    _query: QueryParams

    def __contains__(self, key: str) -> bool:
        """Return whether a query parameter exists."""
        return key in self._query

    def __getitem__(self, key: str) -> str:
        """Return the last value for a query parameter."""
        return self._query[key]

    def get(self, key: str, default: Any = None) -> str | Any:
        """Return the last value for a query parameter."""
        return self._query.get(key, default)

    def get_bool(self, key: str, *, default: bool | None = None) -> bool | None:
        """Return a query parameter parsed as a boolean."""
        raw_value = self._query.get(key)
        if not raw_value:
            return default

        normalized_value = raw_value.lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False

        return default

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Return a query parameter parsed as an integer."""
        raw_value = self._query.get(key)
        if not raw_value:
            return default

        try:
            return int(raw_value)
        except ValueError as error:
            raise ValidationError(
                errors=[ErrorDetail(pointer=f"#/{key}", detail="Value must be an integer")]
            ) from error

    def get_list(self, key: str) -> list[str]:
        """Return all values for a repeated query parameter."""
        return self._query.getlist(key)

    def multi_items(self) -> list[tuple[str, str]]:
        """Return repeated query parameter items."""
        return self._query.multi_items()

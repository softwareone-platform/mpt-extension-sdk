from dataclasses import dataclass
from typing import Any, Protocol, Self

from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail

DEFAULT_OFFSET = 0
DEFAULT_LIMIT = 100


class QueryParameters(Protocol):
    """Minimal query parameter API used by pagination."""

    def get(self, key: str, default: Any = None) -> str | Any:
        """Return the last value for a query parameter."""
        ...


@dataclass(frozen=True)
class Pagination:
    """Pagination parameters parsed from an authenticated API request."""

    offset: int = DEFAULT_OFFSET
    limit: int = DEFAULT_LIMIT

    @classmethod
    def from_query(cls, query: QueryParameters) -> Self:
        """Build pagination parameters from request query parameters."""
        return cls(
            offset=cls._parse_non_negative_int(query, "offset", DEFAULT_OFFSET),
            limit=cls._parse_non_negative_int(query, "limit", DEFAULT_LIMIT),
        )

    @classmethod
    def _parse_non_negative_int(cls, query: QueryParameters, name: str, default: int) -> int:
        raw_int_value = query.get(name)
        if raw_int_value is None:
            return default

        try:
            int_value = int(raw_int_value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                errors=[ErrorDetail(pointer=f"#/{name}", detail="Value must be an integer")]
            ) from error

        if int_value < 0:
            raise ValidationError(
                errors=[
                    ErrorDetail(
                        pointer=f"#/{name}", detail="Value must be greater than or equal to 0"
                    )
                ]
            )
        return int_value


@dataclass(frozen=True)
class PaginatedResult:
    """Result payload used to build a paginated API response."""

    payload: Any
    total: int
    offset: int
    limit: int

    @classmethod
    def from_pagination(cls, pagination: Pagination, *, payload: Any, total: int) -> Self:
        """Build a paginated result from request pagination input."""
        return cls(
            payload=payload,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
        )

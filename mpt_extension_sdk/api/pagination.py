from dataclasses import dataclass
from math import ceil
from typing import Any, Protocol, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 500


class QueryParameters(Protocol):
    """Minimal query parameter API used by pagination."""

    def get(self, key: str, default: Any = None) -> str | Any:
        """Return the last value for a query parameter."""
        ...


@dataclass(frozen=True)
class Pagination:
    """Pagination parameters parsed from an authenticated API request."""

    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    @classmethod
    def from_query(cls, query: QueryParameters) -> Self:
        """Build pagination parameters from request query parameters."""
        return cls(
            page=cls._parse_positive_int(query, "page", DEFAULT_PAGE),
            page_size=cls._parse_page_size(query),
        )

    @classmethod
    def _parse_page_size(cls, query: QueryParameters) -> int:
        page_size = cls._parse_positive_int(query, "page_size", DEFAULT_PAGE_SIZE)
        if page_size > MAX_PAGE_SIZE:
            raise ValidationError(
                errors=[
                    ErrorDetail(
                        pointer="#/page_size",
                        detail=f"Value must be less than or equal to {MAX_PAGE_SIZE}",
                    )
                ]
            )
        return page_size

    @classmethod
    def _parse_positive_int(cls, query: QueryParameters, name: str, default: int) -> int:
        raw_int_value = query.get(name)
        if raw_int_value is None:
            return default

        try:
            int_value = int(raw_int_value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                errors=[ErrorDetail(pointer=f"#/{name}", detail="Value must be an integer")]
            ) from error

        if int_value < 1:
            raise ValidationError(
                errors=[
                    ErrorDetail(
                        pointer=f"#/{name}", detail="Value must be greater than or equal to 1"
                    )
                ]
            )
        return int_value


@dataclass(frozen=True)
class PaginatedResult:
    """Result payload used to build a paginated API response."""

    payload: Any
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Return the total number of pages."""
        if self.total <= 0:
            return 0

        return ceil(self.total / self.page_size)

    @classmethod
    def from_pagination(cls, pagination: Pagination, *, payload: Any, total: int) -> Self:
        """Build a paginated result from request pagination input."""
        return cls(
            payload=payload,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class PaginationLinksBuilder:
    """Build standard pagination links from the current request URL."""

    @classmethod
    def build(cls, request_url: str, result: PaginatedResult) -> dict[str, str | None]:
        """Build all standard pagination links for a paginated result."""
        total_pages = result.total_pages
        last_page = max(total_pages, 1)
        previous_page = result.page - 1 if result.page > 1 else None
        next_page = result.page + 1 if total_pages and result.page < total_pages else None

        return {
            "self": cls.replace_page(request_url, result.page, result.page_size),
            "first": cls.replace_page(request_url, 1, result.page_size),
            "prev": (
                None
                if previous_page is None
                else cls.replace_page(request_url, previous_page, result.page_size)
            ),
            "next": (
                None
                if next_page is None
                else cls.replace_page(request_url, next_page, result.page_size)
            ),
            "last": cls.replace_page(request_url, last_page, result.page_size),
        }

    @classmethod
    def replace_page(cls, request_url: str, page: int, page_size: int) -> str:
        """Return the request URL with normalized page and page_size query parameters."""
        parts = urlsplit(request_url)
        query_items = [
            (key, query_item)
            for key, query_item in parse_qsl(parts.query, keep_blank_values=True)
            if key not in {"page", "page_size"}
        ]
        query_items.extend([("page", str(page)), ("page_size", str(page_size))])  # noqa: WPS221
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_items),
            parts.fragment,
        ))

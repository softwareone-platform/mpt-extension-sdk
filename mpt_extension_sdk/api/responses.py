from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Self

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from mpt_extension_sdk.api.models.base import APIBaseModel
from mpt_extension_sdk.api.pagination import PaginatedResult, PaginationLinksBuilder


class Meta(APIBaseModel):
    """Meta model."""

    total: int | None = None
    page: int | None = None
    page_size: int | None = None
    total_pages: int | None = None


class Links(APIBaseModel):
    """Links model."""

    self: str | None = None  # noqa: WPS117
    first: str | None = None
    last: str | None = None
    next: str | None = None
    prev: str | None = None


@dataclass(frozen=True)
class APIResponse:  # noqa: WPS214
    """API response envelope."""

    status_code: int
    has_body: bool = True
    payload: Any = None
    paginated_result: PaginatedResult | None = None
    links: Links | None = None
    meta: Meta | None = None

    @classmethod
    def accepted(cls, *, payload: Any = None) -> Self:
        """Return a 202 Accepted response."""
        return cls(status_code=HTTPStatus.ACCEPTED, payload=payload)

    @classmethod
    def created(cls, *, payload: Any = None) -> Self:
        """Return a 201 Created response."""
        return cls(status_code=HTTPStatus.CREATED, payload=payload)

    @classmethod
    def no_content(cls) -> Self:
        """Return a 204 No Content response."""
        return cls(status_code=HTTPStatus.NO_CONTENT, has_body=False)

    @classmethod
    def ok(
        cls,
        *,
        payload: Any = None,
        meta: Meta | dict[str, Any] | None = None,
        links: Links | dict[str, Any] | None = None,
    ) -> Self:
        """Return a 200 OK response."""
        return cls(
            status_code=HTTPStatus.OK,
            payload=payload,
            meta=cls.build_meta(meta),
            links=cls.build_links(links),
        )

    @classmethod
    def paginated(cls, result: PaginatedResult) -> Self:
        """Return a 200 OK paginated response."""
        return cls(status_code=HTTPStatus.OK, payload=result.payload, paginated_result=result)

    @classmethod
    def build_meta(cls, meta: Meta | dict[str, Any] | None) -> Meta | None:
        """Build typed metadata from a model or a plain mapping."""
        if meta is None or isinstance(meta, Meta):
            return meta

        return Meta(**meta)

    @classmethod
    def build_links(cls, links: Links | dict[str, Any] | None) -> Links | None:
        """Build typed links from a model or a plain mapping."""
        if links is None or isinstance(links, Links):
            return links

        return Links(**links)

    def to_http_response(self, *, request_url: str | None = None) -> Response:
        """Convert the SDK response envelope to a FastAPI response."""
        if not self.has_body:
            return Response(status_code=self.status_code)

        payload: dict[str, Any] = {"data": self.payload}
        if self.paginated_result is None:
            if self.meta is not None:
                payload["meta"] = self.meta
            if self.links is not None:
                payload["links"] = self.links
        else:
            payload["meta"] = Meta(
                total=self.paginated_result.total,
                page=self.paginated_result.page,
                page_size=self.paginated_result.page_size,
                total_pages=self.paginated_result.total_pages,
            )
            payload["links"] = Links(
                **PaginationLinksBuilder.build(request_url or "", self.paginated_result)
            )

        return JSONResponse(content=jsonable_encoder(payload), status_code=self.status_code)

import json
from http import HTTPStatus

from mpt_extension_sdk.api import (
    APIError,
    APIResponse,
    ForbiddenError,
    NotFoundError,
    PaginatedResult,
    UnauthorizedError,
    UpstreamServiceError,
)
from mpt_extension_sdk.api.responses import Links, Meta

TOTAL_ITEMS = 12


def test_api_error_defaults_to_status_phrase():
    result = APIError(status_code=HTTPStatus.BAD_REQUEST)

    assert result.title == "Bad Request"
    assert result.detail == "Bad Request"
    assert result.errors == []


def test_api_error_convenience_types():
    result = (
        ForbiddenError(),
        NotFoundError(),
        UnauthorizedError(),
        UpstreamServiceError(),
    )

    assert [error.status_code for error in result] == [
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.BAD_GATEWAY,
    ]


def test_api_response_accepted_and_created():
    result = (
        APIResponse.accepted(payload={"status": "queued"}).status_code,
        APIResponse.created(payload={"id": "AGR-1"}).status_code,
    )

    assert result == (HTTPStatus.ACCEPTED, HTTPStatus.CREATED)


def test_api_response_ok_serializes_body():
    response = APIResponse.ok(
        payload={"id": "ORD-1"},
        meta={"total": 1},
        links={"self": "https://example.com/orders/ORD-1"},
    )

    result = response.to_http_response()

    assert result.status_code == HTTPStatus.OK
    assert json.loads(result.body) == {
        "data": {"id": "ORD-1"},
        "meta": {"total": 1, "page": None, "page_size": None, "total_pages": None},
        "links": {
            "self": "https://example.com/orders/ORD-1",
            "first": None,
            "last": None,
            "next": None,
            "prev": None,
        },
    }
    assert isinstance(response.meta, Meta)
    assert isinstance(response.links, Links)


def test_api_response_no_content_has_empty_body():
    result = APIResponse.no_content().to_http_response()

    assert result.status_code == HTTPStatus.NO_CONTENT
    assert result.body == b""


def test_api_response_preserves_typed_metadata():
    meta = Meta(total=1)
    links = Links(self="https://example.com/orders/ORD-1")

    result = APIResponse.ok(payload={}, meta=meta, links=links)

    assert result.meta is meta
    assert result.links is links


def test_api_response_paginated_adds_links():
    paginated_result = PaginatedResult(
        payload=[{"id": "ORD-1"}], total=TOTAL_ITEMS, page=2, page_size=5
    )

    result = APIResponse.paginated(paginated_result).to_http_response(
        request_url="https://example.com/orders?page=2&page_size=5"
    )

    payload = json.loads(result.body)
    assert result.status_code == HTTPStatus.OK
    assert payload["data"] == [{"id": "ORD-1"}]
    assert payload["meta"] == {"total": 12, "page": 2, "page_size": 5, "total_pages": 3}
    assert payload["links"]["next"] == "https://example.com/orders?page=3&page_size=5"

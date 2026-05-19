import pytest

from mpt_extension_sdk.api import PaginatedResult, Pagination, ValidationError
from mpt_extension_sdk.api.pagination import PaginationLinksBuilder

TOTAL_ITEMS = 25
TOO_LARGE_PAGE_SIZE = "501"


def test_paginated_result_from_pagination():
    pagination = Pagination(page=2, page_size=5)

    result = PaginatedResult.from_pagination(pagination, payload=["item"], total=TOTAL_ITEMS)

    assert result.payload == ["item"]
    assert result.total == TOTAL_ITEMS
    assert result.page == 2
    assert result.page_size == 5


def test_paginated_result_total_pages_zero():
    result = PaginatedResult(payload=[], total=0, page=1, page_size=10)

    assert result.total_pages == 0


def test_pagination_from_query_defaults():
    result = Pagination.from_query({})

    assert result.page == 1
    assert result.page_size == 20


def test_pagination_validates_page_size():
    with pytest.raises(ValidationError) as error_info:
        Pagination.from_query({"page_size": TOO_LARGE_PAGE_SIZE})

    assert error_info.value.errors[0].pointer == "#/page_size"


@pytest.mark.parametrize("query", [{"page": "abc"}, {"page": "0"}])
def test_pagination_validates_page(query):
    with pytest.raises(ValidationError) as error_info:
        Pagination.from_query(query)

    assert error_info.value.errors[0].pointer == "#/page"


def test_pagination_links_first_page():
    result = PaginationLinksBuilder.build(
        "https://example.com/orders", PaginatedResult(payload=[], total=0, page=1, page_size=10)
    )

    assert result["prev"] is None
    assert result["next"] is None
    assert result["last"] == "https://example.com/orders?page=1&page_size=10"


def test_pagination_links_replace_page_params():
    result = PaginationLinksBuilder.build(
        "https://example.com/orders?foo=bar&page=9&page_size=1",
        PaginatedResult(payload=[], total=TOTAL_ITEMS, page=2, page_size=10),
    )

    assert result["self"] == "https://example.com/orders?foo=bar&page=2&page_size=10"
    assert result["first"] == "https://example.com/orders?foo=bar&page=1&page_size=10"
    assert result["prev"] == "https://example.com/orders?foo=bar&page=1&page_size=10"
    assert result["next"] == "https://example.com/orders?foo=bar&page=3&page_size=10"
    assert result["last"] == "https://example.com/orders?foo=bar&page=3&page_size=10"

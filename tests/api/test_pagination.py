import pytest

from mpt_extension_sdk.api import PaginatedResult, Pagination, ValidationError

TOTAL_ITEMS = 25
LARGE_LIMIT = "5000"


def test_paginated_result_from_pagination():
    pagination = Pagination(offset=25, limit=5)

    result = PaginatedResult.from_pagination(pagination, payload=["item"], total=TOTAL_ITEMS)

    assert result.payload == ["item"]
    assert result.total == TOTAL_ITEMS
    assert result.offset == 25
    assert result.limit == 5


def test_pagination_from_query_defaults():
    result = Pagination.from_query({})

    assert result.offset == 0
    assert result.limit == 100


def test_pagination_accepts_large_limit():
    result = Pagination.from_query({"limit": LARGE_LIMIT})

    assert result.limit == int(LARGE_LIMIT)


@pytest.mark.parametrize("query", [{"limit": "abc"}, {"limit": "-1"}])
def test_pagination_validates_limit_format(query):
    with pytest.raises(ValidationError) as error_info:
        Pagination.from_query(query)

    assert error_info.value.errors[0].pointer == "#/limit"


@pytest.mark.parametrize("query", [{"offset": "abc"}, {"offset": "-1"}])
def test_pagination_validates_offset(query):
    with pytest.raises(ValidationError) as error_info:
        Pagination.from_query(query)

    assert error_info.value.errors[0].pointer == "#/offset"


def test_pagination_accepts_count_only_limit():
    result = Pagination.from_query({"limit": "0"})

    assert result.limit == 0

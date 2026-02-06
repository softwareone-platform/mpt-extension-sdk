import pytest

from mpt_extension_sdk.mpt_http.utils import find_first


@pytest.mark.parametrize(
    ("data", "predicate", "default", "expected"),
    [
        ([1, 2, 3, 4], lambda x: x > 2, None, 3),
        ([1, 2, 3], lambda x: x > 5, "not found", "not found"),
    ],
)
def test_find_first(data, predicate, default, expected):
    result = find_first(predicate, data, default=default)

    assert result == expected

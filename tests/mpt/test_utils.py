from mpt_extension_sdk.mpt_http.utils import find_first


def test_find_first_match():
    data = [1, 2, 3, 4]
    result = find_first(lambda x: x > 2, data)
    assert result == 3


def test_find_first_no_match_returns_default():
    data = [1, 2, 3]
    result = find_first(lambda x: x > 5, data, default="not found")
    assert result == "not found"

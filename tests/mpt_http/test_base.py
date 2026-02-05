import warnings

import pytest

from mpt_extension_sdk.mpt_http.base import MPTClient


@pytest.fixture
def mock_api_token():
    return "my-secret-token"


def test_mpt_client(mock_api_token):
    result = MPTClient(base_url="https://api.example", api_token=mock_api_token)

    assert result.api_token == mock_api_token
    assert "Authorization" in result.headers
    assert result.headers["Authorization"] == "Bearer my-secret-token"
    assert "User-Agent" in result.headers


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://api.example", "https://api.example/public/v1/"),
        ("http://api.example/", "http://api.example/public/v1/"),
    ],
)
def test_mpt_client_base_url_handling(base_url, expected_url, mock_api_token):
    result = MPTClient(base_url=base_url, api_token=mock_api_token)

    assert result.base_url == expected_url


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://api.example/v1", "https://api.example/public/v1/"),
        ("http://api.example/v1/", "http://api.example/public/v1/"),
        ("https://api.example/public/v1", "https://api.example/public/v1/"),
        ("https://api.example/public/v1/", "https://api.example/public/v1/"),
    ],
)
def test_mpt_client_deprecated_v1_path(base_url, expected_url, mock_api_token):
    # TODO: Remove after /v1/ migration - added 2025-02-05
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")

        result = MPTClient(base_url=base_url, api_token=mock_api_token)

        assert result.base_url == expected_url
        assert len(warning_list) == 1
        assert issubclass(warning_list[0].category, DeprecationWarning)
        assert "Please use the base URL without version path" in str(warning_list[0].message)


@pytest.mark.parametrize("base_url", ["https://api.example/v1", "https://api.example/v1/"])
def test_mpt_client_join_url(base_url, mock_api_token):
    client = MPTClient(base_url=base_url, api_token=mock_api_token)

    result = client.join_url("/commerce/orders")

    assert result == "https://api.example/public/v1/commerce/orders"

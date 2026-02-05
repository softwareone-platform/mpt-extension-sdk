import json

import pytest
import responses
from requests import Request, Response

from mpt_extension_sdk.mpt_http.base import MPTClient
from mpt_extension_sdk.mpt_http.wrap_http_error import (
    MPTAPIError,
    MPTHttpError,
    MPTMaxRetryError,
    wrap_mpt_http_error,
)


def test_mpt_api_error_str(mock_mpt_api_error_payload):
    error = MPTAPIError(400, mock_mpt_api_error_payload)
    expected_str = (
        f"{mock_mpt_api_error_payload['status']} "
        f"{mock_mpt_api_error_payload['title']} - "
        f"{mock_mpt_api_error_payload['detail']} "
        f"({mock_mpt_api_error_payload['traceId']})\n"
        f"{json.dumps(mock_mpt_api_error_payload['errors'], indent=2)}"
    )
    assert str(error) == expected_str


def test_mpt_api_error_as_plain_text():
    response = Response()
    response.status_code = 504
    response._content = b"upstream request timeout"  # noqa: SLF001
    response.request = Request()

    @wrap_mpt_http_error
    def fail_response():
        response.raise_for_status()

    with pytest.raises(MPTHttpError):
        fail_response()


def test_retry_error_responses(requests_mocker):
    client = MPTClient(base_url="https://test", api_token="token")  # noqa: S106

    @wrap_mpt_http_error
    def fail_response():
        client.get(
            "/504",
        )

    requests_mocker.add(
        responses.GET, "https://test/public/v1/504", body="upstream request timeout", status=504
    )
    with pytest.raises(MPTMaxRetryError):
        fail_response()

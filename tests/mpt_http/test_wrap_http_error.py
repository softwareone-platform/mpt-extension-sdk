import json

from mpt_extension_sdk.mpt_http.wrap_http_error import MPTAPIError


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

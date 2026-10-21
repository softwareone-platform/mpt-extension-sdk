from json import JSONDecodeError

import pytest
from fastapi import Request

from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.errors import ValidationError
from mpt_extension_sdk.api.models.errors import ErrorDetail


@pytest.fixture
def http_request(mocker):
    return mocker.Mock(spec=Request)


async def test_parse_request_body_without_body(http_request):
    http_request.body.return_value = b""

    result = await APIHandlerArgumentsBuilder.parse_request_body(http_request)

    assert result is None
    http_request.json.assert_not_awaited()


async def test_parse_request_body_returns_payload(http_request):
    http_request.body.return_value = b'{"agreementId": "AGR-1"}'
    http_request.json.return_value = {"agreementId": "AGR-1"}

    result = await APIHandlerArgumentsBuilder.parse_request_body(http_request)

    assert result == {"agreementId": "AGR-1"}


@pytest.mark.parametrize(
    "decode_error",
    [
        JSONDecodeError("Expecting value", "{invalid", 1),
        UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte"),
    ],
)
async def test_parse_request_body_rejects_invalid(http_request, decode_error):
    http_request.body.return_value = b"\x80"
    http_request.json.side_effect = decode_error

    with pytest.raises(ValidationError) as exc_info:
        await APIHandlerArgumentsBuilder.parse_request_body(http_request)

    assert exc_info.value.errors == [ErrorDetail(pointer="#", detail="Invalid JSON payload")]

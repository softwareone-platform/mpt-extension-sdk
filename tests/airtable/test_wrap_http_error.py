import pytest
from requests import HTTPError, JSONDecodeError, Response

from mpt_extension_sdk.airtable.wrap_http_error import (
    AirTableAPIError,
    AirTableHttpError,
    wrap_airtable_http_error,
)


def test_airtable_http_error_str_and_repr():
    result = AirTableHttpError(404, "Resource Not Found")

    assert str(result) == "404 - Resource Not Found"
    assert "404 - Resource Not Found" in repr(result)


def test_airtable_api_error_str_and_repr():
    payload = {"error": {"message": "airtable api error"}}

    result = AirTableAPIError(400, payload)

    assert str(result) == "400 - airtable api error"
    assert "airtable api error" in repr(result)


def test_wrap_airtable_http_error_api(mocker):
    @wrap_airtable_http_error
    def airtable_error_func():
        resp = Response()
        resp.status_code = 400
        resp._content = b"bad content"  # noqa: SLF001
        resp.json = mocker.Mock(return_value={"error": {"message": "airtable api error"}})
        raise HTTPError(response=resp)

    with pytest.raises(AirTableAPIError) as exc:
        airtable_error_func()

    assert exc.value.message == "airtable api error"
    assert exc.value.code == 400


def test_wrap_airtable_http_error_non_json(mocker):
    @wrap_airtable_http_error
    def func():
        resp = Response()
        resp.status_code = 500
        resp._content = b"server error"  # noqa: SLF001
        resp.json = mocker.Mock(side_effect=JSONDecodeError("Expecting value", "", 0))
        raise HTTPError(response=resp)

    with pytest.raises(AirTableHttpError) as exc:
        func()

    assert exc.value.status_code == 500
    assert exc.value.content == "server error"

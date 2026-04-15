import httpx
import pytest

from mpt_extension_sdk.runtime.bootstrap.client import register_extension_instance


def test_register_ext_posts_expected_request(mocker):
    response = mocker.Mock(spec=["json", "raise_for_status"])
    response.json.return_value = {"instance": "ok"}
    response.raise_for_status.return_value = None
    post = mocker.patch.object(httpx, "post", autospec=True, return_value=response)

    result = register_extension_instance(
        "https://example.com",
        "EXT-1",
        "token-1",
        {"meta": {"version": "1.0.0"}},
    )

    assert result == {"instance": "ok"}
    post.assert_called_once_with(
        "https://example.com/public/v1/integration/extensions/EXT-1/instances",
        json={"meta": {"version": "1.0.0"}},
        headers={"Authorization": "Bearer token-1", "Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status.assert_called_once_with()


def test_register_ext_instance_propagates_errors(mocker):
    response = mocker.Mock(spec=["raise_for_status"])
    request = mocker.Mock(spec=httpx.Request)
    response = mocker.Mock(spec=httpx.Response)
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=request, response=response
    )
    mocker.patch.object(httpx, "post", autospec=True, return_value=response)

    with pytest.raises(httpx.HTTPStatusError):
        register_extension_instance("https://example.com", "EXT-1", "token-1", {})

import pytest
from mpt_api_client import AsyncMPTClient

from mpt_extension_sdk.services.mpt_api_service.client_factory import build_mpt_client


@pytest.fixture(autouse=True)
def clear_mpt_client_cache():
    build_mpt_client.cache_clear()
    yield
    build_mpt_client.cache_clear()


def test_build_mpt_client_uses_bearer_auth(mocker):
    authentication = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.client_factory.BearerTokenAuthentication",
        autospec=True,
    )
    client = mocker.Mock(spec=AsyncMPTClient)
    from_config = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.client_factory.AsyncMPTClient.from_config",
        autospec=True,
        return_value=client,
    )

    result = build_mpt_client("https://api.example.com", "token-1")

    assert result is client
    authentication.assert_called_once_with("token-1")
    from_config.assert_called_once_with(
        base_url="https://api.example.com",
        authentication=authentication.return_value,
    )

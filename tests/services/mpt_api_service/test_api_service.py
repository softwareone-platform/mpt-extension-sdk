from mpt_api_client import AsyncMPTClient

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService


def test_api_service_composes_expected_services(mocker):  # noqa: WPS218
    client = mocker.AsyncMock(spec=AsyncMPTClient)

    result = MPTAPIService(client)

    assert result.client is client
    assert hasattr(result, "agreements")
    assert hasattr(result, "assets")
    assert hasattr(result, "account_token")
    assert hasattr(result, "installations")
    assert hasattr(result, "products")
    assert hasattr(result, "product_items")
    assert hasattr(result, "orders")
    assert hasattr(result, "subscriptions")
    assert hasattr(result, "tasks")
    assert hasattr(result, "templates")
    assert not hasattr(result, "notifications")


def test_api_service_from_config(mocker):
    client = mocker.AsyncMock(spec=AsyncMPTClient)
    mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.api_service.build_mpt_client",
        autospec=True,
        return_value=client,
    )

    result = MPTAPIService.from_config("https://api.example.com", "token-1")

    assert isinstance(result, MPTAPIService)
    assert result.client is client


async def test_from_auth_context_uses_account_client(mocker, runtime_settings):  # noqa: WPS210
    auth = mocker.Mock(spec=AuthContext)
    client = mocker.AsyncMock(spec=AsyncMPTClient)
    get_runtime_settings = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.api_service.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    token_provider = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.api_service.AccountTokenProvider",
        autospec=True,
    )
    from_token_provider = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.api_service."
        "AccountScopedAsyncMPTClient.from_token_provider",
        autospec=True,
        return_value=client,
    )

    result = await MPTAPIService.from_auth_context("https://api.example.com", auth)

    assert isinstance(result, MPTAPIService)
    assert result.client is client
    get_runtime_settings.assert_called_once_with()
    token_provider.assert_called_once_with(
        runtime_settings=runtime_settings, auth=auth, service_type=MPTAPIService
    )
    from_token_provider.assert_called_once_with(
        base_url="https://api.example.com",
        bootstrap_api_token=runtime_settings.ext_api_key,
        token_provider=token_provider.return_value,
    )

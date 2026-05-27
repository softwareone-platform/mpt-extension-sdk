import datetime as dt

import pytest
from mpt_api_client.http.async_client import AsyncHTTPClient
from mpt_api_client.http.types import Response

from mpt_extension_sdk.api.auth import Account, AccountType, AuthContext
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.account_scoped_client import (
    AccountScopedAsyncHTTPClient,
    AccountScopedAsyncMPTClient,
    AccountTokenProvider,
)
from mpt_extension_sdk.services.mpt_api_service.installation import InstallationService


@pytest.fixture
def account_token_factory():
    def factory(token: str | None = None, expires_at: dt.datetime | None = None) -> AccountToken:
        if expires_at is None:
            expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=10)
        return AccountToken(
            token="account-token" if token is None else token,
            exp=int(expires_at.timestamp()),
            expires_at=expires_at,
        )

    return factory


@pytest.fixture
def token_provider_factory(mocker, account_token_factory, runtime_settings):  # noqa: WPS210
    def factory(account_token: AccountToken | None = None):
        provider_token = account_token_factory() if account_token is None else account_token
        auth = mocker.Mock(
            spec=AuthContext,
            token="request-token",
            extension_id="EXT-1",
            account=Account(id="ACC-1", type=AccountType.CLIENT),
        )
        installations = mocker.Mock(
            spec=["create_token"], create_token=mocker.AsyncMock(return_value=provider_token)
        )
        service_type = mocker.Mock(spec=["from_config"])
        service_type.from_config.return_value = mocker.Mock(
            spec=["installations"], installations=installations
        )
        provider = AccountTokenProvider(
            runtime_settings=runtime_settings, auth=auth, service_type=service_type
        )
        return provider, service_type, installations

    return factory


@pytest.fixture
def provider_tokens_factory():
    async def factory(provider):
        return [await provider.get_token(), await provider.get_token()]

    return factory


@pytest.fixture
def clear_account_token_cache():
    AccountTokenProvider.clear_cache()
    yield
    AccountTokenProvider.clear_cache()


async def test_create_token_query_params(mocker, async_mpt_client, jwt_token_factory):
    token = jwt_token_factory({"exp": 4102444800})
    response = mocker.Mock(spec=Response)
    response.json.return_value = {"token": token}
    http_client = mocker.Mock(spec=["request"], request=mocker.AsyncMock(return_value=response))
    installations = mocker.Mock(
        spec=["path", "http_client"],
        path="/public/v1/integration/installations/-/token",
        http_client=http_client,
    )
    async_mpt_client.integration.installations.return_value = installations

    result = await InstallationService(async_mpt_client).create_token("ACC-1")

    assert result.token == token
    assert result.exp == 4102444800
    assert result.expires_at == dt.datetime.fromtimestamp(4102444800, tz=dt.UTC)
    installations.http_client.request.assert_awaited_once_with(
        "post",
        "/public/v1/integration/installations/-/token",
        query_params={"account.id": "ACC-1"},
    )


async def test_provider_caches_token(
    clear_account_token_cache, runtime_settings, token_provider_factory, provider_tokens_factory
):
    provider, service_type, installations = token_provider_factory()

    result = await provider_tokens_factory(provider)

    assert result == ["account-token", "account-token"]
    service_type.from_config.assert_called_once_with(
        base_url=runtime_settings.mpt_api_base_url, api_token=runtime_settings.ext_api_key
    )
    installations.create_token.assert_awaited_once_with("ACC-1")


def test_mpt_client_uses_refreshing_http_client(mocker):
    token_provider = mocker.Mock(
        spec=["get_token"], get_token=mocker.AsyncMock(return_value="account-token")
    )

    result = AccountScopedAsyncMPTClient.from_token_provider(
        base_url="https://api.example.com",
        bootstrap_api_token="extension-api-key",
        token_provider=token_provider,
    )

    assert isinstance(result.http_client, AccountScopedAsyncHTTPClient)


async def test_http_client_refreshes_each_request(mocker):
    token_provider = mocker.Mock(
        spec=["get_token"],
        get_token=mocker.AsyncMock(side_effect=["account-token-1", "account-token-2"]),
    )
    response = mocker.Mock(spec=Response)
    request = mocker.patch.object(AsyncHTTPClient, "request", autospec=True, return_value=response)
    client = AccountScopedAsyncHTTPClient(
        base_url="https://api.example.com",
        bootstrap_api_token="extension-api-key",
        token_provider=token_provider,
    )

    result = [
        await client.request("get", "/orders/ORD-1", headers={"x-test": "1"}),
        await client.request("get", "/orders/ORD-1", headers={"x-test": "1"}),
    ]

    assert result == [response, response]
    assert token_provider.get_token.await_count == 2
    assert request.await_count == 2
    assert request.await_args_list[0].kwargs["headers"] == {
        "x-test": "1",
        "Authorization": "Bearer account-token-1",
    }
    assert request.await_args_list[1].kwargs["headers"] == {
        "x-test": "1",
        "Authorization": "Bearer account-token-2",
    }

import base64
import datetime as dt
import json

import pytest
from mpt_api_client.http.async_client import AsyncHTTPClient

from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.account_scoped_client import (
    AccountScopedAsyncHTTPClient,
    AccountScopedAsyncMPTClient,
    AccountTokenProvider,
)
from mpt_extension_sdk.services.mpt_api_service.installation import InstallationService


def build_token(exp: int) -> str:
    payload = json.dumps({"exp": exp}).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    return f"header.{encoded_payload}.signature"


def build_account_token(token: str, expires_at: dt.datetime) -> AccountToken:
    return AccountToken(
        token=token,
        exp=int(expires_at.timestamp()),
        expires_at=expires_at,
    )


def build_token_provider(mocker, runtime_settings):  # noqa: WPS210
    """Build a token provider with mocked installation token creation."""
    expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=10)
    account_token = build_account_token("account-token", expires_at)
    auth = mocker.Mock()
    auth.token = "request-token"
    auth.extension_id = "EXT-1"
    auth.account.id = "ACC-1"
    installations = mocker.Mock()
    installations.create_token = mocker.AsyncMock(return_value=account_token)
    service_type = mocker.Mock()
    service_type.from_config.return_value = mocker.Mock(installations=installations)
    provider = AccountTokenProvider(
        runtime_settings=runtime_settings,
        auth=auth,
        service_type=service_type,
    )
    return provider, service_type, installations


async def get_provider_tokens(provider):
    """Request the account token twice."""
    return [await provider.get_token(), await provider.get_token()]


@pytest.fixture
def clear_account_token_cache():
    AccountTokenProvider.clear_cache()
    yield
    AccountTokenProvider.clear_cache()


async def test_create_token_query_params(mocker, async_mpt_client):
    installations = mocker.Mock()
    installations.path = "/public/v1/integration/installations/-/token"
    response = mocker.Mock()
    response.json.return_value = {"token": build_token(4102444800), "exp": 4102444800}
    installations.http_client.request = mocker.AsyncMock(return_value=response)
    async_mpt_client.integration.installations.return_value = installations
    service = InstallationService(async_mpt_client)

    result = await service.create_token("ACC-1")

    assert result.token == build_token(4102444800)
    installations.http_client.request.assert_awaited_once_with(
        "post",
        "/public/v1/integration/installations/-/token",
        query_params={"account.id": "ACC-1"},
    )


async def test_provider_caches_token(clear_account_token_cache, mocker, runtime_settings):
    provider, service_type, installations = build_token_provider(mocker, runtime_settings)

    token_results = await get_provider_tokens(provider)  # act

    assert token_results == ["account-token", "account-token"]
    service_type.from_config.assert_called_once_with(
        base_url=runtime_settings.mpt_api_base_url, api_token=runtime_settings.ext_api_key
    )
    installations.create_token.assert_awaited_once_with("ACC-1")


def test_mpt_client_uses_refreshing_http_client(mocker):
    token_provider = mocker.Mock()
    token_provider.get_token = mocker.AsyncMock(return_value="account-token")

    result = AccountScopedAsyncMPTClient.from_token_provider(
        base_url="https://api.example.com",
        bootstrap_api_token="extension-api-key",
        token_provider=token_provider,
    )

    assert isinstance(result.http_client, AccountScopedAsyncHTTPClient)


async def test_http_client_refreshes_each_request(mocker):
    token_provider = mocker.Mock()
    token_provider.get_token = mocker.AsyncMock(side_effect=["account-token-1", "account-token-2"])
    response = mocker.Mock()
    request = mocker.patch.object(AsyncHTTPClient, "request", autospec=True, return_value=response)
    client = AccountScopedAsyncHTTPClient(
        base_url="https://api.example.com",
        bootstrap_api_token="extension-api-key",
        token_provider=token_provider,
    )

    request_results = [
        await client.request("get", "/orders/ORD-1", headers={"x-test": "1"}),
        await client.request("get", "/orders/ORD-1", headers={"x-test": "1"}),
    ]  # act

    assert request_results == [response, response]
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

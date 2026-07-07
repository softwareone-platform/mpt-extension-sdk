import datetime as dt
from collections.abc import AsyncIterator
from contextlib import aclosing
from functools import partial

import pytest
from httpx import AsyncClient, MockTransport, Request, Response, codes
from mpt_api_client.resources.integration.installations_token import InstallationsToken

from mpt_extension_sdk.api.auth import Account, AccountType, AuthContext
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.account_scoped_client import (
    AccountScopedAuthentication,
    AccountTokenProvider,
    build_account_scoped_mpt_client,
)
from mpt_extension_sdk.services.mpt_api_service.account_token import AccountTokenService


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
        account_token = mocker.Mock(
            spec=["create_token"], create_token=mocker.AsyncMock(return_value=provider_token)
        )
        service_type = mocker.Mock(spec=["from_config"])
        service_type.from_config.return_value = mocker.Mock(
            spec=["account_token"], account_token=account_token
        )
        provider = AccountTokenProvider(
            runtime_settings=runtime_settings, auth=auth, service_type=service_type
        )
        return provider, service_type, account_token

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


async def test_create_token(mocker, async_mpt_client, jwt_token_factory):
    service = async_mpt_client.integration.installations_token.return_value
    token = jwt_token_factory({"exp": 4102444800})
    service.token = mocker.AsyncMock(return_value=InstallationsToken(token=token))

    result = await AccountTokenService(async_mpt_client).create_token("ACC-1")

    assert result.token == token
    assert result.exp == 4102444800
    assert result.expires_at == dt.datetime.fromtimestamp(4102444800, tz=dt.UTC)
    service.token.assert_awaited_once_with("ACC-1")


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


async def test_provider_invalidate_forces_refresh(
    clear_account_token_cache, token_provider_factory
):
    provider, _, installations = token_provider_factory()
    first_token = await provider.get_token()

    provider.invalidate(first_token)

    await provider.get_token()
    assert installations.create_token.await_count == 2


async def test_provider_invalidate_ignores_stale_token(
    clear_account_token_cache, token_provider_factory
):
    provider, _, installations = token_provider_factory()
    await provider.get_token()

    provider.invalidate("already-replaced-token")

    await provider.get_token()
    installations.create_token.assert_awaited_once()


def test_build_client_sets_account_authentication(mocker):
    token_provider = mocker.Mock(
        spec=["get_token"], get_token=mocker.AsyncMock(return_value="account-token")
    )

    result = build_account_scoped_mpt_client(
        base_url="https://api.example.com",
        token_provider=token_provider,
    )

    assert isinstance(result.http_client.httpx_client.auth, AccountScopedAuthentication)
    token_provider.get_token.assert_not_awaited()


async def test_authentication_refreshes_each_request(mocker):
    token_provider = mocker.Mock(
        spec=["get_token"],
        get_token=mocker.AsyncMock(side_effect=["account-token-1", "account-token-2"]),
    )
    authentication = AccountScopedAuthentication(token_provider)

    result = [
        await _apply_authentication(
            authentication,
            Request("GET", "https://api.example.com/orders/ORD-1", headers={"x-test": "1"}),
        ),
        await _apply_authentication(
            authentication,
            Request("GET", "https://api.example.com/orders/ORD-1", headers={"x-test": "1"}),
        ),
    ]

    assert token_provider.get_token.await_count == 2
    assert result[0].headers["Authorization"] == "Bearer account-token-1"
    assert result[1].headers["Authorization"] == "Bearer account-token-2"
    assert result[0].headers["x-test"] == "1"


async def test_auth_flow_retries_once_on_unauthorized(mocker):
    token_provider = mocker.Mock(
        spec=["get_token", "invalidate"],
        get_token=mocker.AsyncMock(side_effect=["revoked-token", "fresh-token"]),
    )
    authentication = AccountScopedAuthentication(token_provider)
    auth_flow = authentication.async_auth_flow(
        Request("GET", "https://api.example.com/orders/ORD-1")
    )

    first_authorization = (await anext(auth_flow)).headers["Authorization"]
    retried_request = await auth_flow.asend(Response(codes.UNAUTHORIZED))

    assert first_authorization == "Bearer revoked-token"
    assert retried_request.headers["Authorization"] == "Bearer fresh-token"
    token_provider.invalidate.assert_called_once_with("revoked-token")
    with pytest.raises(StopAsyncIteration):
        await auth_flow.asend(Response(codes.OK))


async def test_auth_flow_retry_resends_streamed_body(mocker):
    token_provider = mocker.Mock(
        spec=["get_token", "invalidate"],
        get_token=mocker.AsyncMock(side_effect=["revoked-token", "fresh-token"]),
    )
    received = []

    async with AsyncClient(
        transport=MockTransport(partial(_record_request, received)),
        auth=AccountScopedAuthentication(token_provider),
    ) as client:
        response = await client.post("https://api.example.com/files", content=_stream_chunks())

    assert response.status_code == codes.OK
    assert received == [
        ("Bearer revoked-token", b"chunk"),
        ("Bearer fresh-token", b"chunk"),
    ]


async def test_auth_flow_does_not_retry_on_success(mocker):
    token_provider = mocker.Mock(
        spec=["get_token", "invalidate"],
        get_token=mocker.AsyncMock(return_value="account-token"),
    )
    authentication = AccountScopedAuthentication(token_provider)
    auth_flow = authentication.async_auth_flow(
        Request("GET", "https://api.example.com/orders/ORD-1")
    )

    await anext(auth_flow)

    with pytest.raises(StopAsyncIteration):
        await auth_flow.asend(Response(codes.OK))
    token_provider.invalidate.assert_not_called()


async def _stream_chunks() -> AsyncIterator[bytes]:  # noqa: RUF029
    yield b"chunk"


def _record_request(received: list, request: Request) -> Response:
    received.append((request.headers["Authorization"], request.content))
    return Response(codes.UNAUTHORIZED if len(received) == 1 else codes.OK)


async def _apply_authentication(
    authentication: AccountScopedAuthentication, request: Request
) -> Request:
    async with aclosing(authentication.async_auth_flow(request)) as auth_flow:
        return await anext(auth_flow)

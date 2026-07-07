import asyncio
import datetime as dt
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, ClassVar, override

from httpx import Request, Response, codes
from mpt_api_client.auth import Authentication
from mpt_api_client.http.async_client import AsyncHTTPClient

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.settings.runtime import RuntimeSettings

if TYPE_CHECKING:
    from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService

AccountCacheKey = tuple[str, str]
AccountTokenCache = dict[AccountCacheKey, AccountToken]
AccountLockCache = dict[AccountCacheKey, asyncio.Lock]

TOKEN_EXPIRY_LEEWAY_SECONDS = 60


class AccountTokenProvider:  # noqa: WPS214
    """Account-scoped token cache with serialized refreshes per account."""

    _account_token_cache: ClassVar[AccountTokenCache] = {}
    _account_token_locks: ClassVar[AccountLockCache] = {}

    def __init__(
        self,
        *,
        runtime_settings: RuntimeSettings,
        auth: AuthContext,
        service_type: type["MPTAPIService"],
        min_remaining_validity_seconds: int = TOKEN_EXPIRY_LEEWAY_SECONDS,
    ) -> None:
        self._runtime_settings = runtime_settings
        self._auth = auth
        self._service_type = service_type
        self._min_remaining_validity_seconds = min_remaining_validity_seconds

    @property
    def cache_key(self) -> AccountCacheKey:
        """The cache key for the current account."""
        return self._auth.extension_id, self._auth.account.id

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached account tokens and refresh locks."""
        cls._account_token_cache.clear()
        cls._account_token_locks.clear()

    async def get_token(self) -> str:
        """Return a valid account token, refreshing it when needed."""
        cache_key = self.cache_key
        cached_token = self._account_token_cache.get(cache_key)
        if cached_token is not None and self._is_token_valid(cached_token.expires_at):
            return cached_token.token

        lock = self._account_token_locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached_token = self._account_token_cache.get(cache_key)
            if cached_token is not None and self._is_token_valid(cached_token.expires_at):
                return cached_token.token

            account_token = await self._fetch_account_token()
            self._store_token(cache_key, account_token)
            return account_token.token

    def invalidate(self, token: str) -> None:
        """Drop the cached account token when it matches a rejected one.

        Only evicts the cache entry if it still holds the rejected token, so a fresh
        token stored by a concurrent refresh is never discarded.

        Args:
            token: The bearer token rejected by the platform.
        """
        cache_key = self.cache_key
        cached_token = self._account_token_cache.get(cache_key)
        if cached_token is not None and cached_token.token == token:
            self._account_token_cache.pop(cache_key, None)

    async def _fetch_account_token(self) -> AccountToken:
        mpt_api_service = self._service_type.from_config(
            base_url=self._runtime_settings.mpt_api_base_url,
            api_token=self._runtime_settings.ext_api_key,
        )
        return await mpt_api_service.account_token.create_token(self._auth.account.id)

    def _is_token_valid(self, expires_at: dt.datetime) -> bool:
        expected_time = dt.datetime.now(dt.UTC).timestamp() + self._min_remaining_validity_seconds
        return expires_at.timestamp() > expected_time

    def _store_token(self, cache_key: AccountCacheKey, cached: AccountToken) -> None:
        self._account_token_cache[cache_key] = cached
        now = dt.datetime.now(dt.UTC)
        expired_keys = [
            key for key, entry in self._account_token_cache.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._account_token_cache.pop(key, None)
            self._account_token_locks.pop(key, None)


class AccountScopedAuthentication(Authentication):
    """Authentication provider that signs requests with an account-scoped token."""

    # Buffer streamed request bodies before the auth flow so the 401 retry can
    # resend them; one-shot streams would otherwise go out consumed or truncated.
    requires_request_body = True

    def __init__(self, token_provider: AccountTokenProvider) -> None:
        self._token_provider = token_provider

    @override
    async def async_auth_flow(self, request: Request) -> AsyncGenerator[Request, Response]:
        """Attach the current account-scoped bearer token, retrying once on 401.

        A 401 response means the token was revoked before its expiry, so the cached
        token is invalidated and the request is retried once with a fresh one.
        """
        token = await self._token_provider.get_token()
        request.headers["Authorization"] = f"Bearer {token}"
        response = yield request
        if response.status_code == codes.UNAUTHORIZED:
            self._token_provider.invalidate(token)
            token = await self._token_provider.get_token()
            request.headers["Authorization"] = f"Bearer {token}"
            yield request


def build_account_scoped_mpt_client(
    *,
    base_url: str,
    token_provider: AccountTokenProvider,
    timeout: float = 60.0,
) -> AsyncMPTClient:
    """Build an MPT client that authenticates requests with account-scoped tokens."""
    return AsyncMPTClient(
        AsyncHTTPClient(
            base_url=base_url,
            authentication=AccountScopedAuthentication(token_provider),
            timeout=timeout,
        )
    )

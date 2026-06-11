import asyncio
import datetime as dt
from typing import TYPE_CHECKING, Any, ClassVar, Self, override

from mpt_api_client.http.async_client import AsyncHTTPClient
from mpt_api_client.http.query_options import QueryOptions
from mpt_api_client.http.types import HeaderTypes, QueryParam, RequestFiles, Response

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


class AccountTokenProvider:
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
        """Return the cache key for the current account."""
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


class AccountScopedAsyncHTTPClient(AsyncHTTPClient):
    """HTTP client that injects a fresh account-scoped token before every request."""

    def __init__(
        self,
        *,
        base_url: str,
        bootstrap_api_token: str,
        token_provider: AccountTokenProvider,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(base_url=base_url, api_token=bootstrap_api_token, timeout=timeout)
        self._token_provider = token_provider

    @override
    async def request(  # noqa: WPS211
        self,
        method: str,
        url: str,
        *,
        files: RequestFiles | None = None,
        json: Any | None = None,
        query_params: QueryParam | None = None,
        headers: HeaderTypes | None = None,
        json_file_key: str = "_attachment_data",
        force_multipart: bool = False,
        options: QueryOptions | None = None,
    ) -> Response:
        """Perform a request using the current account-scoped token."""
        request_headers = self._get_no_auth_headers(headers)
        token = await self._token_provider.get_token()
        request_headers["Authorization"] = f"Bearer {token}"
        return await super().request(
            method,
            url,
            files=files,
            json=json,
            query_params=query_params,
            headers=request_headers,
            json_file_key=json_file_key,
            force_multipart=force_multipart,
            options=options,
        )

    def _get_no_auth_headers(self, headers: HeaderTypes | None) -> HeaderTypes:
        return {
            key: header_value
            for key, header_value in dict(headers or {}).items()
            if key.lower() != "authorization"
        }


class AccountScopedAsyncMPTClient(AsyncMPTClient):
    """MPT client that refreshes account-scoped tokens in the HTTP layer."""

    @classmethod
    def from_token_provider(
        cls,
        *,
        base_url: str,
        bootstrap_api_token: str,
        token_provider: AccountTokenProvider,
    ) -> Self:
        """Create an account-scoped MPT client."""
        return cls(
            AccountScopedAsyncHTTPClient(
                base_url=base_url,
                bootstrap_api_token=bootstrap_api_token,
                token_provider=token_provider,
            )
        )

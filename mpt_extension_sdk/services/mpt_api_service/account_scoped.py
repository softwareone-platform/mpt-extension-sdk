import asyncio
import base64
import binascii
import datetime as dt
import json
from inspect import isawaitable
from typing import Any, ClassVar

from mpt_api_client.exceptions import MPTAPIError

from mpt_extension_sdk.api import UpstreamServiceError
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.base import BaseService
from mpt_extension_sdk.settings.runtime import RuntimeSettings

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
        runtime_settings: RuntimeSettings,
        account_id: str,
        service_type: type[MPTAPIService] = MPTAPIService,
        min_remaining_validity_seconds: int = TOKEN_EXPIRY_LEEWAY_SECONDS,
    ) -> None:
        self._runtime_settings = runtime_settings
        self._account_id = account_id
        self._service_type = service_type
        self._min_remaining_validity_seconds = min_remaining_validity_seconds

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached account tokens and refresh locks."""
        cls._account_token_cache.clear()
        cls._account_token_locks.clear()

    async def get_token(self) -> str:
        """Return a valid account token, refreshing it when needed."""
        cache_key = self._cache_key
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

    @classmethod
    def _store_token(cls, cache_key: AccountCacheKey, cached: AccountToken) -> None:
        cls._account_token_cache[cache_key] = cached
        now = dt.datetime.now(dt.UTC)
        expired_keys = [
            key for key, entry in cls._account_token_cache.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            cls._account_token_cache.pop(key, None)
            cls._account_token_locks.pop(key, None)

    @property
    def _cache_key(self) -> AccountCacheKey:
        return self._runtime_settings.extension_id, self._account_id

    def _decode_token_expiry(self, token: str) -> dt.datetime:
        token_payload = token.split(".")
        if len(token_payload) < 2:
            raise UpstreamServiceError("Account token is not a well-formed JWT")

        token_claims = token_payload[1]
        token_claims += "=" * ((4 - len(token_claims) % 4) % 4)
        try:
            token_expiry = self._get_exp_from_jwt(token_claims)
        except ValueError as error:
            raise UpstreamServiceError("Account token claims could not be parsed") from error

        return dt.datetime.fromtimestamp(token_expiry, tz=dt.UTC)

    async def _fetch_account_token(self) -> AccountToken:
        mpt_api_service = self._service_type.from_config(
            base_url=self._runtime_settings.mpt_api_base_url,
            api_token=self._runtime_settings.ext_api_key,
        )
        try:
            account_token = await mpt_api_service.installations.create_token(self._account_id)
        except MPTAPIError as error:
            raise UpstreamServiceError(
                f"Failed to fetch account token (upstream {error.status_code})"
            ) from error

        return account_token

    def _get_exp_from_jwt(self, token_claims: str) -> int:
        try:
            decoded_claims = base64.urlsafe_b64decode(token_claims.encode("utf-8")).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as error:
            raise ValueError("Invalid token claims") from error

        try:
            claims = json.loads(decoded_claims)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid token claims") from error

        exp = claims.get("exp")
        if not isinstance(exp, int | float) or exp <= 0:
            raise ValueError("Token claims do not contain an expiration time")

        return int(exp)

    def _is_token_valid(self, expires_at: dt.datetime) -> bool:
        expected_time = dt.datetime.now(dt.UTC).timestamp() + self._min_remaining_validity_seconds
        return expires_at.timestamp() > expected_time


class AccountScopedMPTAPIService(MPTAPIService):
    """MPT API service proxy that refreshes the account token on demand.

    TODO: merge with MPTAPIService once auth flow is unified.
    """

    def __init__(
        self,
        *,
        service_type: type[MPTAPIService],
        base_url: str,
        token_provider: AccountTokenProvider,
    ) -> None:
        self._service_type = service_type
        self._base_url = base_url
        self._token_provider = token_provider
        self._service: MPTAPIService | None = None
        self._service_token = ""

    def __getattr__(self, name: str) -> Any:
        """Proxy all public service access to the current refreshed service instance."""
        service = self._service
        if service is None:
            return AccountScopedServiceProxy(self, name)

        service_attribute = getattr(service, name)
        if isinstance(service_attribute, BaseService):
            return AccountScopedServiceProxy(self, name)

        return service_attribute

    async def refresh(self) -> None:
        """Refresh the current account-scoped API service."""
        token = await self._token_provider.get_token()
        if self._service is not None and token == self._service_token:
            return

        self._service = self._service_type.from_config(base_url=self._base_url, api_token=token)
        self._service_token = token

    async def get_refreshed_attribute(self, name: str) -> Any:
        """Return a service attribute after refreshing the account token when needed."""
        await self.refresh()
        if self._service is None:
            raise RuntimeError("Account-scoped API service could not be initialized")

        return getattr(self._service, name)


class AccountScopedServiceProxy:
    """Proxy a nested MPT service and refresh before each operation."""

    def __init__(self, api_service: AccountScopedMPTAPIService, service_name: str) -> None:
        self._api_service = api_service
        self._service_name = service_name

    def __getattr__(self, name: str) -> Any:
        """Return a callable that refreshes before invoking the nested service method."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            service = await self._api_service.get_refreshed_attribute(self._service_name)
            method = getattr(service, name)
            result = method(*args, **kwargs)
            if isawaitable(result):
                return await result
            return result

        return wrapper

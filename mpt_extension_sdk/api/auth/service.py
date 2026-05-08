import datetime as dt
from typing import Any, cast

from fastapi import Request

from mpt_extension_sdk.api.auth.constants import (
    CLAIM_ACCOUNT_ID,
    CLAIM_ACCOUNT_TYPE,
    CLAIM_EXTENSION_ID,
    CLAIM_MODULES,
)
from mpt_extension_sdk.api.auth.context import Account, AccountType, AuthContext
from mpt_extension_sdk.errors.runtime import ExtRuntimeError
from mpt_extension_sdk.jwt import JWTClaimsError, JWTFormatError, decode_unverified_jwt_claims

TOKEN_EXPIRY_LEEWAY_SECONDS = 30


class AuthenticationError(ExtRuntimeError):
    """Raised when an authenticated request cannot be trusted."""


class RequestAuthenticationService:  # noqa: WPS214
    """Extract auth context from a framework-validated JWT."""

    def authenticate(self, request: Request) -> AuthContext:
        """Return auth context from already validated JWT claims."""
        token = self._extract_bearer_token(request)
        claims = self._decode_jwt_claims(token)
        self._assert_required_claims(claims)
        self._assert_token_not_expiring(claims)
        return self._build_auth_context(claims, token)

    def _assert_required_claims(self, claims: dict[str, Any]) -> None:
        """Ensure the claims needed by SDK contexts are present."""
        self._assert_string_claim(claims, CLAIM_ACCOUNT_ID)
        self._assert_string_claim(claims, CLAIM_EXTENSION_ID)
        self._assert_string_claim(claims, CLAIM_ACCOUNT_TYPE)

    def _assert_string_claim(self, claims: dict[str, Any], claim_name: str) -> None:
        """Ensure the requested claim exists and is a non-empty string."""
        claim_value = claims.get(claim_name)
        if not isinstance(claim_value, str) or not claim_value:
            raise AuthenticationError

    def _assert_token_not_expiring(self, claims: dict[str, Any]) -> None:
        """Ensure the trusted token is not expired or too close to expiring."""
        exp = claims.get("exp")
        if not isinstance(exp, int) or exp <= 0:
            raise AuthenticationError

        expected_time = dt.datetime.now(dt.UTC).timestamp() + TOKEN_EXPIRY_LEEWAY_SECONDS
        if exp <= expected_time:
            raise AuthenticationError

    def _build_auth_context(self, claims: dict[str, Any], token: str) -> AuthContext:
        """Build the normalized auth context from trusted JWT claims."""
        return AuthContext(
            token=token,
            account=Account(
                id=cast(str, claims[CLAIM_ACCOUNT_ID]),
                type=self._build_account_type(claims),
            ),
            extension_id=cast(str, claims[CLAIM_EXTENSION_ID]),
            permissions=self._build_permissions(claims),
        )

    def _build_account_type(self, claims: dict[str, Any]) -> AccountType:
        """Return the typed account type from trusted JWT claims."""
        try:
            return AccountType(cast(str, claims[CLAIM_ACCOUNT_TYPE]))
        except ValueError as error:
            raise AuthenticationError from error

    def _build_permissions(self, claims: dict[str, Any]) -> dict[str, list[str]]:
        """Return the permissions claim as a typed dictionary of module actions."""
        raw_permissions = claims.get(CLAIM_MODULES, {})
        if not isinstance(raw_permissions, dict):
            return {}

        permissions: dict[str, list[str]] = {}
        for module, actions in raw_permissions.items():
            if not isinstance(module, str) or not module:
                return {}
            if not isinstance(actions, list) or not all(
                isinstance(action, str) and action for action in actions
            ):
                return {}
            permissions[module] = list(actions)
        return permissions

    def _decode_jwt_claims(self, token: str) -> dict[str, Any]:
        """Decode trusted JWT claims without re-verifying framework-authenticated tokens."""
        try:
            return decode_unverified_jwt_claims(token)
        except (JWTClaimsError, JWTFormatError) as error:
            raise AuthenticationError from error

    def _extract_bearer_token(self, request: Request) -> str:
        """Extract the bearer token from the Authorization header."""
        authorization = request.headers.get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials:
            raise AuthenticationError
        return credentials

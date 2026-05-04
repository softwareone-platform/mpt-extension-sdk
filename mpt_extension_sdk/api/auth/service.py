import base64
import datetime as dt
import json
from typing import Any, cast

from fastapi import Request

from mpt_extension_sdk.api.auth.constants import (
    CLAIM_ACCOUNT_ID,
    CLAIM_ACCOUNT_TYPE,
    CLAIM_EXTENSION_ID,
    CLAIM_MODULES,
)
from mpt_extension_sdk.api.auth.context import Account, AccountType, AuthContext
from mpt_extension_sdk.api.errors import UnauthorizedError

TOKEN_EXPIRY_LEEWAY_SECONDS = 30


class RequestAuthenticationService:  # noqa: WPS214
    """Extract trusted auth context from an Extension Framework service validated JWT."""

    def authenticate(self, request: Request) -> AuthContext:
        """Return auth context from already validated JWT claims."""
        claims = self._decode_jwt_claims(self._extract_bearer_token(request))
        self._assert_required_claims(claims)
        self._assert_token_not_expiring(claims)
        return self._build_auth_context(claims)

    def _assert_string_claim(self, claims: dict[str, Any], claim_name: str) -> None:
        """Ensure the requested claim exists and is a non-empty string."""
        claim_value = claims.get(claim_name)
        if not isinstance(claim_value, str) or not claim_value:
            raise UnauthorizedError

    def _build_auth_context(self, claims: dict[str, Any]) -> AuthContext:
        """Build the normalized auth context from trusted JWT claims."""
        permissions = self._build_permissions(claims)
        return AuthContext(
            account=Account(
                id=cast(str, claims[CLAIM_ACCOUNT_ID]),
                type=self._build_account_type(claims),
            ),
            extension_id=cast(str, claims[CLAIM_EXTENSION_ID]),
            permissions=permissions,
        )

    def _build_account_type(self, claims: dict[str, Any]) -> AccountType:
        """Return the typed account type from trusted JWT claims."""
        try:
            return AccountType(cast(str, claims[CLAIM_ACCOUNT_TYPE]))
        except ValueError as error:
            raise UnauthorizedError from error

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
        token_parts = token.split(".")
        if len(token_parts) < 2:
            raise UnauthorizedError

        payload = token_parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        try:
            decoded_claims = self._decode_claims_payload(payload)
        except (ValueError, json.JSONDecodeError) as error:
            raise UnauthorizedError from error

        if not isinstance(decoded_claims, dict):
            raise UnauthorizedError
        return cast(dict[str, Any], decoded_claims)

    def _decode_claims_payload(self, payload: str) -> object:
        """Decode the serialized JWT claims payload."""
        decoded_payload = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        return json.loads(decoded_payload)

    def _extract_bearer_token(self, request: Request) -> str:
        """Extract the bearer token from the Authorization header."""
        authorization = request.headers.get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credentials:
            raise UnauthorizedError
        return credentials

    def _assert_required_claims(self, claims: dict[str, Any]) -> None:
        """Ensure the claims needed by SDK contexts are present."""
        self._assert_string_claim(claims, CLAIM_ACCOUNT_ID)
        self._assert_string_claim(claims, CLAIM_EXTENSION_ID)
        self._assert_string_claim(claims, CLAIM_ACCOUNT_TYPE)

    def _assert_token_not_expiring(self, claims: dict[str, Any]) -> None:
        """Ensure the trusted token is not expired or too close to expiring."""
        exp = claims.get("exp")
        if not isinstance(exp, int | float) or exp <= 0:
            raise UnauthorizedError

        expected_time = dt.datetime.now(dt.UTC).timestamp() + TOKEN_EXPIRY_LEEWAY_SECONDS
        if exp <= expected_time:
            raise UnauthorizedError

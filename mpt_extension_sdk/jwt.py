import base64
import binascii
import json
from typing import Any


class JWTFormatError(ValueError):
    """Raised when a token does not contain a JWT claims payload."""


class JWTClaimsError(ValueError):
    """Raised when JWT claims cannot be decoded."""

    def __init__(self, message: str = "Invalid token claims") -> None:
        super().__init__(message)


def decode_unverified_jwt_claims(token: str) -> dict[str, Any]:
    """Decode JWT claims without verifying the token signature."""
    token_parts = token.split(".")
    if len(token_parts) != 3:
        raise JWTFormatError("Token is not a JWT")

    payload = _add_urlsafe_padding(token_parts[1])
    claims = _load_claims(_decode_urlsafe_payload(payload))

    if not isinstance(claims, dict):
        raise JWTClaimsError
    return claims


def _add_urlsafe_padding(payload: str) -> str:
    """Add missing base64 URL-safe padding."""
    return payload + "=" * ((4 - len(payload) % 4) % 4)


def _decode_urlsafe_payload(payload: str) -> str:
    """Decode a base64 URL-safe JWT payload."""
    try:
        return base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise JWTClaimsError from error


def _load_claims(payload: str) -> Any:
    """Load JWT claims JSON."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise JWTClaimsError from error

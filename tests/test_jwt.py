import base64

import pytest

from mpt_extension_sdk.jwt import JWTClaimsError, JWTFormatError, decode_unverified_jwt_claims


@pytest.fixture
def jwt_token_factory():
    def factory(payload: str) -> str:
        encoded_payload = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
        return f"header.{encoded_payload.rstrip('=')}.signature"

    return factory


def test_decode_unverified_jwt_claims(jwt_token_factory):
    token = jwt_token_factory('{"exp": 1234567890}')

    result = decode_unverified_jwt_claims(token)

    assert result == {"exp": 1234567890}


def test_decode_rejects_invalid_format():
    with pytest.raises(JWTFormatError, match="Token is not a JWT"):
        decode_unverified_jwt_claims("invalid-token")


def test_decode_rejects_missing_signature(jwt_token_factory):
    token = jwt_token_factory('{"exp": 1234567890}').rsplit(".", maxsplit=1)[0]

    with pytest.raises(JWTFormatError, match="Token is not a JWT"):
        decode_unverified_jwt_claims(token)


def test_decode_rejects_invalid_payload():
    with pytest.raises(JWTClaimsError, match="Invalid token claims"):
        decode_unverified_jwt_claims("header.invalid_payload.signature")


def test_decode_rejects_invalid_json(jwt_token_factory):
    token = jwt_token_factory("invalid")

    with pytest.raises(JWTClaimsError, match="Invalid token claims"):
        decode_unverified_jwt_claims(token)


def test_decode_rejects_non_object_claims(jwt_token_factory):
    token = jwt_token_factory("[]")

    with pytest.raises(JWTClaimsError, match="Invalid token claims"):
        decode_unverified_jwt_claims(token)

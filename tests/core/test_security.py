import jwt
from django.http import HttpRequest

from mpt_extension_sdk.constants import SECURITY_ALGORITHM
from mpt_extension_sdk.core.security import JWTAuth


def test_jwt_auth_success(mpt_client, mock_auth_payload):
    secret = "auth_secret"
    token = jwt.encode(mock_auth_payload, secret, algorithm=SECURITY_ALGORITHM)

    def secret_callback(client, claims):
        assert client is mpt_client
        assert claims["user_id"] == mock_auth_payload["user_id"]
        return secret

    request = HttpRequest()
    request.client = mpt_client

    auth = JWTAuth(secret_callback)

    claims = auth.authenticate(request, token)

    assert claims == mock_auth_payload
    assert hasattr(request, "jwt_claims")
    assert request.jwt_claims == mock_auth_payload


def test_jwt_auth_no_secret(mpt_client, mock_auth_payload):
    secret = None
    token = jwt.encode(mock_auth_payload, "invalid_value", algorithm=SECURITY_ALGORITHM)

    def secret_callback(client, claims):
        return secret

    request = HttpRequest()
    request.client = mpt_client
    auth = JWTAuth(secret_callback)

    claims = auth.authenticate(request, token)

    assert claims is None
    assert request.jwt_claims is None


def test_jwt_auth_invalid_token(mpt_client):
    secret = "auth_secret"
    invalid_token = "invalid_jwt"

    def secret_callback(client, claims):
        return secret

    request = HttpRequest()
    request.client = mpt_client
    auth = JWTAuth(secret_callback)

    claims = auth.authenticate(request, invalid_token)

    assert claims is None
    assert not hasattr(request, "jwt_claims")

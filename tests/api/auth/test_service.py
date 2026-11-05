import base64
import json

import pytest
from starlette.requests import Request

from mpt_extension_sdk.api.auth import AuthenticationError, RequestAuthenticationService
from mpt_extension_sdk.api.auth.constants import (
    CLAIM_ACCOUNT_ID,
    CLAIM_ACCOUNT_TYPE,
    CLAIM_EXTENSION_ID,
    CLAIM_MODULES,
)


@pytest.fixture
def token_factory(claims_factory):
    def factory(claims=None):
        claims = claims or claims_factory()
        payload = json.dumps(claims).encode("utf-8")
        encoded_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
        return f"header.{encoded_payload}."

    return factory


@pytest.fixture
def claims_factory():
    def factory(modules=None):
        return {
            CLAIM_ACCOUNT_ID: "ACC-1",
            CLAIM_ACCOUNT_TYPE: "Client",
            CLAIM_EXTENSION_ID: "EXT-1",
            CLAIM_MODULES: modules or {},
            "exp": 4102444800,
        }

    return factory


@pytest.fixture
def request_factory(mocker, token_factory):
    def factory(token=None):
        token = token or token_factory()
        return mocker.Mock(spec=Request, headers={"authorization": f"Bearer {token}"})

    return factory


@pytest.fixture
def request_auth_service():
    return RequestAuthenticationService()


def test_authenticate(claims_factory, request_factory, request_auth_service, token_factory):
    token = token_factory(claims_factory({"billing": ["edit", "view"]}))
    request = request_factory(token)

    result = request_auth_service.authenticate(request)

    assert result.token == token
    assert result.account.id == "ACC-1"
    assert result.account.is_client()
    assert result.extension_id == "EXT-1"
    assert result.permissions == {"billing": ["edit", "view"]}


def test_authenticate_missing_token(mocker, request_auth_service):
    request = mocker.Mock(spec=Request, headers={})

    with pytest.raises(AuthenticationError):
        request_auth_service.authenticate(request)


def test_authenticate_no_claim(
    claims_factory, request_factory, request_auth_service, token_factory
):
    claims = claims_factory({"billing": ["edit", "view"]})
    claims.pop(CLAIM_EXTENSION_ID)
    request = request_factory(token_factory(claims))

    with pytest.raises(AuthenticationError):
        request_auth_service.authenticate(request)


def test_authenticate_wrong_account_type(
    claims_factory, request_factory, request_auth_service, token_factory
):
    claims = claims_factory({"billing": ["edit", "view"]})
    claims[CLAIM_ACCOUNT_TYPE] = "fake_account_type"
    request = request_factory(token_factory(claims))

    with pytest.raises(AuthenticationError):
        request_auth_service.authenticate(request)


@pytest.mark.parametrize(
    "modules",
    [
        "billing",
        {"billing": "edit"},
        {"billing": [1]},
        {"": ["edit"]},
    ],
)
def test_authenticate_ignores_invalid_permissions(
    modules, claims_factory, request_factory, request_auth_service, token_factory
):
    token = token_factory(claims_factory(modules))
    request = request_factory(token)

    result = request_auth_service.authenticate(request)

    assert result.permissions == {}


def test_authenticate_rejects_malformed_token(request_factory, request_auth_service):
    request = request_factory("header.not-base64.")

    with pytest.raises(AuthenticationError):
        request_auth_service.authenticate(request)


@pytest.mark.parametrize("exp", [-1, 1777900335])
def test_authenticate_rejects_wrong_exp(
    exp, claims_factory, request_factory, request_auth_service, token_factory
):
    claims = claims_factory()
    claims["exp"] = exp
    request = request_factory(token_factory(claims))

    with pytest.raises(AuthenticationError):
        request_auth_service.authenticate(request)

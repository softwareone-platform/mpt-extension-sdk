import base64
import json

import pytest

from mpt_extension_sdk.api.auth import (
    RequestAuthenticationService,
)
from mpt_extension_sdk.api.auth.constants import (
    CLAIM_ACCOUNT_ID,
    CLAIM_ACCOUNT_TYPE,
    CLAIM_EXTENSION_ID,
    CLAIM_MODULES,
)


def build_token(claims):
    payload = json.dumps(claims).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    return f"header.{encoded_payload}."


def build_claims(modules):
    return {
        CLAIM_ACCOUNT_ID: "ACC-1",
        CLAIM_ACCOUNT_TYPE: "Client",
        CLAIM_EXTENSION_ID: "EXT-1",
        CLAIM_MODULES: modules,
        "exp": 4102444800,
    }


def build_request(mocker, token):
    request = mocker.Mock()
    request.headers = {"authorization": f"Bearer {token}"}
    return request


def test_authenticate_returns_permissions(mocker):
    token = build_token(build_claims({"billing": ["edit", "view"]}))
    request = build_request(mocker, token)

    result = RequestAuthenticationService().authenticate(request)

    assert result.permissions == {"billing": ["edit", "view"]}


@pytest.mark.parametrize(
    "modules",
    [
        "billing",
        {"billing": "edit"},
        {"billing": [1]},
        {"": ["edit"]},
    ],
)
def test_authenticate_ignores_invalid_permissions(mocker, modules):
    token = build_token(build_claims(modules))
    request = build_request(mocker, token)

    result = RequestAuthenticationService().authenticate(request)

    assert result.permissions == {}

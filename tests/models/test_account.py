import datetime as dt

import pytest
from pydantic import ValidationError

from mpt_extension_sdk.models.account import AccountToken


def test_validate_overrides_provided_expires_at():
    exp_timestamp = int(dt.datetime.now(tz=dt.UTC).timestamp())
    payload = {
        "token": "dummy_token",
        "exp": exp_timestamp,
        "expires_at": dt.datetime.fromtimestamp(1234567890, tz=dt.UTC),
    }

    result = AccountToken.model_validate(payload)

    assert result.exp == exp_timestamp
    assert result.expires_at == dt.datetime.fromtimestamp(exp_timestamp, tz=dt.UTC)


def test_validate_uses_provided_exp():
    exp_timestamp = int(dt.datetime.now(tz=dt.UTC).timestamp())
    payload = {
        "token": "invalid_token",
        "exp": exp_timestamp,
    }

    result = AccountToken.model_validate(payload)

    assert result.exp == exp_timestamp
    assert result.expires_at == dt.datetime.fromtimestamp(exp_timestamp, tz=dt.UTC)


def test_validate_token_must_be_string():
    payload = {"token": object(), "exp": 4102444800}

    with pytest.raises(ValidationError, match="Input should be a valid string"):
        AccountToken.model_validate(payload)


def test_validate_exp_must_be_int():
    payload = {
        "token": "dummy_token",
        "exp": "1234567890",
    }

    with pytest.raises(TypeError, match="Account token expiration claim is invalid"):
        AccountToken.model_validate(payload)


def test_validate_requires_exp():
    payload = {"token": "dummy_token"}

    with pytest.raises(TypeError, match="Account token expiration claim is invalid"):
        AccountToken.model_validate(payload)

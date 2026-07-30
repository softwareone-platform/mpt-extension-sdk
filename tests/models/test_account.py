import datetime as dt
import warnings

import pytest
from pydantic import ValidationError

from mpt_extension_sdk.models.account import (
    AccountStatus,
    AccountToken,
    BuyerAccount,
    UnknownAccountStatusWarning,
)


@pytest.fixture
def buyer_account_payload():
    return {"id": "BUY-1234-1234", "name": "Buyer"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Enabled", AccountStatus.ENABLED),
        ("Active", AccountStatus.ACTIVE),
        ("Disabled", AccountStatus.DISABLED),
        ("Deleted", AccountStatus.DELETED),
        ("Unassigned", AccountStatus.UNASSIGNED),
        ("Conflict", AccountStatus.CONFLICT),
        ("Mismatch", AccountStatus.MISMATCH),
        ("active", AccountStatus.ACTIVE),
    ],
)
def test_account_parses_known_status_into_enum(buyer_account_payload, status, expected):
    result = BuyerAccount.model_validate(buyer_account_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_account_keeps_unknown_status_as_string(buyer_account_payload):
    with pytest.warns(UnknownAccountStatusWarning, match="BUY-1234-1234"):
        result = BuyerAccount.model_validate(buyer_account_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, AccountStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_account_defaults_missing_status(buyer_account_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownAccountStatusWarning)

        result = BuyerAccount.model_validate(buyer_account_payload)

    assert result.status is None


def test_account_status_rejects_non_string_lookup():
    with pytest.raises(ValueError, match="not a valid AccountStatus"):
        AccountStatus(0)


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

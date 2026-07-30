import warnings

import pytest

from mpt_extension_sdk.models.subscription import (
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
    UnknownSubscriptionStatusWarning,
)


@pytest.fixture
def subscription_payload():
    return {"id": "SUB-1234-1234", "name": "Subscription"}


@pytest.fixture
def subscription_line_payload():
    return {"id": "SUBL-1234-1234", "quantity": 1, "item": {"id": "ITM-1", "name": "Item"}}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Draft", SubscriptionStatus.DRAFT),
        ("Active", SubscriptionStatus.ACTIVE),
        ("Updating", SubscriptionStatus.UPDATING),
        ("Terminating", SubscriptionStatus.TERMINATING),
        ("Terminated", SubscriptionStatus.TERMINATED),
        ("Expired", SubscriptionStatus.EXPIRED),
        ("Deleted", SubscriptionStatus.DELETED),
        ("active", SubscriptionStatus.ACTIVE),
    ],
)
def test_subscription_parses_known_status(subscription_payload, status, expected):
    result = Subscription.model_validate(subscription_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_subscription_keeps_unknown_status(subscription_payload):
    with pytest.warns(UnknownSubscriptionStatusWarning, match="SUB-1234-1234"):
        result = Subscription.model_validate(subscription_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, SubscriptionStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_subscription_defaults_missing_status(subscription_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownSubscriptionStatusWarning)

        result = Subscription.model_validate(subscription_payload)

    assert result.status is None


def test_subscription_rejects_non_string(subscription_payload):
    with pytest.raises(ValueError, match="not a valid SubscriptionStatus"):
        SubscriptionStatus(0)


def test_subscription_line_parses_known(subscription_line_payload):
    result = SubscriptionLine.model_validate(subscription_line_payload | {"status": "Terminated"})

    assert result.status is SubscriptionStatus.TERMINATED


def test_subscription_line_keeps_unknown(subscription_line_payload):
    with pytest.warns(UnknownSubscriptionStatusWarning, match="Subscription line SUBL-1234-1234"):
        result = SubscriptionLine.model_validate(
            subscription_line_payload | {"status": "UnknownStatus"}
        )

    assert result.status == "UnknownStatus"

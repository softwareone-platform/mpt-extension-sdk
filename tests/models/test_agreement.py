import warnings

import pytest

from mpt_extension_sdk.models.agreement import (
    Agreement,
    AgreementLine,
    AgreementStatus,
    UnknownAgreementStatusWarning,
)


@pytest.fixture
def agreement_payload():
    return {
        "id": "AGR-1234-1234-1234",
        "name": "Agreement",
        "client": {"id": "ACC-1234-4444", "name": "Client"},
        "licensee": {"id": "LCE-1234-1234-1234", "name": "Licensee", "status": "Active"},
        "product": {"id": "PRD-1234-1234", "name": "Product"},
    }


@pytest.fixture
def agreement_line_payload():
    return {
        "id": "ALI-1234-1234-1234-0127",
        "quantity": 10,
        "item": {"id": "ITM-1234-1234-1234-0992", "name": "Item"},
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("New", AgreementStatus.NEW),
        ("Draft", AgreementStatus.DRAFT),
        ("Deleted", AgreementStatus.DELETED),
        ("Provisioning", AgreementStatus.PROVISIONING),
        ("Failed", AgreementStatus.FAILED),
        ("Active", AgreementStatus.ACTIVE),
        ("Updating", AgreementStatus.UPDATING),
        ("Terminated", AgreementStatus.TERMINATED),
        ("active", AgreementStatus.ACTIVE),
    ],
)
def test_agreement_parses_known_status_into_enum(agreement_payload, status, expected):
    result = Agreement.model_validate(agreement_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_agreement_keeps_unknown_status_as_string(agreement_payload):
    with pytest.warns(UnknownAgreementStatusWarning, match="AGR-1234-1234-1234"):
        result = Agreement.model_validate(agreement_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, AgreementStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_agreement_defaults_missing_status(agreement_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownAgreementStatusWarning)

        result = Agreement.model_validate(agreement_payload)

    assert result.status is None


def test_line_parses_known_status_into_enum(agreement_line_payload):
    result = AgreementLine.model_validate(agreement_line_payload | {"status": "active"})

    assert result.status is AgreementStatus.ACTIVE
    assert result.model_dump(mode="json")["status"] == AgreementStatus.ACTIVE.value


def test_line_keeps_unknown_status_as_string(agreement_line_payload):
    with pytest.warns(UnknownAgreementStatusWarning, match="ALI-1234-1234-1234-0127"):
        result = AgreementLine.model_validate(agreement_line_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, AgreementStatus)


def test_line_defaults_missing_status(agreement_line_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownAgreementStatusWarning)

        result = AgreementLine.model_validate(agreement_line_payload)

    assert result.status is None


def test_status_rejects_non_string_lookup():
    with pytest.raises(ValueError, match="not a valid AgreementStatus"):
        AgreementStatus(0)

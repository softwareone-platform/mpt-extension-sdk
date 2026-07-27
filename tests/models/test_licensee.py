import pytest

from mpt_extension_sdk.models.licensee import (
    Licensee,
    LicenseeStatus,
    UnknownLicenseeStatusWarning,
)


@pytest.fixture
def licensee_payload():
    return {"id": "LCE-1234-1234", "name": "Licensee"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Enabled", LicenseeStatus.ENABLED),
        ("Active", LicenseeStatus.ACTIVE),
        ("Disabled", LicenseeStatus.DISABLED),
        ("Deleted", LicenseeStatus.DELETED),
        ("active", LicenseeStatus.ACTIVE),
    ],
)
def test_licensee_parses_known_status_into_enum(licensee_payload, status, expected):
    result = Licensee.model_validate(licensee_payload | {"status": status})

    assert result.status is expected
    assert result.model_dump(mode="json")["status"] == expected.value


def test_licensee_keeps_unknown_status_as_string(licensee_payload):
    with pytest.warns(UnknownLicenseeStatusWarning, match="LCE-1234-1234"):
        result = Licensee.model_validate(licensee_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, LicenseeStatus)
    assert result.model_dump(mode="json")["status"] == "UnknownStatus"


def test_licensee_rejects_non_string_lookup():
    with pytest.raises(ValueError, match="not a valid LicenseeStatus"):
        LicenseeStatus(0)

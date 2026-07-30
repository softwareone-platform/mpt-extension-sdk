import warnings

import pytest

from mpt_extension_sdk.models.installation import (
    Installation,
    InstallationInvitation,
    InstallationInvitationStatus,
    InstallationStatus,
    UnknownInstallationInvitationStatusWarning,
    UnknownInstallationStatusWarning,
)


@pytest.fixture
def installation_payload():
    return {"id": "EXI-1234-1234", "account": {"id": "ACC-1"}, "extension": {"id": "EXT-1"}}


@pytest.fixture
def invitation_payload():
    return {
        "message": "Join",
        "validity": {"period": "7d"},
        "url": "https://example.com/invite",
        "externalId": "EXI-1234-1234",
    }


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Invited", InstallationStatus.INVITED),
        ("Installed", InstallationStatus.INSTALLED),
        ("Uninstalled", InstallationStatus.UNINSTALLED),
        ("Expired", InstallationStatus.EXPIRED),
        ("installed", InstallationStatus.INSTALLED),
    ],
)
def test_installation_parses_known_status(installation_payload, status, expected):
    result = Installation.model_validate(installation_payload | {"status": status})

    assert result.status is expected


def test_installation_keeps_unknown_status(installation_payload):
    with pytest.warns(UnknownInstallationStatusWarning, match="EXI-1234-1234"):
        result = Installation.model_validate(installation_payload | {"status": "UnknownStatus"})

    assert result.status == "UnknownStatus"
    assert not isinstance(result.status, InstallationStatus)


def test_installation_defaults_missing_status(installation_payload):
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownInstallationStatusWarning)

        result = Installation.model_validate(installation_payload)

    assert result.status is None


def test_installation_rejects_non_string():
    with pytest.raises(ValueError, match="not a valid InstallationStatus"):
        InstallationStatus(0)


@pytest.mark.parametrize("status", ["Invited", "invited"])
def test_invitation_parses_known_status(invitation_payload, status):
    result = InstallationInvitation.model_validate(invitation_payload | {"status": status})

    assert result.status is InstallationInvitationStatus.INVITED


def test_invitation_keeps_unknown_status(invitation_payload):
    with pytest.warns(UnknownInstallationInvitationStatusWarning, match="EXI-1234-1234"):
        result = InstallationInvitation.model_validate(
            invitation_payload | {"status": "UnknownStatus"}
        )

    assert result.status == "UnknownStatus"

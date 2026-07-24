import warnings

import pytest

from mpt_extension_sdk.models.status import (
    CaseInsensitiveStrEnum,
    UnknownStatusWarning,
    warn_on_unknown_status,
)


class _SampleStatus(CaseInsensitiveStrEnum):
    """Sample status enum for base-class tests."""

    OPEN = "Open"
    CLOSED = "Closed"


class _SampleStatusWarning(UnknownStatusWarning):
    """Sample unknown-status warning for base-class tests."""


@pytest.mark.parametrize("raw_status", ["Open", "open", "OPEN"])
def test_enum_matches_any_case(raw_status):
    result = _SampleStatus(raw_status)

    assert result is _SampleStatus.OPEN


def test_enum_rejects_non_string():
    with pytest.raises(ValueError, match="not a valid"):
        _SampleStatus(1)


def test_warn_on_unknown_status():
    with pytest.warns(_SampleStatusWarning, match="Widget WID-1"):
        warn_on_unknown_status("Widget", "WID-1", "Missing", _SampleStatus, _SampleStatusWarning)


def test_warn_on_known_status_is_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error", _SampleStatusWarning)

        warn_on_unknown_status(
            "Widget", "WID-1", _SampleStatus.OPEN, _SampleStatus, _SampleStatusWarning
        )  # act

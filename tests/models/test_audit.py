import datetime as dt

import pytest

from mpt_extension_sdk.models.audit import AuditData


def test_audit_timestamp_parses_aware_datetime():
    audit_entry = AuditData(at="2026-07-14T10:00:00Z")  # act

    assert audit_entry.timestamp == dt.datetime(2026, 7, 14, 10, tzinfo=dt.UTC)


def test_audit_timestamp_assumes_utc_when_naive():
    audit_entry = AuditData(at="2026-07-14T10:00:00")  # act

    assert audit_entry.timestamp == dt.datetime(2026, 7, 14, 10, tzinfo=dt.UTC)


@pytest.mark.parametrize("raw_value", ["", "not-a-date", "14/07/2026"])
def test_audit_timestamp_ignores_malformed_values(raw_value):
    audit_entry = AuditData(at=raw_value)  # act

    assert audit_entry.timestamp is None

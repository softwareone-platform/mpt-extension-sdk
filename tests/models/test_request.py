import pytest

from mpt_extension_sdk.models import Request, RequestStatus
from mpt_extension_sdk.models.request import UnknownRequestStatusWarning


def test_request_keeps_unknown_fields():
    payload = {
        "id": "REQ-1671-0642",
        "status": "Querying",
        "externalIds": {"vendor": "ABC-2023"},
        "product": {"id": "PRD-1111-1111-1111", "name": "Microsoft Office 365 NCE"},
    }

    result = Request.from_payload(payload)

    assert (result.status, result.external_ids.vendor, result.to_dict()["product"]) == (
        RequestStatus.QUERYING,
        "ABC-2023",
        {"id": "PRD-1111-1111-1111", "name": "Microsoft Office 365 NCE"},
    )


def test_request_warns_on_unknown_status():
    payload = {"id": "REQ-1671-0642", "status": "Archived"}

    with pytest.warns(UnknownRequestStatusWarning, match="Archived"):
        result = Request.from_payload(payload)

    assert result.status == "Archived"

import httpx
import pytest

from mpt_extension_sdk.core.utils_a import mpt_httpx_client_a
from mpt_extension_sdk.mpt_http.mpt_a import get_agreements_by_3yc_enroll_status_a


@pytest.mark.asyncio()
@pytest.mark.parametrize("status", ["Active", "processing"])
async def test_get_agreements_by_3yc_enroll_status_a(status, httpx_mock):
    json_resp = {
        "$meta": {
            "pagination": {"offset": 0, "limit": 10, "total": 2},
            "omitted": ["termsAndConditions", "certificates", "audit"],
        },
        "data": [
            {
                "id": "AGR-3014-8280-4553",
                "status": "Active",
                "externalIds": {"client": "AGR-12345"},
            },
            {
                "id": "AGR-7374-9057-7434",
                "status": "Active",
                "externalIds": {"client": "", "vendor": "P1005205689"},
            },
        ],
    }

    httpx_mock.add_response(
        method="GET",
        url=httpx.URL(
            "http://localhost:8000/v1/commerce/agreements",
            params={
                f"and(eq(status,{status}),any(parameters.fulfillment,and(eq(externalId,3YCEnrollStatus),"
                "in(displayValue,(REQUESTED,ACCEPTED)))))": None,
                "select": "lines,parameters,subscriptions,product,listing",
                "limit": 10,
                "offset": 0,
            },
        ),
        json=json_resp,
    )

    async with mpt_httpx_client_a() as mpt_client:
        r = await get_agreements_by_3yc_enroll_status_a(
            mpt_client, ("REQUESTED", "ACCEPTED"), status=status
        )

    assert r == [
        {
            "externalIds": {"client": "AGR-12345"},
            "id": "AGR-3014-8280-4553",
            "status": "Active",
        },
        {
            "externalIds": {"client": "", "vendor": "P1005205689"},
            "id": "AGR-7374-9057-7434",
            "status": "Active",
        },
    ]

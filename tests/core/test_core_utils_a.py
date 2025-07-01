import pytest

from mpt_extension_sdk.core.utils_a import mpt_httpx_client_a


@pytest.mark.asyncio()
async def test_mpt_httpx_client_a(httpx_mock):
    httpx_mock.add_response(json={"test": "test"})

    async with mpt_httpx_client_a() as mpt_client:
        response = await mpt_client.get("/test")
        response.raise_for_status()

    assert response.json() == {"test": "test"}

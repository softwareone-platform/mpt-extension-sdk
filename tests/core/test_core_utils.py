from django.conf import settings

from mpt_extension_sdk.core.utils import (
    mpt_httpx_client,
    setup_client,
)
from mpt_extension_sdk.mpt_http.base import MPTClient


def test_setup_client():
    client = setup_client()
    assert isinstance(client, MPTClient)
    assert client.base_url == f"{settings.MPT_API_BASE_URL}/v1/"
    assert client.api_token == settings.MPT_API_TOKEN


def test_mpt_httpx_client(httpx_mock):
    httpx_mock.add_response(json={"test": "test"})

    with mpt_httpx_client() as mpt_client:
        response = mpt_client.get("/test")
        response.raise_for_status()

    assert response.json() == {"test": "test"}

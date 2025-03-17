from django.conf import settings

from mpt_extension_sdk.core.utils import setup_client
from mpt_extension_sdk.mpt_http.base import MPTClient


def test_setup_client():
    client = setup_client()
    assert isinstance(client, MPTClient)
    assert client.base_url == f"{settings.MPT_API_BASE_URL}/v1/"
    assert client.api_token == settings.MPT_API_TOKEN

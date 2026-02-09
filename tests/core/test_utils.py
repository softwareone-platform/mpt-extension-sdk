from django.conf import settings

from mpt_extension_sdk.core.utils import setup_client
from mpt_extension_sdk.mpt_http.base import MPTClient


def test_setup_client():
    result = setup_client()

    assert isinstance(result, MPTClient)
    assert result.base_url == f"{settings.MPT_API_BASE_URL}/public/v1/"
    assert result.api_token == settings.MPT_API_TOKEN

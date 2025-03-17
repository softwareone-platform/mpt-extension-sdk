from django.conf import settings

from mpt_extension_sdk.mpt_http.base import MPTClient


def setup_client():
    return MPTClient(
        f"{settings.MPT_API_BASE_URL}/v1/",
        settings.MPT_API_TOKEN,
    )


def setup_operations_client():
    return MPTClient(
        f"{settings.MPT_API_BASE_URL}/v1/",
        settings.MPT_API_TOKEN_OPERATIONS,
    )

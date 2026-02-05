from django.conf import settings

from mpt_extension_sdk.mpt_http.base import MPTClient


def setup_client():
    """Set up the main client."""
    return MPTClient(settings.MPT_API_BASE_URL, settings.MPT_API_TOKEN)


def setup_operations_client():
    """Set up the operations client."""
    return MPTClient(settings.MPT_API_BASE_URL, settings.MPT_API_TOKEN_OPERATIONS)

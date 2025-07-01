from contextlib import contextmanager

import httpx
from django.conf import settings

from mpt_extension_sdk.constants import USER_AGENT
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


class BearerAuth(httpx.Auth):
    def __init__(self, token=None):
        self.token = token or settings.MPT_API_TOKEN

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


@contextmanager
def mpt_httpx_client():
    client = httpx.Client(
        base_url=f"{settings.MPT_API_BASE_URL}/v1/",
        headers={"User-Agent": USER_AGENT},
        auth=BearerAuth(),
        transport=httpx.HTTPTransport(retries=5),
    )
    try:
        yield client
    finally:
        client.close()

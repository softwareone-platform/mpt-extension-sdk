from contextlib import asynccontextmanager

import httpx
from django.conf import settings

from mpt_extension_sdk.constants import USER_AGENT
from mpt_extension_sdk.core.utils import BearerAuth


@asynccontextmanager
async def mpt_httpx_client_a():
    client = httpx.AsyncClient(
        base_url=f"{settings.MPT_API_BASE_URL}/v1/",
        headers={"User-Agent": USER_AGENT},
        auth=BearerAuth(),
        transport=httpx.AsyncHTTPTransport(retries=5),
    )
    try:
        yield client
    finally:
        await client.aclose()

import pytest
from mpt_api_client.resources import AsyncCommerce, AsyncIntegration

from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient


@pytest.fixture
def async_mpt_client(mocker):
    client = mocker.AsyncMock(spec=AsyncMPTClient)
    client.commerce = mocker.AsyncMock(spec=AsyncCommerce)
    client.integration = mocker.AsyncMock(spec=AsyncIntegration)
    return client

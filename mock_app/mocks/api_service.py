from typing import Any, override

from mpt_extension_sdk.models import Order
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService


class ExtMPTAPIService(MPTAPIService):
    """Mock MPT API service."""

    def __init__(self, client: AsyncMPTClient, *args: Any, **kwargs: Any) -> None:
        super().__init__(client)
        self.orders = MockOrderService(client)


class MockOrderService(OrderService):
    """Mock order service."""

    @override
    async def get_by_id(self, order_id: str) -> Order:
        payload = {
            "id": order_id,
            "status": "Processing",
            "type": "Purchase",
            "agreement": {
                "id": "AGR-111",
                "name": "Test Agreement",
                "client": {"id": "CLT-111", "name": "Test Client"},
                "licensee": {"id": "LIC-111", "name": "Test Licensee", "status": "Active"},
                "parameters": {},
                "product": {"id": "PROD-111", "name": "Test Product"},
            },
            "authorization": {"id": "AUTH-111", "name": "Test Authorization", "currency": "USD"},
            "product": {"id": "PROD-111", "name": "Test Product"},
        }
        return Order.from_payload(payload)

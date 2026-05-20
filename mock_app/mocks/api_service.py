from collections.abc import Mapping
from typing import Any, override

from mpt_extension_sdk.models import Agreement, Order
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.installation import InstallationService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService


class ExtMPTAPIService(MPTAPIService):
    """Mock MPT API service."""

    def __init__(self, client: AsyncMPTClient, *args: Any, **kwargs: Any) -> None:
        super().__init__(client)
        self.agreements = MockAgreementService(client)
        self.installations = MockInstallationService(client)
        self.orders = MockOrderService(client)


class MockAgreementService(AgreementService):
    """Mock agreement service."""

    async def create(self, agreement: Mapping[str, Any] | BaseModel) -> Agreement:
        """Create an agreement."""
        return Agreement.from_payload(agreement)

    async def get_all(self, batch_size: int = 100) -> list[Agreement]:
        """Get all agreements."""
        return [
            Agreement.from_payload({
                "id": f"AGR-{ind}",
                "name": "Test Agreement",
                "client": {"id": f"CLT-11{ind}", "name": "Test Client"},
                "licensee": {"id": f"LIC-11{ind}", "name": "Test Licensee", "status": "Active"},
                "parameters": {},
                "product": {"id": f"PROD-11{ind}", "name": "Test Product"},
            })
            for ind in range(batch_size)
        ]

    @override
    async def get_by_id(self, agreement_id: str) -> Agreement:
        payload = {
            "id": agreement_id,
            "name": "Test Agreement",
            "client": {"id": "CLT-111", "name": "Test Client"},
            "licensee": {"id": "LIC-111", "name": "Test Licensee", "status": "Active"},
            "parameters": {},
            "product": {"id": "PROD-111", "name": "Test Product"},
        }
        return Agreement.from_payload(payload)


class MockInstallationService(InstallationService):
    """Mock installation service."""

    @override
    async def create_token(self, account_id: str) -> AccountToken:
        return AccountToken.from_payload({
            "token": "mock-account-token",
            "exp": 1877516378,
        })


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

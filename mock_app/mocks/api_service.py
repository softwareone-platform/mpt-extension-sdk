from collections.abc import Mapping
from typing import Any, override

from mpt_extension_sdk.models import Agreement, Order
from mpt_extension_sdk.models.account import AccountToken
from mpt_extension_sdk.models.base import BaseModel
from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.account_token import AccountTokenService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.base import PaginatedCollection
from mpt_extension_sdk.services.mpt_api_service.order import OrderService


class ExtMPTAPIService(MPTAPIService):
    """Mock MPT API service."""

    def __init__(self, client: AsyncMPTClient, *args: Any, **kwargs: Any) -> None:
        super().__init__(client)
        self.agreements = MockAgreementService(client)
        self.account_token = MockAccountTokenService(client)
        self.orders = MockOrderService(client)


class MockAccountTokenService(AccountTokenService):
    """Mock account token service."""

    @override
    async def create_token(self, account_id: str) -> AccountToken:
        return AccountToken.from_payload({
            "token": "mock-account-token",
            "exp": 1877516378,
        })


class MockAgreementService(AgreementService):
    """Mock agreement service."""

    async def create(self, agreement: Mapping[str, Any] | BaseModel) -> Agreement:
        """Create an agreement."""
        return Agreement.from_payload(agreement)

    @override
    async def get_all(self, offset: int = 0, limit: int = 100) -> PaginatedCollection[Agreement]:
        """Get agreements using offset pagination."""
        total = 10
        agreements = [
            Agreement.from_payload({
                "id": f"AGR-{ind}",
                "name": "Test Agreement",
                "client": {"id": f"CLT-11{ind}", "name": "Test Client"},
                "licensee": {"id": f"LIC-11{ind}", "name": "Test Licensee", "status": "Active"},
                "parameters": {},
                "product": {"id": f"PROD-11{ind}", "name": "Test Product"},
            })
            for ind in range(offset, min(offset + limit, total))
        ]
        return PaginatedCollection(limit=limit, offset=offset, resources=agreements, total=total)

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

import asyncio

from mpt_extension_sdk.services.mpt_api_service.account_scoped import (
    AccountScopedMPTAPIService,
)
from mpt_extension_sdk.services.mpt_api_service.base import BaseService


class FakeTokenProvider:
    def __init__(self, tokens):
        self.tokens = list(tokens)

    async def get_token(self):
        return self.tokens.pop(0)


class FakeAgreementService(BaseService):
    async def get_by_id(self, agreement_id):
        return {"id": agreement_id, "token": self._client.token}


class FakeMPTAPIService:
    calls = None

    def __init__(self, token):
        self.agreements = FakeAgreementService(type("Client", (), {"token": token})())

    @classmethod
    def from_config(cls, base_url, api_token):
        cls.calls.append((base_url, api_token))
        return cls(api_token)


def test_account_scoped_refreshes_before_calls():
    FakeMPTAPIService.calls = []
    api_service = AccountScopedMPTAPIService(
        service_type=FakeMPTAPIService,
        base_url="https://api.example.com",
        token_provider=FakeTokenProvider(["token-1", "token-2"]),
    )

    result = [
        asyncio.run(api_service.agreements.get_by_id("AGR-1")),
        asyncio.run(api_service.agreements.get_by_id("AGR-1")),
    ]

    assert result == [
        {"id": "AGR-1", "token": "token-1"},
        {"id": "AGR-1", "token": "token-2"},
    ]
    assert FakeMPTAPIService.calls == [
        ("https://api.example.com", "token-1"),
        ("https://api.example.com", "token-2"),
    ]


def test_account_scoped_reuses_valid_client():
    FakeMPTAPIService.calls = []
    api_service = AccountScopedMPTAPIService(
        service_type=FakeMPTAPIService,
        base_url="https://api.example.com",
        token_provider=FakeTokenProvider(["token-1", "token-1"]),
    )

    result = [
        asyncio.run(api_service.agreements.get_by_id("AGR-1")),
        asyncio.run(api_service.agreements.get_by_id("AGR-2")),
    ]

    assert result == [
        {"id": "AGR-1", "token": "token-1"},
        {"id": "AGR-2", "token": "token-1"},
    ]
    assert FakeMPTAPIService.calls == [("https://api.example.com", "token-1")]

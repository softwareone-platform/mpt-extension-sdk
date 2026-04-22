import asyncio
from collections.abc import Callable

import pytest
from mpt_api_client.resources.commerce.agreements import AsyncAgreementsService

from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService


@pytest.fixture
def agreement_service_factory(mocker, async_mpt_client):
    def factory():
        agreements_service = mocker.Mock(spec=AsyncAgreementsService)
        async_mpt_client.commerce.agreements = agreements_service
        return AgreementService(async_mpt_client), agreements_service

    return factory


def test_get_by_id(mocker, agreement_service_factory):
    api_agreement = mocker.Mock(spec=["to_dict"])
    service, agreements_client = agreement_service_factory()
    agreements_client.get = mocker.AsyncMock(spec=Callable, return_value=api_agreement)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.agreement.Agreement.from_payload",
        autospec=True,
        return_value="agreement-model",
    )

    result = asyncio.run(service.get_by_id("AGR-1"))

    assert result == "agreement-model"
    agreements_client.get.assert_awaited_once_with(
        "AGR-1",
        select=[
            "client",
            "seller",
            "buyer",
            "listing",
            "product",
            "subscriptions",
            "assets",
            "lines",
            "parameters",
        ],
    )
    from_payload.assert_called_once_with(api_agreement)


def test_update_calls_agreement_update(mocker, agreement_service_factory):
    service, agreement_client = agreement_service_factory()
    agreement_client.update = mocker.AsyncMock(spec=Callable)

    asyncio.run(service.update("AGR-1", {"status": "processing"}))  # act

    agreement_client.update.assert_awaited_once_with("AGR-1", {"status": "processing"})

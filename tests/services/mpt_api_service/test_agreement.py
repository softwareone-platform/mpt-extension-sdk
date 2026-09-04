from collections.abc import Callable

import pytest
from mpt_api_client.http.mixins import AsyncCollectionMixin
from mpt_api_client.models.meta import Meta, Pagination
from mpt_api_client.models.model_collection import ModelCollection
from mpt_api_client.resources.commerce.agreements import AsyncAgreementsService

from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService


@pytest.fixture
def agreement_service_factory(mocker, async_mpt_client):
    def factory():
        agreements_service = mocker.Mock(spec=AsyncAgreementsService)
        async_mpt_client.commerce.agreements = agreements_service
        return AgreementService(async_mpt_client), agreements_service

    return factory


@pytest.fixture
def agreements_page(mocker):
    def factory(resources, limit=50):
        pagination = Pagination(limit=limit, offset=0, total=len(resources))
        meta = Meta(response=mocker.Mock(), pagination=pagination)
        return ModelCollection(resources=resources, meta=meta)

    return factory


async def test_get_all_selects_nested_objects(mocker, agreement_service_factory, agreements_page):
    api_agreement = mocker.Mock(spec=["to_dict"])
    service, agreements_client = agreement_service_factory()
    query = mocker.create_autospec(AsyncCollectionMixin, instance=True)
    agreements_client.select.return_value = query
    query.fetch_page.return_value = agreements_page([api_agreement])
    mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.agreement.Agreement.from_payload",
        autospec=True,
        return_value="agreement-model",
    )

    result = await service.get_all(limit=50)

    agreements_client.select.assert_called_once_with(
        "assets",
        "buyer",
        "client",
        "licensee",
        "lines",
        "listing",
        "parameters",
        "product",
        "seller",
    )
    assert result.resources == ["agreement-model"]


async def test_get_by_id(mocker, agreement_service_factory):
    api_agreement = mocker.Mock(spec=["to_dict"])
    service, agreements_client = agreement_service_factory()
    agreements_client.get = mocker.AsyncMock(spec=Callable, return_value=api_agreement)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.agreement.Agreement.from_payload",
        autospec=True,
        return_value="agreement-model",
    )

    result = await service.get_by_id("AGR-1")

    assert result == "agreement-model"
    agreements_client.get.assert_awaited_once_with(
        "AGR-1",
        select=[
            "assets",
            "buyer",
            "client",
            "licensee",
            "lines",
            "listing",
            "parameters",
            "product",
            "seller",
            "subscriptions",
        ],
    )
    from_payload.assert_called_once_with(api_agreement)


async def test_update_calls_agreement_update(mocker, agreement_service_factory):
    service, agreement_client = agreement_service_factory()
    agreement_client.update = mocker.AsyncMock(spec=Callable)

    await service.update("AGR-1", {"status": "processing"})  # act

    agreement_client.update.assert_awaited_once_with("AGR-1", {"status": "processing"})

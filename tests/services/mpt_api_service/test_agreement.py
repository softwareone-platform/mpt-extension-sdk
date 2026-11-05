from collections.abc import Callable

import pytest
from mpt_api_client.http.mixins import AsyncCollectionMixin
from mpt_api_client.models.meta import Meta, Pagination
from mpt_api_client.models.model_collection import ModelCollection
from mpt_api_client.resources.commerce.agreements import AsyncAgreementsService

from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.base import PaginatedCollection


@pytest.fixture
def agreement_service_factory(mocker, async_mpt_client):
    def factory():
        agreements_service = mocker.Mock(spec=AsyncAgreementsService)
        async_mpt_client.commerce.agreements = agreements_service
        return AgreementService(async_mpt_client), agreements_service

    return factory


@pytest.fixture
def agreements_page(mocker):
    def factory(resources, limit=50, offset=0, total=None):
        pagination = Pagination(
            limit=limit, offset=offset, total=len(resources) if total is None else total
        )
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


@pytest.fixture
def api_agreements(mocker):
    return [mocker.Mock(spec=["to_dict"]) for _ in range(2)]


@pytest.fixture
def agreements_query(mocker, agreement_service_factory):
    service, agreements_client = agreement_service_factory()
    query = mocker.create_autospec(AsyncCollectionMixin, instance=True)
    agreements_client.select.return_value = query
    mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.agreement.Agreement.from_payload",
        autospec=True,
        side_effect=["agreement-1", "agreement-2"],
    )
    return service, query


async def test_get_all_returns_page_pagination(agreements_query, agreements_page, api_agreements):
    service, query = agreements_query
    query.fetch_page.return_value = agreements_page(api_agreements, limit=2, offset=4, total=10)

    result = await service.get_all(offset=4, limit=2)

    assert result == PaginatedCollection(
        limit=2, offset=4, resources=["agreement-1", "agreement-2"], total=10
    )
    query.fetch_page.assert_awaited_once_with(offset=4, limit=2)


async def test_get_all_falls_back_when_meta_missing(agreements_query, api_agreements):
    service, query = agreements_query
    query.fetch_page.return_value = ModelCollection(resources=api_agreements, meta=None)

    result = await service.get_all(offset=4, limit=2)

    assert result == PaginatedCollection(
        limit=2, offset=4, resources=["agreement-1", "agreement-2"], total=6
    )


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

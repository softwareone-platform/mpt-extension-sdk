import pytest
from mpt_api_client.resources import AsyncCatalog
from mpt_api_client.resources.catalog.items import AsyncItemsService

from mpt_extension_sdk.models import ProductItem
from mpt_extension_sdk.services.mpt_api_service.product import ProductItemService


@pytest.fixture
def product_item_service_factory(mocker, async_mpt_client):
    def factory():
        items_client = mocker.Mock(spec=AsyncItemsService)
        catalog_client = mocker.Mock(spec=AsyncCatalog)
        catalog_client.items = items_client
        async_mpt_client.catalog = catalog_client
        return ProductItemService(async_mpt_client), items_client

    return factory


async def test_get_items_returns_empty_without_ids(mocker, product_item_service_factory):
    service, items_client = product_item_service_factory()
    iterate_all = mocker.patch.object(service, "_iterate_all", autospec=True)

    result = await service.get_product_one_time_items_by_ids("PROD-1", [])

    assert result == []
    items_client.filter.assert_not_called()
    iterate_all.assert_not_called()


async def test_get_items_filters_and_collects(mocker, product_item_service_factory):
    service, items_client = product_item_service_factory()
    filtered_collection = mocker.Mock(spec=["iterate"])
    items_client.filter.return_value = filtered_collection
    iterate_all = mocker.patch.object(
        service, "_iterate_all", autospec=True, return_value=["item-1", "item-2"]
    )

    result = await service.get_product_one_time_items_by_ids("PROD-1", ["ITEM-1", "ITEM-2"])

    assert result == ["item-1", "item-2"]
    items_client.filter.assert_called_once_with(mocker.ANY)
    iterate_all.assert_awaited_once_with(filtered_collection, ProductItem)

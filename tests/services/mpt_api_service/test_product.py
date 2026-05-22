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
    paginate = mocker.patch.object(service, "_paginate", autospec=True)

    result = await service.get_product_one_time_items_by_ids("PROD-1", [])

    assert result == []
    items_client.filter.assert_not_called()
    paginate.assert_not_called()


async def test_get_items_filters_and_collects(mocker, product_item_service_factory):
    service, items_client = product_item_service_factory()
    filtered_collection = mocker.Mock(spec=["fetch_page"])
    items_client.filter.return_value = filtered_collection
    paginate = mocker.patch.object(
        service,
        "_paginate",
        autospec=True,
        return_value=mocker.Mock(resources=["item-1", "item-2"]),
    )

    result = await service.get_product_one_time_items_by_ids("PROD-1", ["ITEM-1", "ITEM-2"])

    assert result == ["item-1", "item-2"]
    items_client.filter.assert_called_once_with(mocker.ANY)
    paginate.assert_awaited_once_with(filtered_collection, ProductItem, limit=2)


async def test_get_items_chunks_when_over_max_page_size(  # noqa: WPS210
    mocker, product_item_service_factory
):
    service, items_client = product_item_service_factory()
    filtered_collections = [mocker.Mock(spec=["fetch_page"]) for _ in range(3)]
    items_client.filter.side_effect = filtered_collections
    chunk_resources = [
        [f"item-{idx}" for idx in range(100)],
        [f"item-{idx}" for idx in range(100, 200)],
        [f"item-{idx}" for idx in range(200, 250)],
    ]
    paginate = mocker.patch.object(
        service,
        "_paginate",
        autospec=True,
        side_effect=[mocker.Mock(resources=resources) for resources in chunk_resources],
    )
    item_ids = [f"ITEM-{idx}" for idx in range(250)]

    result = await service.get_product_one_time_items_by_ids("PROD-1", item_ids)

    expected_resources = [entry for chunk in chunk_resources for entry in chunk]
    assert result == expected_resources
    assert items_client.filter.call_count == 3
    assert paginate.await_count == 3
    paginate.assert_any_await(filtered_collections[0], ProductItem, limit=100)
    paginate.assert_any_await(filtered_collections[1], ProductItem, limit=100)
    paginate.assert_any_await(filtered_collections[2], ProductItem, limit=50)

import asyncio
from collections.abc import Callable

import pytest

from mpt_extension_sdk.services.mpt_api_service.asset import AssetService


@pytest.fixture
def asset_client_mock(mocker, async_mpt_client):
    def factory():
        asset_client = mocker.Mock(spec=["create", "update", "get"])
        order_asset_client = mocker.Mock(spec=["create"])
        async_mpt_client.commerce.assets = asset_client
        async_mpt_client.commerce.orders.assets = mocker.Mock(
            spec=Callable,
            return_value=order_asset_client,
        )
        return AssetService(async_mpt_client), asset_client, order_asset_client

    return factory


def test_create(mocker, asset_client_mock):
    api_asset = mocker.Mock(spec=["id"])
    service, asset_client, _ = asset_client_mock()
    asset_client.create = mocker.AsyncMock(spec=Callable, return_value=api_asset)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.asset.Asset.from_payload",
        autospec=True,
        return_value="asset-model",
    )

    result = asyncio.run(service.create({"name": "AST-1"}))

    assert result == "asset-model"
    asset_client.create.assert_awaited_once_with({"name": "AST-1"})
    from_payload.assert_called_once_with(api_asset)


def test_create_order_asset(mocker, asset_client_mock):
    api_asset = mocker.Mock(spec=["id"])
    service, _, order_asset_client = asset_client_mock()
    order_asset_client.create = mocker.AsyncMock(spec=Callable, return_value=api_asset)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.asset.Asset.from_payload",
        autospec=True,
        return_value="asset-model",
    )

    result = asyncio.run(service.create_order_asset("ORD-1", {"name": "AST-1"}))

    assert result == "asset-model"
    order_asset_client.create.assert_awaited_once_with({"name": "AST-1"})
    from_payload.assert_called_once_with(api_asset)


def test_update(mocker, asset_client_mock):
    api_asset = mocker.Mock(spec=["id"])
    service, asset_client, _ = asset_client_mock()
    asset_client.update = mocker.AsyncMock(spec=Callable, return_value=api_asset)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.asset.Asset.from_payload",
        autospec=True,
        return_value="asset-model",
    )

    result = asyncio.run(service.update("AST-1", {"description": "fake"}))

    assert result == "asset-model"
    asset_client.update.assert_awaited_once_with("AST-1", {"description": "fake"})
    from_payload.assert_called_once_with(api_asset)

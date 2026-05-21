from collections.abc import Callable

import pytest
from mpt_api_client.resources import AsyncCommerce
from mpt_api_client.resources.commerce.orders import AsyncOrdersService

from mpt_extension_sdk.services.api_client_v2.mpt_api_client import AsyncMPTClient
from mpt_extension_sdk.services.mpt_api_service.order import OrderService


@pytest.fixture
def order_service_factory(mocker):
    def factory():
        orders_client = mocker.Mock(spec=AsyncOrdersService)
        commerce_client = mocker.Mock(spec=AsyncCommerce)
        commerce_client.orders = orders_client
        client = mocker.Mock(spec=AsyncMPTClient)
        client.commerce = commerce_client
        return OrderService(client), orders_client

    return factory


async def test_get_by_id(mocker, order_service_factory):
    api_order = mocker.Mock(spec=["to_dict"])
    service, orders_client = order_service_factory()
    orders_client.get = mocker.AsyncMock(spec=Callable, return_value=api_order)
    from_payload = mocker.patch(
        "mpt_extension_sdk.services.mpt_api_service.order.Order.from_payload",
        autospec=True,
        return_value="order-model",
    )

    result = await service.get_by_id("ORD-1")

    assert result == "order-model"
    orders_client.get.assert_awaited_once_with(
        "ORD-1",
        select=[
            "agreement",
            "agreement.authorizations",
            "agreement.client",
            "agreement.licensee",
            "agreement.lines",
            "agreement.parameters",
            "assets",
            "authorization",
            "externalIds",
            "lines",
            "lines.asset",
            "lines.subscription",
            "parameters",
            "product",
            "seller",
            "subscriptions",
            "template",
        ],
    )
    from_payload.assert_called_once_with(api_order)


async def test_complete_calls_orders_complete(mocker, order_service_factory):
    service, orders_client = order_service_factory()
    orders_client.complete = mocker.AsyncMock(spec=Callable)
    template = {"id": "TPL-1"}

    await service.complete("ORD-1", template, attributes={"status": "completed"})  # act

    orders_client.complete.assert_awaited_once_with(
        "ORD-1",
        {"template": template, "status": "completed"},
    )


async def test_update_calls_orders_update(mocker, order_service_factory):
    service, orders_client = order_service_factory()
    orders_client.update = mocker.AsyncMock(spec=Callable)

    await service.update("ORD-1", {"status": "processing"})  # act

    orders_client.update.assert_awaited_once_with("ORD-1", {"status": "processing"})


async def test_query_calls_orders_query(mocker, order_service_factory):
    service, orders_client = order_service_factory()
    orders_client.query = mocker.AsyncMock(spec=Callable)

    await service.query("ORD-1", {"reason": "missing-data"})  # act

    orders_client.query.assert_awaited_once_with("ORD-1", {"reason": "missing-data"})


async def test_fail_calls_orders_fail(mocker, order_service_factory):
    service, orders_client = order_service_factory()
    orders_client.fail = mocker.AsyncMock(spec=Callable)

    await service.fail(
        "ORD-1",
        {"message": "failed"},
        attributes={"reason": "validation-error"},
    )  # act

    orders_client.fail.assert_awaited_once_with(
        "ORD-1",
        {"reason": "validation-error", "statusNotes": {"message": "failed"}},
    )

from mpt_extension_sdk.pipeline.context.event import EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


def test_order_context_exposes_order_id(
    mocker, logger, runtime_settings, order_factory, auth_context
):
    context = OrderContext(
        logger=logger,
        meta=EventMetadata(
            event_id="EVT-1",
            object_id="ORD-1",
            object_type="Order",
            task_id="TASK-1",
        ),
        mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        auth=auth_context,
        order=order_factory("ORD-99"),
    )

    result = context.order_id

    assert result == "ORD-99"


async def test_order_context_refreshes_order(
    mocker, logger, runtime_settings, order_factory, auth_context
):
    service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
    service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory("ORD-2"))
    context = OrderContext(
        logger=logger,
        meta=EventMetadata(
            event_id="EVT-1",
            object_id="ORD-1",
            object_type="Order",
            task_id="TASK-1",
        ),
        mpt_api_service=service,
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        auth=auth_context,
        order=order_factory("ORD-1"),
    )

    await context.refresh_order()  # act

    assert context.order.id == "ORD-2"
    service.orders.get_by_id.assert_awaited_once_with("ORD-1")

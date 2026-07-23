from collections.abc import Callable

import pytest

from mpt_extension_sdk.pipeline.context.event import EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.pipeline.decorators import refresh_order
from mpt_extension_sdk.pipeline.step import BaseStep
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


class SampleStep(BaseStep):
    @refresh_order
    async def decorated(self, ctx):
        return ctx

    @refresh_order
    async def failing(self, ctx):
        raise RuntimeError("boom")

    async def process(self, ctx):
        return ctx


async def test_refresh_order(mocker, logger, runtime_settings, order_factory, auth_context):
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
        order=order_factory(),
    )
    context.refresh_order = mocker.AsyncMock(spec=Callable)

    result = await SampleStep().decorated(context)

    assert result == context
    context.refresh_order.assert_awaited_once_with()


async def test_refresh_order_on_failure(
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
        order=order_factory(),
    )
    context.refresh_order = mocker.AsyncMock(spec=Callable)

    with pytest.raises(RuntimeError, match="boom"):
        await SampleStep().failing(context)

    context.refresh_order.assert_not_awaited()

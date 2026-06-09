from collections.abc import Callable

import pytest

from mpt_extension_sdk.decorators import with_operations_mpt_api_service
from mpt_extension_sdk.pipeline.context.event import EventMetadata
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService


class FakeMPTAPIService(MPTAPIService):
    """Subclass used to verify the decorator honors the configured service type."""


@pytest.fixture
def order_event_context_factory(mocker, runtime_settings, order_factory):
    def factory(ops_account_id="ACC-OPS"):
        ext_settings = mocker.Mock(spec=["mpt_ops_account_id"])
        ext_settings.mpt_ops_account_id = ops_account_id
        return OrderContext(
            logger=mocker.Mock(),
            meta=EventMetadata(
                event_id="EVT-1",
                object_id="ORD-1",
                object_type="Order",
                task_id="TASK-1",
            ),
            mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
            ext_settings=ext_settings,
            runtime_settings=runtime_settings,
            order=order_factory(),
        )

    return factory


async def test_with_operations_attaches_ops_service(  # noqa: WPS210
    mocker, runtime_settings, order_event_context_factory
):
    ctx = order_event_context_factory()
    ops_service = mocker.AsyncMock(spec=MPTAPIService)
    from_account_id = mocker.patch.object(
        MPTAPIService, "from_account_id", return_value=ops_service, autospec=True
    )
    original_mpt_api_service = ctx.mpt_api_service
    inner_handler = mocker.AsyncMock(spec=Callable)
    event = {"id": "EVT-1"}

    await with_operations_mpt_api_service()(inner_handler)(event, ctx)

    assert ctx.ops_mpt_api_service is ops_service
    assert ctx.mpt_api_service is original_mpt_api_service
    inner_handler.assert_awaited_once_with(event, ctx)
    from_account_id.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url, account_id="ACC-OPS"
    )


async def test_with_operations_custom_settings_attr(
    mocker, runtime_settings, order_event_context_factory
):
    ctx = order_event_context_factory()
    ctx.ext_settings = mocker.Mock(spec=["ops_account"])
    ctx.ext_settings.ops_account = "ACC-CUSTOM"
    ops_service = mocker.AsyncMock(spec=MPTAPIService)
    from_account_id = mocker.patch.object(
        MPTAPIService, "from_account_id", return_value=ops_service, autospec=True
    )
    inner_handler = mocker.AsyncMock(spec=Callable)

    await with_operations_mpt_api_service(settings_attr="ops_account")(inner_handler)(
        {"id": "EVT-1"}, ctx
    )

    assert ctx.ops_mpt_api_service is ops_service
    from_account_id.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url,
        account_id="ACC-CUSTOM",
    )


async def test_with_operations_uses_custom_service_type(
    mocker, runtime_settings, order_event_context_factory
):
    ctx = order_event_context_factory()
    ops_service = mocker.AsyncMock(spec=FakeMPTAPIService)
    from_account_id = mocker.patch.object(
        FakeMPTAPIService, "from_account_id", return_value=ops_service
    )
    inner_handler = mocker.AsyncMock(spec=Callable)

    await with_operations_mpt_api_service(service_type=FakeMPTAPIService)(inner_handler)(
        {"id": "EVT-1"}, ctx
    )

    assert ctx.ops_mpt_api_service is ops_service
    from_account_id.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url, account_id="ACC-OPS"
    )


async def test_with_operations_missing_ctx_raises(mocker):
    mocker.patch.object(MPTAPIService, "from_account_id", autospec=True)
    inner_handler = mocker.AsyncMock(spec=Callable)

    with pytest.raises(TypeError, match="BaseContext"):
        await with_operations_mpt_api_service()(inner_handler)({"id": "EVT-1"})

    inner_handler.assert_not_awaited()


async def test_with_operations_missing_setting_raises(
    mocker, runtime_settings, order_event_context_factory
):
    ctx = order_event_context_factory()
    ctx.ext_settings = mocker.Mock(spec=[])
    mocker.patch.object(MPTAPIService, "from_account_id", autospec=True)
    inner_handler = mocker.AsyncMock()

    with pytest.raises(AttributeError):
        await with_operations_mpt_api_service()(inner_handler)({"id": "EVT-1"}, ctx)

    inner_handler.assert_not_awaited()

import datetime as dt
from contextlib import contextmanager

import pytest

from mpt_extension_sdk.api.auth import AuthContext, AuthenticationError
from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.pipeline.context.schedule import ScheduleContext
from mpt_extension_sdk.pipeline.factory import (
    RouteContextFactory,
    build_api_context,
    build_context,
)
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


class FakeAuthAPIService:
    from_auth_context = None
    from_vendor_account = None


@contextmanager
def event_context_scope():
    corr_token = correlation_id_ctx.set("corr-1")
    task_token = task_id_ctx.set("task-ctx")
    try:
        yield
    finally:
        correlation_id_ctx.reset(corr_token)
        task_id_ctx.reset(task_token)


@pytest.fixture
def auth(mocker):
    return mocker.Mock(spec=AuthContext, extension_id="EXT-1")


@pytest.fixture(autouse=True)
def factory_settings(mocker, runtime_settings):
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=mocker.AsyncMock(spec=BaseExtensionSettings),
    )


@pytest.fixture
def vendor_service(mocker):
    service = mocker.AsyncMock(spec=MPTAPIService)
    FakeAuthAPIService.from_vendor_account = mocker.AsyncMock(return_value=service)
    return service


@pytest.fixture
def account_service(mocker, vendor_service):
    service = mocker.AsyncMock(spec=MPTAPIService)
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=service)
    return service


@pytest.fixture
def order_service_factory(mocker, order_factory, vendor_service):
    def factory(order_id="ORD-1"):
        service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
        service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory(order_id))
        FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=service)
        return service

    return factory


async def test_build_context_returns_order_context(
    logger, event_factory, order_service_factory, auth
):
    order_service_factory()

    result = await build_context(
        event_factory("Order", "ORD-1"),
        logger,
        auth=auth,
        mpt_api_service_type=FakeAuthAPIService,
    )

    assert isinstance(result, OrderContext)
    assert result.meta.event_id == "EVT-1111-1112"
    assert result.meta.object_id == "ORD-1"
    assert result.meta.object_type == "Order"


async def test_build_context_returns_agreement_context(
    mocker, logger, event_factory, agreement_factory, auth, vendor_service
):
    service = mocker.AsyncMock(
        spec=MPTAPIService, agreements=mocker.AsyncMock(spec=AgreementService)
    )
    service.agreements.get_by_id = mocker.AsyncMock(return_value=agreement_factory("AGR-1"))
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=service)

    result = await build_context(
        event_factory("Agreement", "AGR-1"),
        logger,
        auth=auth,
        mpt_api_service_type=FakeAuthAPIService,
    )

    assert isinstance(result, AgreementContext)
    assert result.meta.object_type == "Agreement"


async def test_build_ctx_rejects_unsupported_obj_type(logger, event_factory, auth, account_service):
    with pytest.raises(RuntimeError, match="Unsupported context type: Subscription"):
        await build_context(
            event_factory("Subscription", "SUB-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )


async def test_build_context_carries_contextvars(
    logger, event_factory, order_service_factory, auth
):
    order_service_factory()

    with event_context_scope():
        result = await build_context(
            event_factory("Order", "ORD-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )

        assert result.meta.correlation_id == "corr-1"
        assert result.meta.task_id == "task-ctx"


async def test_build_context_uses_auth_context(
    logger, runtime_settings, event_factory, order_service_factory, auth
):
    order_service_factory()

    result = await build_context(
        event_factory("Order", "ORD-1"),
        logger,
        auth=auth,
        mpt_api_service_type=FakeAuthAPIService,
    )

    assert result.auth is auth
    FakeAuthAPIService.from_auth_context.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url,
        auth=auth,
    )


async def test_build_context_rejects_mismatched_ext_id(
    logger, event_factory, auth, account_service
):
    auth.extension_id = "EXT-2"

    with pytest.raises(AuthenticationError):
        await build_context(
            event_factory("Order", "ORD-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )

    FakeAuthAPIService.from_auth_context.assert_not_awaited()


async def test_build_schedule_context(logger, task_service, auth, task_event, account_service):
    factory = RouteContextFactory.from_service_type(FakeAuthAPIService)
    enqueued_at = dt.datetime(2026, 8, 11, 17, 4, tzinfo=dt.UTC)

    result = await factory.build_schedule_context(
        schedule_id="agreements.sync",
        task_id="TSK-1",
        handler_logger=logger,
        auth=auth,
        task_service=task_service,
        event=task_event,
    )

    assert isinstance(result, ScheduleContext)
    assert (result.meta.schedule_id, result.meta.task_id, result.task.id) == (
        "agreements.sync",
        "TSK-1",
        "TSK-1",
    )
    assert (result.meta.event_id, result.meta.enqueue_time) == (task_event.id, enqueued_at)


async def test_event_context_exposes_vendor_service(
    logger, runtime_settings, event_factory, order_service_factory, auth, vendor_service
):
    order_service_factory()

    result = await build_context(
        event_factory("Order", "ORD-1"),
        logger,
        auth=auth,
        mpt_api_service_type=FakeAuthAPIService,
    )

    assert result.vendor_mpt_api_service is vendor_service
    FakeAuthAPIService.from_vendor_account.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url
    )


async def test_api_context_exposes_vendor_service(
    mocker, logger, auth, account_service, vendor_service
):
    result = await build_api_context(
        auth_context=auth,
        request_context=mocker.Mock(spec=AuthenticatedRequestContext),
        handler_logger=logger,
        mpt_api_service_type=FakeAuthAPIService,
    )

    assert result.vendor_mpt_api_service is vendor_service


async def test_schedule_context_exposes_vendor_service(
    logger, task_service, auth, task_event, account_service, vendor_service
):
    factory = RouteContextFactory.from_service_type(FakeAuthAPIService)

    result = await factory.build_schedule_context(
        schedule_id="agreements.sync",
        task_id="TSK-1",
        handler_logger=logger,
        auth=auth,
        task_service=task_service,
        event=task_event,
    )

    assert result.vendor_mpt_api_service is vendor_service

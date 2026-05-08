import asyncio
from contextlib import contextmanager

import pytest

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.pipeline.factory import build_context
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


class FakeAuthAPIService:
    from_auth_context = None


@contextmanager
def event_context_scope():
    corr_token = correlation_id_ctx.set("corr-1")
    task_token = task_id_ctx.set("task-ctx")
    try:
        yield
    finally:
        correlation_id_ctx.reset(corr_token)
        task_id_ctx.reset(task_token)


def test_build_context_returns_order_context(
    mocker, logger, runtime_settings, event_factory, order_factory
):
    auth = mocker.Mock()
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    fake_service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
    fake_service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory("ORD-1"))
    fake_extension_settings = mocker.AsyncMock(spec=BaseExtensionSettings)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=fake_extension_settings,
    )
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=fake_service)

    result = asyncio.run(
        build_context(
            event_factory("Order", "ORD-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )
    )

    assert isinstance(result, OrderContext)
    assert result.meta.event_id == "EVT-1111-1112"
    assert result.meta.object_id == "ORD-1"
    assert result.meta.object_type == "Order"


def test_build_context_returns_agreement_context(
    mocker, logger, runtime_settings, event_factory, agreement_factory
):
    auth = mocker.Mock(spec=AuthContext)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    fake_extension_settings = mocker.AsyncMock(spec=BaseExtensionSettings)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=fake_extension_settings,
    )
    fake_service = mocker.AsyncMock(
        spec=MPTAPIService, agreements=mocker.AsyncMock(spec=AgreementService)
    )
    fake_service.agreements.get_by_id = mocker.AsyncMock(return_value=agreement_factory("AGR-1"))
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=fake_service)

    result = asyncio.run(
        build_context(
            event_factory("Agreement", "AGR-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )
    )

    assert isinstance(result, AgreementContext)
    assert result.meta.object_type == "Agreement"


def test_build_ctx_rejects_unsupported_obj_type(mocker, logger, runtime_settings, event_factory):
    auth = mocker.Mock(spec=AuthContext)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings",
        autospec=True,
        return_value=runtime_settings,
    )
    fake_extension_settings = mocker.AsyncMock(spec=BaseExtensionSettings)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        autospec=True,
        return_value=fake_extension_settings,
    )
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=mocker.AsyncMock())

    with pytest.raises(RuntimeError, match="Unsupported context type: Subscription"):
        asyncio.run(
            build_context(
                event_factory("Subscription", "SUB-1"),
                logger,
                auth=auth,
                mpt_api_service_type=FakeAuthAPIService,
            )
        )


def test_build_context_carries_contextvars(
    mocker, logger, runtime_settings, event_factory, order_factory
):
    auth = mocker.Mock()
    fake_service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
    fake_service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory("ORD-1"))
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=fake_service)
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_runtime_settings", return_value=runtime_settings
    )
    mocker.patch(
        "mpt_extension_sdk.pipeline.factory.get_extension_settings",
        return_value=mocker.AsyncMock(),
    )

    with event_context_scope():
        result = asyncio.run(
            build_context(
                event_factory("Order", "ORD-1"),
                logger,
                auth=auth,
                mpt_api_service_type=FakeAuthAPIService,
            )
        )

        assert result.meta.correlation_id == "corr-1"
        assert result.meta.task_id == "task-ctx"


def test_build_context_uses_auth_context(
    mocker, logger, runtime_settings, event_factory, order_factory
):
    auth = mocker.Mock(spec=AuthContext)
    service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
    service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory("ORD-1"))
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
    FakeAuthAPIService.from_auth_context = mocker.AsyncMock(return_value=service)

    result = asyncio.run(
        build_context(
            event_factory("Order", "ORD-1"),
            logger,
            auth=auth,
            mpt_api_service_type=FakeAuthAPIService,
        )
    )

    assert result.auth is auth
    FakeAuthAPIService.from_auth_context.assert_awaited_once_with(
        base_url=runtime_settings.mpt_api_base_url,
        auth=auth,
    )

import asyncio

import pytest

from mpt_extension_sdk.errors.runtime import ConfigError
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.base import ExecutionMetadata
from mpt_extension_sdk.pipeline.context.factory import get_context_by_type
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.agreement import AgreementService
from mpt_extension_sdk.services.mpt_api_service.order import OrderService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


def test_order_context_exposes_order_id(mocker, logger, runtime_settings, order_factory):
    context = OrderContext(
        logger=logger,
        meta=ExecutionMetadata(
            event_id="EVT-1",
            object_id="ORD-1",
            object_type="Order",
            task_id="TASK-1",
        ),
        mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        order=order_factory("ORD-99"),
    )

    result = context.order_id

    assert result == "ORD-99"


def test_agreement_context_exposes_agreement_id(
    mocker, logger, runtime_settings, agreement_factory
):
    context = AgreementContext(
        logger=logger,
        meta=ExecutionMetadata(
            event_id="EVT-1",
            object_id="AGR-1",
            object_type="Agreement",
            task_id="TASK-1",
        ),
        mpt_api_service=mocker.AsyncMock(spec=MPTAPIService),
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        agreement=agreement_factory("AGR-99"),
    )

    result = context.agreement_id

    assert result == "AGR-99"


def test_order_context_refreshes_order(mocker, logger, runtime_settings, order_factory):
    service = mocker.AsyncMock(spec=MPTAPIService, orders=mocker.AsyncMock(spec=OrderService))
    service.orders.get_by_id = mocker.AsyncMock(return_value=order_factory("ORD-2"))
    context = OrderContext(
        logger=logger,
        meta=ExecutionMetadata(
            event_id="EVT-1",
            object_id="ORD-1",
            object_type="Order",
            task_id="TASK-1",
        ),
        mpt_api_service=service,
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        order=order_factory("ORD-1"),
    )

    result = asyncio.run(context.refresh_order())

    assert result is None
    assert context.order.id == "ORD-2"
    service.orders.get_by_id.assert_awaited_once_with("ORD-1")


def test_agreement_context_refreshes_agreement(mocker, logger, runtime_settings, agreement_factory):
    service = mocker.AsyncMock(
        spec=MPTAPIService, agreements=mocker.AsyncMock(spec=AgreementService)
    )
    service.agreements.get_by_id = mocker.AsyncMock(return_value=agreement_factory("AGR-2"))
    context = AgreementContext(
        logger=logger,
        meta=ExecutionMetadata(
            event_id="EVT-1",
            object_id="AGR-1",
            object_type="Agreement",
            task_id="TASK-1",
        ),
        mpt_api_service=service,
        ext_settings=mocker.AsyncMock(spec=BaseExtensionSettings),
        runtime_settings=runtime_settings,
        agreement=agreement_factory("AGR-1"),
    )

    result = asyncio.run(context.refresh_agreement())

    assert result is None
    assert context.agreement.id == "AGR-2"
    service.agreements.get_by_id.assert_awaited_once_with("AGR-1")


def test_get_ctx_by_type_returns_order_context():
    result = get_context_by_type("Order")

    assert result is OrderContext


def test_get_context_by_type():
    result = get_context_by_type("Agreement")

    assert result is AgreementContext


def test_get_ctx_by_type_rejects_unsupported_type():
    with pytest.raises(ConfigError, match="Unsupported object type: Subscription"):
        get_context_by_type("Subscription")

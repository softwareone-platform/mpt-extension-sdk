from contextlib import contextmanager

import pytest

from mpt_extension_sdk.pipeline.builders import EventContextBuilder
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.logging import correlation_id_ctx, task_id_ctx
from mpt_extension_sdk.settings.account import AccountSettings


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
def order_resources(resources, order_factory):
    resources.mpt_api_service.orders.get_by_id.return_value = order_factory("ORD-1")
    return resources


async def test_build_returns_order_context(logger, event_factory, order_resources):
    builder = EventContextBuilder(event=event_factory("Order", "ORD-1"), handler_logger=logger)

    result = await builder.build(order_resources)

    assert isinstance(result, OrderContext)
    assert (result.meta.event_id, result.meta.object_id, result.meta.object_type) == (
        "EVT-1111-1112",
        "ORD-1",
        "Order",
    )
    order_resources.mpt_api_service.orders.get_by_id.assert_awaited_once_with("ORD-1")


async def test_build_returns_agreement_context(logger, event_factory, agreement_factory, resources):
    resources.mpt_api_service.agreements.get_by_id.return_value = agreement_factory("AGR-1")
    builder = EventContextBuilder(event=event_factory("Agreement", "AGR-1"), handler_logger=logger)

    result = await builder.build(resources)

    assert isinstance(result, AgreementContext)
    assert result.meta.object_type == "Agreement"


async def test_build_rejects_unsupported_obj_type(logger, event_factory, resources):
    builder = EventContextBuilder(
        event=event_factory("Subscription", "SUB-1"), handler_logger=logger
    )

    with pytest.raises(RuntimeError, match="Unsupported context type: Subscription"):
        await builder.build(resources)


async def test_build_carries_contextvars(logger, event_factory, order_resources):
    builder = EventContextBuilder(event=event_factory("Order", "ORD-1"), handler_logger=logger)

    with event_context_scope():
        result = await builder.build(order_resources)

    assert (result.meta.correlation_id, result.meta.task_id) == ("corr-1", "task-ctx")


async def test_build_sets_account_settings(logger, event_factory, order_resources):
    builder = EventContextBuilder(event=event_factory("Order", "ORD-1"), handler_logger=logger)

    result = await builder.build(order_resources)

    assert result.account_settings == AccountSettings()

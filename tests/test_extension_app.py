from dataclasses import dataclass

import pytest

from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.base import (
    ContextAdapter,
    ExecutionContext,
    ExecutionMetadata,
)
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.runtime.models import MetaConfig
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


def test_ext_router_registers_non_task_route(dummy_handler, extension_router):
    extension_router.route(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)

    result = extension_router.routes[0]

    assert len(extension_router.routes) == 1
    assert result.name == "purchase"
    assert result.path == "/events/orders/purchase"
    assert result.event == "OrderPurchased"
    assert result.task_based is False


def test_ext_router_registers_task_route(dummy_handler, extension_router):
    extension_router.task_route(path="/change", name="change", event="OrderChanged")(dummy_handler)

    result = extension_router.routes[0]

    assert result.path == "/events/orders/change"
    assert result.task_based is True


def test_ext_router_rejects_duplicate_name(dummy_handler, extension_router):
    extension_router.route(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.route(path="/other", name="purchase", event="OrderChanged")

    with pytest.raises(ValueError, match="Route name 'purchase' is already registered"):
        action(dummy_handler)


def test_ext_router_rejects_duplicate_path(dummy_handler, extension_router):
    extension_router.route(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.route(path="/purchase", name="change", event="OrderChanged")

    with pytest.raises(
        ValueError,
        match="Route path '/events/orders/purchase' is already registered",
    ):
        action(dummy_handler)


def test_ext_router_rejects_duplicate_event(dummy_handler, extension_router):
    extension_router.route(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.route(path="/other", name="change", event="OrderPurchased")

    with pytest.raises(ValueError, match="Route event 'OrderPurchased' is already registered"):
        action(dummy_handler)


def test_ext_router_rejects_blank_name(dummy_handler, extension_router):
    action = extension_router.route(path="/purchase", name="   ", event="OrderPurchased")

    with pytest.raises(ValueError, match="Route name cannot be empty"):
        action(dummy_handler)


def test_ext_router_rejects_blank_event(dummy_handler, extension_router):
    action = extension_router.route(path="/purchase", name="purchase", event="   ")

    with pytest.raises(ValueError, match="Route event cannot be empty"):
        action(dummy_handler)


def test_ext_app_include_router_applies_prefix(dummy_handler, extension_router):
    app = ExtensionApp(prefix="/api/v1")
    extension_router.route(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)

    result = app.include_router(extension_router)

    assert result is None
    assert app.routes[0].path == "/api/v1/events/orders/purchase"


def test_ext_app_to_meta_config(dummy_handler, extension_router):
    app = ExtensionApp(prefix="/api/v1")
    extension_router.task_route(path="/change", name="change", event="OrderChanged")(dummy_handler)
    app.include_router(extension_router)

    result = app.to_meta_config()

    assert isinstance(result, MetaConfig)
    assert result.events[0].event == "OrderChanged"
    assert result.events[0].path == "/api/v1/events/orders/change"
    assert result.events[0].task is True


def test_ext_app_rejects_invalid_service_type():
    with pytest.raises(TypeError, match="mpt_api_service_type must inherit from MPTAPIService"):
        ExtensionApp(mpt_api_service_type=object)


def test_ext_app_rejects_invalid_context_type():
    with pytest.raises(TypeError, match="must inherit from 'OrderContext'"):
        ExtensionApp(order_context_type=dict)


def test_ext_app_build_ctx_returns_unadapted_ctx(mocker, logger, runtime_settings, order_factory):
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
        order=order_factory(),
    )

    result = ExtensionApp().build_context(context)

    assert isinstance(result, ExecutionContext)
    assert result is context


@dataclass(kw_only=True)
class CustomOrderContext(OrderContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        result = cls(**ctx.__dict__)
        result.marker = "adapted"
        return result


def test_ext_app_build_context_adapts_order_ctx(mocker, logger, runtime_settings, order_factory):
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
        order=order_factory(),
    )

    result = ExtensionApp(order_context_type=CustomOrderContext).build_context(context)

    assert isinstance(result, CustomOrderContext)
    assert result.marker == "adapted"


class BadOrderContext(OrderContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return "invalid"


def test_ext_app_build_ctx_invalid_return_type(mocker, logger, runtime_settings, order_factory):
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
        order=order_factory(),
    )

    with pytest.raises(TypeError, match="must return BadOrderContext"):
        ExtensionApp(order_context_type=BadOrderContext).build_context(context)


class WrongOrderAdapter(OrderContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return AgreementContext(
            logger=ctx.logger,
            meta=ctx.meta,
            mpt_api_service=ctx.mpt_api_service,
            account_settings=ctx.account_settings,
            ext_settings=ctx.ext_settings,
            runtime_settings=ctx.runtime_settings,
            agreement=object(),
        )


def test_ext_app_build_ctx_rejects_wrong_subtype(mocker, logger, runtime_settings, order_factory):
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
        order=order_factory(),
    )

    with pytest.raises(TypeError, match="must return WrongOrderAdapter"):
        ExtensionApp(order_context_type=WrongOrderAdapter).build_context(context)

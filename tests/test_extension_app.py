from dataclasses import dataclass

import pytest

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.context import BaseContext, ContextAdapter
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.pipeline.context.agreement import AgreementContext
from mpt_extension_sdk.pipeline.context.event import (
    EventMetadata,
)
from mpt_extension_sdk.pipeline.context.order import OrderContext
from mpt_extension_sdk.routing import (
    APIRouter,
    EventDeliveryMode,
    EventRouteDefinition,
)
from mpt_extension_sdk.routing.models import RouteType
from mpt_extension_sdk.runtime.models import MetaConfig
from mpt_extension_sdk.services.mpt_api_service import MPTAPIService
from mpt_extension_sdk.settings.extension import BaseExtensionSettings


def test_event_router_registers_non_task_route(dummy_handler, extension_router):
    extension_router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)

    result = extension_router.routes[0]

    assert len(extension_router.routes) == 1
    assert (
        result.name,
        result.path,
        result.route_type,
        result.event,
        result.delivery_mode,
    ) == (
        "purchase",
        "/events/orders/purchase",
        RouteType.EVENT,
        "OrderPurchased",
        EventDeliveryMode.EVENT,
    )


def test_event_router_registers_task_route(dummy_handler, extension_router):
    extension_router.task(path="/change", name="change", event="OrderChanged")(dummy_handler)

    result = extension_router.routes[0]

    assert result.path == "/events/orders/change"
    assert result.delivery_mode == EventDeliveryMode.TASK


def test_event_router_rejects_duplicate_name(dummy_handler, extension_router):
    extension_router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.event(path="/other", name="purchase", event="OrderChanged")

    with pytest.raises(ValueError, match="Route name 'purchase' is already registered"):
        action(dummy_handler)


def test_event_router_rejects_duplicate_path(dummy_handler, extension_router):
    extension_router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.event(path="/purchase", name="change", event="OrderChanged")

    with pytest.raises(
        ValueError,
        match="Route path '/events/orders/purchase' is already registered",
    ):
        action(dummy_handler)


def test_event_router_rejects_duplicate_event(dummy_handler, extension_router):
    extension_router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)
    action = extension_router.event(path="/other", name="change", event="OrderPurchased")

    with pytest.raises(ValueError, match="Route event 'OrderPurchased' is already registered"):
        action(dummy_handler)


def test_event_router_rejects_blank_name(dummy_handler, extension_router):
    action = extension_router.event(path="/purchase", name="   ", event="OrderPurchased")

    with pytest.raises(ValueError, match="Route name cannot be empty"):
        action(dummy_handler)


def test_event_router_rejects_blank_event(dummy_handler, extension_router):
    with pytest.raises(ValueError, match="Route event cannot be empty"):
        extension_router.event(path="/purchase", name="purchase", event="   ")


def test_ext_app_include_router_applies_prefix(dummy_handler, extension_router):
    app = ExtensionApp(prefix="/api/v1")
    extension_router.event(path="/purchase", name="purchase", event="OrderPurchased")(dummy_handler)

    app.include_router(extension_router)  # act

    assert app.routes[0].path == "/api/v1/events/orders/purchase"


def test_meta_config_ignores_non_event_routes(dummy_handler):
    event_router = EventRouter(prefix="/events/orders")
    api_router = APIRouter(prefix="/api")
    app = ExtensionApp(prefix="/api/v1")
    event_router.task(path="/change", name="change", event="OrderChanged")(dummy_handler)
    api_router.endpoint(path="/healthz", name="healthz")(dummy_handler)
    app.include_router(event_router)
    app.include_router(api_router)

    result = app.to_meta_config()

    assert isinstance(result, MetaConfig)
    assert len(result.events) == 1
    assert result.events[0].event == "OrderChanged"
    assert result.events[0].path == "/api/v1/events/orders/change"
    assert result.events[0].task is True


def test_ext_app_rejects_invalid_service_type():
    with pytest.raises(TypeError, match="mpt_api_service_type must inherit from MPTAPIService"):
        ExtensionApp(mpt_api_service_type=object)


def test_ext_app_build_ctx_returns_unadapted_ctx(
    mocker, logger, runtime_settings, order_factory, dummy_handler
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
        order=order_factory(),
    )
    route = EventRouteDefinition(
        name="purchase",
        path="/purchase",
        route_type=RouteType.EVENT,
        callback=dummy_handler,
        event="OrderPurchased",
        delivery_mode=EventDeliveryMode.EVENT,
    )

    result = ExtensionApp().build_context(route, context)

    assert isinstance(result, BaseContext)
    assert result is context


@dataclass(kw_only=True)
class CustomOrderContext(OrderContext, ContextAdapter):
    marker: str = ""

    @classmethod
    def from_context(cls, ctx):
        return cls(**ctx.__dict__, marker="adapted")


def test_ext_app_build_context_adapts_order_ctx(
    mocker, logger, runtime_settings, order_factory, dummy_handler
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
        order=order_factory(),
    )
    route = EventRouteDefinition(
        name="purchase",
        path="/purchase",
        route_type=RouteType.EVENT,
        callback=dummy_handler,
        event="OrderPurchased",
        delivery_mode=EventDeliveryMode.EVENT,
        context_adapter_type=CustomOrderContext,
    )

    result = ExtensionApp().build_context(route, context)

    assert isinstance(result, CustomOrderContext)
    assert result.marker == "adapted"


class BadOrderContext(OrderContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return "invalid"


def test_ext_app_build_ctx_invalid_return_type(
    mocker, logger, runtime_settings, order_factory, dummy_handler
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
        order=order_factory(),
    )
    route = EventRouteDefinition(
        name="purchase",
        path="/purchase",
        route_type=RouteType.EVENT,
        callback=dummy_handler,
        event="OrderPurchased",
        delivery_mode=EventDeliveryMode.EVENT,
        context_adapter_type=BadOrderContext,
    )

    with pytest.raises(
        TypeError,
        match=r"BadOrderContext\.from_context must return BadOrderContext",
    ):
        ExtensionApp().build_context(route, context)


class WrongOrderAdapter(ContextAdapter):
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


def test_ext_app_build_ctx_rejects_wrong_subtype(
    mocker, logger, runtime_settings, order_factory, dummy_handler
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
        order=order_factory(),
    )
    route = EventRouteDefinition(
        name="purchase",
        path="/purchase",
        route_type=RouteType.EVENT,
        callback=dummy_handler,
        event="OrderPurchased",
        delivery_mode=EventDeliveryMode.EVENT,
        context_adapter_type=WrongOrderAdapter,
    )

    with pytest.raises(TypeError, match="must inherit from 'OrderContext'"):
        ExtensionApp().build_context(route, context)

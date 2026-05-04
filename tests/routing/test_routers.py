from collections.abc import Callable

import pytest

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing.enums import EventDeliveryMode, HTTPMethod, RouteType
from mpt_extension_sdk.routing.routers import APIRouter, PlugRouter, ScheduleRouter
from mpt_extension_sdk.schemas import BaseSchema


class FakePayloadSchema(BaseSchema):
    """Dummy payload schema for API router tests."""

    name: str


class FakeCustomAdapter(ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return cls()


@pytest.fixture
def route_handler(mocker):
    return mocker.Mock(spec=Callable)


def test_router_rejects_invalid_adapter():
    with pytest.raises(TypeError, match="must implement 'ContextAdapter'"):
        EventRouter(context_adapter_type=dict)


def test_event_router_event_router_ctx_adapter(route_handler):
    router = EventRouter(prefix="/events", context_adapter_type=FakeCustomAdapter)
    decorator = router.event(path="orders", name="purchase", event="OrderPurchased")

    decorator(route_handler)  # act

    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/events/orders"
    assert route.route_type == RouteType.EVENT
    assert route.delivery_mode == EventDeliveryMode.EVENT
    assert route.context_adapter_type is FakeCustomAdapter


def test_event_router_task_ctx_adapter_override(route_handler):
    router = EventRouter(prefix="/events", context_adapter_type=FakeCustomAdapter)

    result = router.task(
        path="/orders/purchase",
        name="purchase-task",
        event="OrderPurchased",
        context_adapter_type=None,
    )(route_handler)

    route = router.routes[0]
    assert result is route_handler
    assert route.path == "/events/orders/purchase"
    assert route.delivery_mode == EventDeliveryMode.TASK
    assert route.context_adapter_type is None


def test_event_router_rejects_empty_event_name():
    router = EventRouter(prefix="/events")

    with pytest.raises(ValueError, match="Route event cannot be empty"):
        router.event(path="orders", name="purchase", event="   ")


def test_api_router_registers_post_and_body(route_handler):
    router = APIRouter(prefix="/api")

    result = router.post(
        path="orders",
        name="orders-create",
        body_validator=FakePayloadSchema,
    )(route_handler)

    assert result is route_handler
    route = router.routes[0]
    assert route.method == HTTPMethod.POST
    assert route.body_validator_type is FakePayloadSchema


def test_api_router_allows_same_path_diff_methods(route_handler):
    router = APIRouter(prefix="/api")
    router.get(path="orders", name="orders-list")(route_handler)
    router.post(path="orders", name="orders-create")(route_handler)

    result = router.routes

    assert len(result) == 2


def test_api_router_rejects_duplicate_method_path(route_handler):
    router = APIRouter(prefix="/api")
    router.get(path="orders", name="orders-list")(route_handler)
    action = router.get(path="orders", name="orders-list-copy")

    with pytest.raises(
        ValueError,
        match="Route path '/api/orders' is already registered for method 'GET'",
    ):
        action(route_handler)


def test_schedule_router_registers_handler(route_handler):
    router = ScheduleRouter(prefix="/schedule")

    result = router.schedule(path="daily", name="daily-sync")(route_handler)

    assert result is route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/schedule/daily"
    assert route.name == "daily-sync"
    assert route.route_type == RouteType.SCHEDULE


def test_plug_router_registers_handler(route_handler):
    router = PlugRouter(prefix="/plug")

    result = router.plug(path="assets", name="assets")(route_handler)

    assert result is route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/plug/assets"
    assert route.name == "assets"
    assert route.route_type == RouteType.PLUG

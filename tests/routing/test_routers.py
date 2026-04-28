from collections.abc import Callable

import pytest

from mpt_extension_sdk import EventRouter
from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing import APIRouter, PlugRouter, ScheduleRouter
from mpt_extension_sdk.routing.models import EventDeliveryMode, RouteType


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


@pytest.mark.parametrize(
    ("prefix", "path", "expected"),
    [
        ("", "orders", "/orders"),
        ("   ", "/orders", "/orders"),
        ("/", "/orders", "/orders"),
        ("/events/", "/", "/events"),
        ("events", "orders", "/events/orders"),
        ("/events", "/orders", "/events/orders"),
    ],
)
def test_api_router_normalizes_prefix_and_path(prefix, path, expected, route_handler):
    router = APIRouter(prefix=prefix)

    router.endpoint(path=path, name="orders")(route_handler)  # act

    assert router.routes[0].path == expected


def test_api_router_rejects_empty_path():
    router = APIRouter(prefix="/events")

    with pytest.raises(ValueError, match="Route path cannot be empty"):
        router.endpoint(path="   ", name="orders")


def test_prefixed_routes_returns_prefixed_copies():
    router = APIRouter(prefix="/api")

    # BL
    @router.endpoint(path="orders", name="orders")
    def mock_handler():  # noqa: WPS430
        """Mock handler."""

    result = router.prefixed_routes("/v1")

    assert len(result) == 1
    assert result[0].path == "/v1/api/orders"
    assert result[0].name == "orders"
    route = router.routes[0]
    assert route.path == "/api/orders"
    assert result[0] is not route


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


def test_api_router_registers_endpoint(route_handler):
    router = APIRouter(prefix="/api")

    result = router.endpoint(path="orders", name="orders")(route_handler)

    assert result is route_handler
    assert len(router.routes) == 1
    route = router.routes[0]
    assert route.path == "/api/orders"
    assert route.name == "orders"
    assert route.route_type == RouteType.API


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

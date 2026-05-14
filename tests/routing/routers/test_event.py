import pytest

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing import EventDeliveryMode, EventRouter, RouteType


class FakeCustomAdapter(ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return cls()


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

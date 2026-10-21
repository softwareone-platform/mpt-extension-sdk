import pytest

from mpt_extension_sdk.routing import APIRouter, HTTPMethod, TaskTimeouts
from mpt_extension_sdk.schemas import BaseSchema


class FakePayloadSchema(BaseSchema):
    """Dummy payload schema for API router tests."""

    name: str


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
def test_api_router_normalizes_path(prefix, path, expected, route_handler):
    router = APIRouter(prefix=prefix)

    router.get(path=path, name="orders")(route_handler)  # act

    route = router.routes[0]
    assert route.path == expected
    assert route.method == HTTPMethod.GET


def test_api_router_rejects_empty_path():
    router = APIRouter(prefix="/events")

    with pytest.raises(ValueError, match="Route path cannot be empty"):
        router.get(path="   ", name="orders")


def test_api_router_endpoint_warns_deprecated(route_handler):
    router = APIRouter(prefix="/api")

    with pytest.warns(DeprecationWarning, match="use APIRouter.get instead"):
        router.endpoint(path="orders", name="orders")(route_handler)

    route = router.routes[0]
    assert route.path == "/api/orders"
    assert route.method == HTTPMethod.GET


def test_prefixed_routes_returns_prefixed_copies(route_handler):
    router = APIRouter(prefix="/api")
    router.get(path="orders", name="orders")(route_handler)

    result = router.prefixed_routes("/v1")

    assert len(result) == 1
    assert result[0].path == "/v1/api/orders"
    assert result[0].name == "orders"
    route = router.routes[0]
    assert route.path == "/api/orders"
    assert result[0] is not route


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


def test_api_router_rejects_bad_body_validator():
    router = APIRouter(prefix="/api")

    with pytest.raises(TypeError, match="must inherit from 'BaseSchema'"):
        router.post(path="orders", name="orders-create", body_validator=dict)


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


@pytest.mark.parametrize(
    ("register", "method"),
    [
        ("delete", HTTPMethod.DELETE),
        ("get", HTTPMethod.GET),
        ("patch", HTTPMethod.PATCH),
        ("post", HTTPMethod.POST),
        ("put", HTTPMethod.PUT),
    ],
)
def test_api_router_registers_deferrable(register, method, async_route_handler):
    router = APIRouter(prefix="/agreements")
    timeouts = TaskTimeouts(max_task_lifespan=7200, max_task_processing=3600)

    getattr(router, register)(
        path="orders", name="orders-sync", deferrable=True, timeouts=timeouts
    )(async_route_handler)  # act

    route = router.routes[0]
    assert route.method == method
    assert route.deferrable is True
    assert route.timeouts is timeouts


@pytest.mark.parametrize("register", ["delete", "get", "patch", "post", "put"])
def test_api_router_defaults_to_not_deferrable(register, route_handler):
    router = APIRouter(prefix="/agreements")

    getattr(router, register)(path="orders", name="orders-sync")(route_handler)  # act

    route = router.routes[0]
    assert route.deferrable is False
    assert route.timeouts is None


@pytest.mark.parametrize("register", ["delete", "get", "patch", "post", "put"])
def test_api_router_rejects_positional_options(register):
    router = APIRouter(prefix="/agreements")
    timeouts = TaskTimeouts(max_task_lifespan=7200)

    with pytest.raises(TypeError, match="positional argument"):
        getattr(router, register)("orders", "orders-sync", None, timeouts)


@pytest.mark.parametrize("option", ["deferrable", "timeouts"])
def test_api_router_endpoint_rejects_deferrable(option):
    router = APIRouter(prefix="/agreements")

    with pytest.raises(TypeError, match=option):
        router.endpoint(path="orders", name="orders", **{option: None})


def test_api_router_rejects_sync_deferrable(route_handler):
    router = APIRouter()
    route_handler.__qualname__ = "sync_agreements"
    action = router.post(path="sync", name="agreements-sync", deferrable=True)

    with pytest.raises(TypeError, match="'sync_agreements' must be a coroutine function"):
        action(route_handler)

    assert router.routes == []


def test_api_router_rejects_deferrable_path_param():
    router = APIRouter()

    with pytest.raises(ValueError, match="take the input from the request body"):
        router.post(path="{agreement_id}/sync", name="agreements-sync", deferrable=True)


def test_api_router_rejects_plain_timeouts():
    router = APIRouter()
    timeouts = TaskTimeouts(max_task_lifespan=7200)

    with pytest.raises(TypeError, match="declares task timeouts but is not deferrable"):
        router.post(path="sync", name="agreements-sync", timeouts=timeouts)


def test_api_router_keeps_plain_validation(route_handler):
    router = APIRouter()

    router.get(path="{agreement_id}", name="agreements-detail")(route_handler)  # act

    route = router.routes[0]
    assert route.path == "/{agreement_id}"
    assert route.deferrable is False

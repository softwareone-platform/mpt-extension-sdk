import pytest

from mpt_extension_sdk.routing import APIRouter, HTTPMethod
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
def test_api_router_endpoint_normalizes_path(prefix, path, expected, route_handler):
    router = APIRouter(prefix=prefix)

    router.endpoint(path=path, name="orders")(route_handler)  # act

    route = router.routes[0]
    assert route.path == expected
    assert route.method == HTTPMethod.GET


def test_api_router_rejects_empty_path():
    router = APIRouter(prefix="/events")

    with pytest.raises(ValueError, match="Route path cannot be empty"):
        router.endpoint(path="   ", name="orders")


def test_prefixed_routes_returns_prefixed_copies(route_handler):
    router = APIRouter(prefix="/api")
    router.endpoint(path="orders", name="orders")(route_handler)

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

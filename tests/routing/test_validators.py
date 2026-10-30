from collections.abc import Callable

import pytest

from mpt_extension_sdk.routing import (
    RouteType,
    ScheduleRouteDefinition,
    TaskTimeouts,
    WebhookRouteDefinition,
)
from mpt_extension_sdk.routing.validators import RouteValidator


@pytest.fixture
def schedule_route(mocker):
    def factory(name, path, schedule_id):
        return ScheduleRouteDefinition(
            name=name,
            path=path,
            route_type=RouteType.SCHEDULE,
            callback=mocker.Mock(spec=Callable),
            id=schedule_id,
            description="Sync data",
            cron="0 0 * * *",
        )

    return factory


@pytest.fixture
def webhook_route(mocker):
    def factory(name, path, product_id):
        return WebhookRouteDefinition(
            name=name,
            path=path,
            route_type=RouteType.WEBHOOK,
            callback=mocker.Mock(spec=Callable),
            criteria_sets=({"product.id": product_id},),
            description="Validate draft orders",
            webhook_type="validatePurchaseOrderDraft",
        )

    return factory


def test_validate_rejects_duplicate_webhook(webhook_route):
    existing = webhook_route("first", "/webhooks/first", "PRD-1")
    duplicate = webhook_route("second", "/webhooks/second", "PRD-1")

    with pytest.raises(ValueError, match="Webhook 'validatePurchaseOrderDraft' is already"):
        RouteValidator.validate_route_uniqueness(route=duplicate, routes=[existing])


def test_validate_accepts_webhook_other_criteria(webhook_route):
    existing = webhook_route("first", "/webhooks/first", "PRD-1")
    other_product = webhook_route("second", "/webhooks/second", "PRD-2")

    result = RouteValidator.validate_route_uniqueness(route=other_product, routes=[existing])

    assert result is None


def test_validate_rejects_duplicate_schedule_id(schedule_route):
    existing = schedule_route("first", "/schedule/first", "sync")
    duplicate = schedule_route("second", "/schedule/second", "sync")

    with pytest.raises(ValueError, match="Schedule id 'sync' is already registered"):
        RouteValidator.validate_route_uniqueness(route=duplicate, routes=[existing])


@pytest.mark.parametrize(
    ("handler_type", "deferrable"),
    [("AsyncMock", True), ("AsyncMock", False), ("Mock", False)],
)
def test_validate_deferrable_handler_accepts(mocker, handler_type, deferrable):
    route_handler = getattr(mocker, handler_type)(spec=Callable)

    result = RouteValidator.validate_deferrable_handler(route_handler, deferrable=deferrable)

    assert result is None


def test_validate_deferrable_handler_rejects_sync(mocker):
    route_handler = mocker.Mock(spec=Callable)
    route_handler.__qualname__ = "sync_agreements"

    with pytest.raises(TypeError, match="'sync_agreements' must be a coroutine function"):
        RouteValidator.validate_deferrable_handler(route_handler, deferrable=True)


@pytest.mark.parametrize(
    ("path", "deferrable", "timeouts"),
    [
        ("/agreements/sync", True, None),
        ("/agreements/sync", True, TaskTimeouts(max_task_processing=3600)),
        ("/agreements/{agreement_id}", False, None),
        ("/agreements/{sync-all}", True, None),
    ],
)
def test_validate_deferrable_options_accepts(path, deferrable, timeouts):
    result = RouteValidator.validate_deferrable_options(
        path=path, deferrable=deferrable, timeouts=timeouts
    )

    assert result is None


@pytest.mark.parametrize("path", ["/agreements/{agreement_id}", "/agreements/{agreement_id:int}"])
def test_validate_deferrable_rejects_path_param(path):
    with pytest.raises(ValueError, match="cannot declare path parameters"):
        RouteValidator.validate_deferrable_options(path=path, deferrable=True, timeouts=None)


def test_validate_deferrable_rejects_timeouts():
    timeouts = TaskTimeouts(max_task_lifespan=7200)

    with pytest.raises(TypeError, match="declares task timeouts but is not deferrable"):
        RouteValidator.validate_deferrable_options(
            path="/agreements/sync", deferrable=False, timeouts=timeouts
        )


@pytest.mark.parametrize(
    ("existing_path", "duplicate_path"),
    [
        ("/orders", "/orders/"),
        ("/orders/{id}", "/orders/{order_id}"),
        ("/orders/{id:int}", "/orders/{order_id}"),
    ],
)
def test_validate_rejects_equivalent_api_path(api_route_factory, existing_path, duplicate_path):
    existing = api_route_factory(name="orders-first", path=existing_path)
    duplicate = api_route_factory(name="orders-second", path=duplicate_path)

    with pytest.raises(ValueError, match="is already registered for method 'POST'"):
        RouteValidator.validate_route_uniqueness(route=duplicate, routes=[existing])


def test_validate_accepts_distinct_api_path(api_route_factory):
    existing = api_route_factory(name="orders-detail", path="/orders/{order_id}")
    route = api_route_factory(name="orders-lines", path="/orders/{order_id}/lines")

    result = RouteValidator.validate_route_uniqueness(route=route, routes=[existing])

    assert result is None


@pytest.mark.parametrize(
    "method_paths",
    [
        [("POST", "/agreements/sync"), ("POST", "/agreements/sync/")],
        [("POST", "/agreements/{id}/sync"), ("POST", "/agreements/{agreement_id:str}/sync")],
    ],
)
def test_validate_rejects_duplicate_deferrable(method_paths):
    with pytest.raises(ValueError, match="is already declared for method 'POST'"):
        RouteValidator.validate_deferrable_uniqueness(method_paths)


def test_validate_accepts_unique_deferrables():
    method_paths = [
        ("POST", "/agreements/sync"),
        ("PUT", "/agreements/sync"),
        ("POST", "/orders/sync"),
    ]

    result = RouteValidator.validate_deferrable_uniqueness(method_paths)

    assert result is None

import logging
from collections.abc import Callable

import pytest

from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.routing import RouteType, WebhookRouter
from mpt_extension_sdk.webhooks import AccountWebhookContext, WebhookContext, WebhookType


class FakeAccountWebhookContext(AccountWebhookContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return cls(**ctx.__dict__)


class FakeWebhookContext(WebhookContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        return cls(**ctx.__dict__)


@pytest.fixture
def webhook_handler(mocker):
    route_handler = mocker.Mock(spec=Callable)
    route_handler.__name__ = "validate_purchase_order_draft"
    return route_handler


@pytest.fixture
def other_webhook_handler(mocker):
    route_handler = mocker.Mock(spec=Callable)
    route_handler.__name__ = "validate_draft_orders_again"
    return route_handler


def test_webhook_router_registers_webhook(webhook_handler):
    router = WebhookRouter(prefix="/webhooks")

    result = router.webhook(
        "orders/validate",
        type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        description=" Validate draft orders ",
        criteria={"product.id": "PRD-1111-1111"},
    )(webhook_handler)

    route = router.routes[0]
    assert result is webhook_handler
    assert (
        route.path,
        route.name,
        route.webhook_type,
        route.description,
        route.criteria_sets,
        route.route_type,
    ) == (
        "/webhooks/orders/validate",
        "validate_purchase_order_draft",
        WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        "Validate draft orders",
        ({"product.id": "PRD-1111-1111"},),
        RouteType.WEBHOOK,
    )


def test_webhook_router_accepts_criteria_list(webhook_handler):
    router = WebhookRouter()

    router.webhook(
        "/orders/validate",
        type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        description="Validate draft orders",
        criteria=[{"product.id": "PRD-1111-1111"}, {"product.id": "PRD-1111-1112"}],
    )(webhook_handler)  # act

    assert router.routes[0].criteria_sets == (
        {"product.id": "PRD-1111-1111"},
        {"product.id": "PRD-1111-1112"},
    )


def test_webhook_router_strips_criteria(webhook_handler):
    router = WebhookRouter()

    router.webhook(
        "/orders/validate",
        type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        description="Validate draft orders",
        criteria={" product.id ": " PRD-2222-2222 "},
    )(webhook_handler)  # act

    assert router.routes[0].criteria_sets == ({"product.id": "PRD-2222-2222"},)


def test_webhook_router_resolves_type_string(webhook_handler):
    router = WebhookRouter()

    router.webhook(
        "/orders/validate",
        type="ValidatePurchaseOrderDraft",
        description="Validate draft orders",
        criteria={"product.id": "PRD-1111-1111"},
    )(webhook_handler)  # act

    assert router.routes[0].webhook_type is WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT


def test_webhook_router_accepts_unknown_type(webhook_handler, caplog):
    router = WebhookRouter()

    with caplog.at_level(logging.WARNING):
        router.webhook(
            "/answers/validate",
            type="validateHelpdeskAnswer",
            description="Validate helpdesk answers",
            criteria={"form.id": "FRM-1"},
        )(webhook_handler)  # act

    assert router.routes[0].webhook_type == "validateHelpdeskAnswer"
    assert caplog.messages == ["Webhook type 'validateHelpdeskAnswer' is not known by the SDK"]


@pytest.mark.parametrize(
    ("webhook_kwargs", "error_message"),
    [
        (
            {"type": " ", "description": "Validate", "criteria": {"product.id": "PRD-1"}},
            "Webhook type cannot be empty",
        ),
        (
            {"type": "validateAccount", "description": " ", "criteria": {"product.id": "PRD-1"}},
            "Webhook description cannot be empty",
        ),
        (
            {"type": "validateAccount", "description": "Validate", "criteria": {}},
            "Webhook criteria cannot be empty",
        ),
        (
            {"type": "validateAccount", "description": "Validate", "criteria": []},
            "Webhook criteria cannot be empty",
        ),
        (
            {
                "type": "validateAccount",
                "description": "Validate",
                "criteria": [{"product.id": "PRD-1"}, {"product.id": "PRD-1"}],
            },
            "Webhook criteria cannot be repeated",
        ),
        (
            {"type": "validateAccount", "description": "Validate", "criteria": {" ": "PRD-1"}},
            "Webhook criteria keys must be non-empty strings",
        ),
        (
            {"type": "validateAccount", "description": "Validate", "criteria": {"product.id": ""}},
            "Webhook criteria value for 'product.id' must be a non-empty string",
        ),
        (
            {
                "type": "validateAccount",
                "description": "Validate",
                "criteria": {"product.id": "PRD-1", " product.id": "PRD-2"},
            },
            "Webhook criteria keys cannot be repeated",
        ),
        (
            {
                "type": "validateAccount",
                "description": "Validate",
                "criteria": [{"product.id": "PRD-1"}, {" product.id ": " PRD-1 "}],
            },
            "Webhook criteria cannot be repeated",
        ),
    ],
)
def test_webhook_router_rejects_invalid(webhook_kwargs, error_message):
    router = WebhookRouter()

    with pytest.raises(ValueError, match=error_message):
        router.webhook("/accounts/validate", **webhook_kwargs)


def test_webhook_router_rejects_duplicate(webhook_handler, other_webhook_handler):
    router = WebhookRouter()
    router.webhook(
        "/orders/validate",
        type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        description="Validate draft orders",
        criteria={"product.id": "PRD-1111-1111"},
    )(webhook_handler)
    duplicate = router.webhook(
        "/orders/validate-again",
        type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        description="Validate draft orders again",
        criteria=[{"product.id": "PRD-1111-1112"}, {"product.id": "PRD-1111-1111"}],
    )

    with pytest.raises(ValueError, match="Webhook 'validatePurchaseOrderDraft' is already"):
        duplicate(other_webhook_handler)


def test_webhook_router_uses_router_adapter(webhook_handler):
    router = WebhookRouter(context_adapter_type=FakeAccountWebhookContext)

    router.webhook(
        "/accounts/validate",
        type=WebhookType.VALIDATE_ACCOUNT,
        description="Validate accounts",
        criteria={"product.id": "PRD-3333-3333"},
    )(webhook_handler)  # act

    assert router.routes[0].context_adapter_type is FakeAccountWebhookContext


def test_webhook_route_overrides_adapter(webhook_handler):
    router = WebhookRouter(context_adapter_type=FakeAccountWebhookContext)

    router.webhook(
        "/accounts/validate",
        type=WebhookType.VALIDATE_ACCOUNT,
        description="Validate accounts",
        criteria={"product.id": "PRD-3333-3333"},
        context_adapter_type=None,
    )(webhook_handler)  # act

    assert router.routes[0].context_adapter_type is None


def test_webhook_router_rejects_bad_adapter():
    router = WebhookRouter()

    with pytest.raises(TypeError, match="must implement 'ContextAdapter'"):
        router.webhook(
            "/accounts/validate",
            type=WebhookType.VALIDATE_ACCOUNT,
            description="Validate accounts",
            criteria={"product.id": "PRD-3333-3333"},
            context_adapter_type=object,
        )


def test_router_rejects_wrong_default_adapter():
    router = WebhookRouter(context_adapter_type=FakeAccountWebhookContext)

    with pytest.raises(TypeError, match="must inherit from 'OrderWebhookContext'"):
        router.webhook(
            "/orders/validate",
            type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
            description="Validate orders",
            criteria={"product.id": "PRD-3333-3333"},
        )


def test_router_rejects_wrong_route_adapter():
    router = WebhookRouter()

    with pytest.raises(TypeError, match="must inherit from 'RequestWebhookContext'"):
        router.webhook(
            "/requests/validate",
            type=WebhookType.VALIDATE_REQUEST,
            description="Validate requests",
            criteria={"product.id": "PRD-3333-3333"},
            context_adapter_type=FakeAccountWebhookContext,
        )


def test_router_accepts_adapter_for_unknown_type(webhook_handler):
    router = WebhookRouter(context_adapter_type=FakeWebhookContext)

    router.webhook(
        "/answers/validate",
        type="validateHelpdeskAnswer",
        description="Validate answers",
        criteria={"product.id": "PRD-3333-3333"},
    )(webhook_handler)  # act

    assert [route.context_adapter_type for route in router.routes] == [FakeWebhookContext]


def test_router_rejects_typed_unknown_adapter():
    router = WebhookRouter(context_adapter_type=FakeAccountWebhookContext)

    with pytest.raises(TypeError, match="must not inherit from 'AccountWebhookContext'"):
        router.webhook(
            "/answers/validate",
            type="validateHelpdeskAnswer",
            description="Validate answers",
            criteria={"product.id": "PRD-3333-3333"},
        )

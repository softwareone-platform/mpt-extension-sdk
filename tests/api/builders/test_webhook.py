from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.trace import StatusCode

from mpt_extension_sdk.api.builders.webhook import create_webhook_route
from mpt_extension_sdk.context import ContextAdapter
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.observability.tracing import RouteSpanAttributes
from mpt_extension_sdk.routing import WebhookRouter
from mpt_extension_sdk.runtime import app as runtime_app
from mpt_extension_sdk.webhooks import (
    OrderWebhookContext,
    WebhookContext,
    WebhookError,
    WebhookResponse,
    WebhookType,
)


@dataclass(kw_only=True)
class FakeOrderWebhookContext(OrderWebhookContext, ContextAdapter):
    marker: str = ""

    @classmethod
    def from_context(cls, ctx):
        return cls(**ctx.__dict__, marker="adapted")


class FakeFailingAdapter(OrderWebhookContext, ContextAdapter):
    @classmethod
    def from_context(cls, ctx):
        raise ValueError("Adapter failed")


@pytest.fixture
def order_payload():
    return {
        "id": "ORD-1",
        "status": "Draft",
        "type": "Purchase",
        "agreement": {"id": "AGR-1", "href": "/commerce/agreements/AGR-1"},
        "authorization": {"id": "AUT-1", "name": "US", "currency": "USD"},
        "product": {"id": "PRD-1", "name": "Product"},
        "notes": "kept as it arrived",
    }


@pytest.fixture
def webhook_handler(mocker):
    route_handler = mocker.Mock(spec=Callable)
    route_handler.__name__ = "validate_order"
    route_handler.__module__ = __name__
    return route_handler


@pytest.fixture
def webhook_client(api_route_dependencies, api_service_type_factory, mock_api_service):
    def factory(
        route_handler,
        webhook_type=WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT,
        context_adapter_type=None,
    ):
        extension_app = ExtensionApp(
            mpt_api_service_type=api_service_type_factory(mock_api_service)
        )
        webhook_router = WebhookRouter(prefix="/webhooks")
        webhook_router.webhook(
            "/validate",
            type=webhook_type,
            description="Validate",
            criteria={"product.id": "PRD-1"},
            context_adapter_type=context_adapter_type,
        )(route_handler)
        extension_app.include_router(webhook_router)
        app = FastAPI()
        runtime_app._configure_middlewares(app)
        app.include_router(create_webhook_route(extension_app.routes[0], extension_app))
        return TestClient(app)

    return factory


@pytest.fixture
def call_webhook(webhook_client, webhook_handler, auth_headers, order_payload):
    def factory():
        client = webhook_client(webhook_handler)
        return client.post(
            "/webhooks/validate",
            json=order_payload,
            headers={**auth_headers, "x-request-id": "corr-1"},
        )

    return factory


@pytest.fixture
def webhook_span(mocker):
    span = mocker.Mock()

    @contextmanager
    def start_span(*args):  # noqa: WPS430
        yield span

    start_route_span = mocker.patch(
        "mpt_extension_sdk.api.builders.webhook_execution.start_route_span",
        autospec=True,
        side_effect=start_span,
    )
    return start_route_span, span


def test_webhook_route_returns_handler_payload(call_webhook, webhook_handler, order_payload):
    webhook_handler.return_value = WebhookResponse.ok(order_payload)

    result = call_webhook()

    context = webhook_handler.call_args.args[0]
    assert (result.status_code, result.json()) == (HTTPStatus.OK, order_payload)
    assert isinstance(context, OrderWebhookContext)
    assert (context.payload, context.request.body) == (order_payload, order_payload)


def test_webhook_returns_order_as_it_arrived(call_webhook, webhook_handler, order_payload):
    webhook_handler.side_effect = lambda ctx: WebhookResponse.ok(ctx.order)

    result = call_webhook()

    assert result.json() == order_payload


def test_webhook_unknown_type_gets_payload(webhook_client, webhook_handler, auth_headers):
    webhook_handler.return_value = WebhookResponse.ok({"id": "ANS-1"})
    client = webhook_client(webhook_handler, webhook_type="validateHelpdeskAnswer")

    result = client.post("/webhooks/validate", json={"id": "ANS-1"}, headers=auth_headers)

    assert result.status_code == HTTPStatus.OK
    assert webhook_handler.call_args.args[0].__class__ is WebhookContext


def test_webhook_route_adapts_context(webhook_client, webhook_handler, auth_headers, order_payload):
    webhook_handler.return_value = WebhookResponse.ok({})
    client = webhook_client(webhook_handler, context_adapter_type=FakeOrderWebhookContext)

    client.post("/webhooks/validate", json=order_payload, headers=auth_headers)  # act

    context = webhook_handler.call_args.args[0]
    assert (context.marker, context.order.id) == ("adapted", "ORD-1")


def test_webhook_adapter_error_is_unexpected(
    webhook_client, webhook_handler, auth_headers, order_payload
):
    client = webhook_client(webhook_handler, context_adapter_type=FakeFailingAdapter)

    result = client.post(
        "/webhooks/validate", json=order_payload, headers={**auth_headers, "x-request-id": "corr-1"}
    )

    assert (result.status_code, result.json()["id"]) == (HTTPStatus.INTERNAL_SERVER_ERROR, "EXT001")
    webhook_handler.assert_not_called()


def test_webhook_route_rejects_wrong_payload(webhook_client, webhook_handler, auth_headers):
    client = webhook_client(webhook_handler)

    result = client.post("/webhooks/validate", json={"id": "ORD-1"}, headers=auth_headers)

    assert (result.status_code, result.json()) == (
        HTTPStatus.BAD_REQUEST,
        {"id": "EXT003", "message": "The webhook body does not match its type"},
    )
    webhook_handler.assert_not_called()


def test_webhook_route_awaits_async_handler(mocker, webhook_client, auth_headers, order_payload):
    async_handler = mocker.AsyncMock(
        spec=Callable, return_value=WebhookResponse.ok({"id": "ORD-1"})
    )
    async_handler.__name__ = "validate_order"
    async_handler.__module__ = __name__
    client = webhook_client(async_handler)

    result = client.post("/webhooks/validate", json=order_payload, headers=auth_headers)

    assert (result.status_code, result.json()) == (HTTPStatus.OK, {"id": "ORD-1"})


def test_webhook_route_returns_error_response(call_webhook, webhook_handler):
    webhook_handler.return_value = WebhookResponse.error("AWS001", "Invalid account type")

    result = call_webhook()

    assert (result.status_code, result.json()) == (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {"id": "AWS001", "message": "Invalid account type"},
    )


@pytest.mark.parametrize(
    ("webhook_error", "expected_status"),
    [
        (WebhookError("AWS001", "Invalid account type"), HTTPStatus.INTERNAL_SERVER_ERROR),
        (
            WebhookError("AWS001", "Invalid account type", status_code=HTTPStatus.BAD_GATEWAY),
            HTTPStatus.BAD_GATEWAY,
        ),
    ],
)
def test_webhook_route_maps_webhook_error(
    call_webhook, webhook_handler, webhook_error, expected_status
):
    webhook_handler.side_effect = webhook_error

    result = call_webhook()

    assert (result.status_code, result.json()) == (
        expected_status,
        {"id": "AWS001", "message": "Invalid account type"},
    )


@pytest.mark.parametrize(
    "handler_outcome",
    [{"side_effect": ValueError("Unexpected")}, {"return_value": {"id": "ORD-1"}}],
)
def test_webhook_route_hides_unexpected_errors(call_webhook, webhook_handler, handler_outcome):
    webhook_handler.configure_mock(**handler_outcome)

    result = call_webhook()

    assert (result.status_code, result.json()) == (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {
            "id": "EXT001",
            "message": "Unexpected webhook error - contact support. Correlation id: corr-1",
        },
    )


def test_webhook_route_rejects_missing_token(webhook_client, webhook_handler, order_payload):
    client = webhook_client(webhook_handler)

    result = client.post("/webhooks/validate", json=order_payload)

    assert (result.status_code, result.json()["id"]) == (HTTPStatus.UNAUTHORIZED, "EXT002")
    webhook_handler.assert_not_called()


def test_webhook_route_rejects_other_extension(
    webhook_client, webhook_handler, order_payload, auth_claims_factory, jwt_token_factory
):
    client = webhook_client(webhook_handler)
    token = jwt_token_factory(auth_claims_factory(extension_id="EXT-OTHER"))

    result = client.post(
        "/webhooks/validate", json=order_payload, headers={"Authorization": f"Bearer {token}"}
    )

    assert (result.status_code, result.json()["id"]) == (HTTPStatus.UNAUTHORIZED, "EXT002")


@pytest.mark.parametrize(
    ("request_kwargs", "expected_message"),
    [
        ({"content": b"not-json"}, "The webhook body is not valid JSON"),
        ({"json": [{"id": "ORD-1"}]}, "The webhook body must be a JSON object"),
    ],
)
def test_webhook_route_rejects_invalid_payload(
    webhook_client, webhook_handler, auth_headers, request_kwargs, expected_message
):
    client = webhook_client(webhook_handler)

    result = client.post("/webhooks/validate", headers=auth_headers, **request_kwargs)

    assert (result.status_code, result.json()) == (
        HTTPStatus.BAD_REQUEST,
        {"id": "EXT003", "message": expected_message},
    )


def test_webhook_span_describes_call(call_webhook, webhook_handler, webhook_span):
    start_route_span, _ = webhook_span
    webhook_handler.return_value = WebhookResponse.ok({})

    call_webhook()  # act

    start_route_span.assert_called_once_with(
        "Webhook validatePurchaseOrderDraft ORD-1",
        RouteSpanAttributes(
            account_id="ACC-1",
            correlation_id="corr-1",
            extension_id="EXT-1",
            route_name="validate_order",
            route_path="/webhooks/validate",
            route_type="webhook",
        ),
        {"mpt.webhook.type": "validatePurchaseOrderDraft", "order.id": "ORD-1"},
    )


def test_webhook_span_unknown_type(webhook_client, webhook_handler, webhook_span, auth_headers):
    start_route_span, _ = webhook_span
    webhook_handler.return_value = WebhookResponse.ok({})
    client = webhook_client(webhook_handler, webhook_type="validateHelpdeskAnswer")

    client.post("/webhooks/validate", json={"id": "ANS-1"}, headers=auth_headers)  # act

    span_name, _, attributes = start_route_span.call_args.args
    assert (span_name, attributes) == (
        "Webhook validateHelpdeskAnswer",
        {"mpt.webhook.type": "validateHelpdeskAnswer"},
    )


@pytest.mark.parametrize(
    ("webhook_type", "payload", "span_name", "attributes"),
    [
        (
            WebhookType.VALIDATE_ACCOUNT,
            {"id": "ACC-1", "name": "Vendor"},
            "Webhook validateAccount ACC-1",
            {"mpt.webhook.type": "validateAccount", "account.id": "ACC-1"},
        ),
        (
            WebhookType.VALIDATE_REQUEST,
            {"id": "REQ-1", "status": "Draft"},
            "Webhook validateRequest REQ-1",
            {"mpt.webhook.type": "validateRequest", "request.id": "REQ-1"},
        ),
    ],
)
def test_webhook_span_names_business_object(  # noqa: WPS211
    webhook_client,
    webhook_handler,
    webhook_span,
    auth_headers,
    webhook_type,
    payload,
    span_name,
    attributes,
):
    start_route_span, _ = webhook_span
    webhook_handler.return_value = WebhookResponse.ok({})
    client = webhook_client(webhook_handler, webhook_type=webhook_type)

    client.post("/webhooks/validate", json=payload, headers=auth_headers)  # act

    result_name, _, result_attributes = start_route_span.call_args.args
    assert (result_name, result_attributes) == (span_name, attributes)


def test_webhook_sets_log_context(mocker, call_webhook, webhook_handler):
    set_webhook_context = mocker.patch(
        "mpt_extension_sdk.api.builders.webhook_execution.set_webhook_context", autospec=True
    )
    webhook_handler.return_value = WebhookResponse.ok({})

    call_webhook()  # act

    set_webhook_context.assert_called_once_with(order_id="ORD-1", account_id="", request_id="")


@pytest.mark.parametrize(
    ("webhook_type", "payload", "log_context"),
    [
        (
            WebhookType.VALIDATE_ACCOUNT,
            {"id": "ACC-1", "name": "Vendor"},
            {"order_id": "", "account_id": "ACC-1", "request_id": ""},
        ),
        (
            WebhookType.VALIDATE_REQUEST,
            {"id": "REQ-1", "status": "Draft"},
            {"order_id": "", "account_id": "", "request_id": "REQ-1"},
        ),
    ],
)
def test_webhook_log_context_names_object(  # noqa: WPS211
    mocker, webhook_client, webhook_handler, auth_headers, webhook_type, payload, log_context
):
    set_webhook_context = mocker.patch(
        "mpt_extension_sdk.api.builders.webhook_execution.set_webhook_context", autospec=True
    )
    webhook_handler.return_value = WebhookResponse.ok({})
    client = webhook_client(webhook_handler, webhook_type=webhook_type)

    client.post("/webhooks/validate", json=payload, headers=auth_headers)  # act

    set_webhook_context.assert_called_once_with(**log_context)


def test_webhook_span_keeps_status_on_error(call_webhook, webhook_handler, webhook_span):
    _, span = webhook_span
    webhook_handler.side_effect = WebhookError("AWS001", "Invalid account type")

    call_webhook()  # act

    span.set_status.assert_not_called()


def test_webhook_span_marks_unexpected_error(call_webhook, webhook_handler, webhook_span):
    _, span = webhook_span
    webhook_handler.side_effect = ValueError("Unexpected")

    call_webhook()  # act

    span_status = span.set_status.call_args.args[0]
    assert span_status.status_code is StatusCode.ERROR

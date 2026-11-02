import pytest

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.webhooks import (
    AccountWebhookContext,
    OrderWebhookContext,
    RequestWebhookContext,
    WebhookContext,
)


@pytest.fixture
def context_fields(mocker, logger):
    return {
        "auth": None,
        "ext_settings": mocker.sentinel.ext_settings,
        "logger": logger,
        "mpt_api_service": mocker.sentinel.mpt_api_service,
        "request": mocker.create_autospec(AuthenticatedRequestContext, instance=True),
        "runtime_settings": mocker.sentinel.runtime_settings,
        "vendor_mpt_api_service": mocker.sentinel.vendor_mpt_api_service,
    }


@pytest.fixture
def order_payload():
    return {
        "id": "ORD-1",
        "status": "Draft",
        "type": "Purchase",
        "agreement": {"id": "AGR-1", "href": "/commerce/agreements/AGR-1"},
        "authorization": {"id": "AUT-1", "name": "US", "currency": "USD"},
        "product": {"id": "PRD-1", "name": "Product"},
    }


def test_webhook_context_keeps_payload(context_fields):
    result = WebhookContext.from_payload({"id": "ANS-1"}, **context_fields)

    assert result.payload == {"id": "ANS-1"}


def test_account_context_parses_account(context_fields):
    payload = {"id": "ACC-1", "name": "Vendor"}

    result = AccountWebhookContext.from_payload(payload, **context_fields)

    assert (result.account.id, result.payload) == ("ACC-1", payload)


def test_order_context_parses_order(context_fields, order_payload):
    result = OrderWebhookContext.from_payload(order_payload, **context_fields)

    assert (result.order.id, result.order.agreement.id, result.payload) == (
        "ORD-1",
        "AGR-1",
        order_payload,
    )


def test_request_context_parses_request(context_fields):
    payload = {"id": "REQ-1", "status": "Draft"}

    result = RequestWebhookContext.from_payload(payload, **context_fields)

    assert (result.mpt_request.id, result.payload) == ("REQ-1", payload)

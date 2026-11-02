import pytest

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders import WebhookContextBuilder
from mpt_extension_sdk.webhooks import (
    AccountWebhookContext,
    OrderWebhookContext,
    RequestWebhookContext,
    WebhookContext,
    WebhookType,
)
from mpt_extension_sdk.webhooks.errors import WebhookInvalidPayloadError


@pytest.fixture
def builder_factory(mocker, logger):
    def factory(webhook_type, payload):
        return WebhookContextBuilder(
            handler_logger=logger,
            payload=payload,
            request_context=mocker.create_autospec(AuthenticatedRequestContext, instance=True),
            webhook_type=webhook_type,
        )

    return factory


@pytest.fixture
def order_payload():
    return {
        "id": "ORD-1",
        "status": "Draft",
        "type": "Purchase",
        "agreement": {"id": "AGR-1", "name": "Agreement", "status": "Draft"},
        "authorization": {"id": "AUT-1", "name": "US", "currency": "USD"},
        "product": {"id": "PRD-1", "name": "Product"},
    }


async def test_webhook_context_types_account(builder_factory, resources):
    builder = builder_factory(WebhookType.VALIDATE_ACCOUNT, {"id": "ACC-1", "name": "Vendor"})

    result = await builder.build(resources)

    assert isinstance(result, AccountWebhookContext)
    assert result.account.id == "ACC-1"


async def test_webhook_context_types_order(builder_factory, resources, order_payload):
    builder = builder_factory(WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT, order_payload)

    result = await builder.build(resources)

    assert isinstance(result, OrderWebhookContext)
    assert result.order.id == "ORD-1"


async def test_webhook_context_types_request(builder_factory, resources):
    builder = builder_factory(WebhookType.VALIDATE_REQUEST, {"id": "REQ-1", "status": "Draft"})

    result = await builder.build(resources)

    assert isinstance(result, RequestWebhookContext)
    assert result.mpt_request.id == "REQ-1"


async def test_webhook_context_generic_for_unknown(builder_factory, resources):
    builder = builder_factory("validateHelpdeskAnswer", {"id": "ANS-1"})

    result = await builder.build(resources)

    assert result.__class__ is WebhookContext
    assert (result.payload, result.mpt_api_service) == ({"id": "ANS-1"}, resources.mpt_api_service)


async def test_webhook_context_rejects_wrong_payload(builder_factory, resources, caplog):
    builder = builder_factory(WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT, {"id": "ORD-1"})

    with pytest.raises(WebhookInvalidPayloadError) as error_info:
        await builder.build(resources)

    assert (error_info.value.error_id, error_info.value.status_code) == ("EXT003", 400)
    assert caplog.messages[0].startswith("Invalid webhook validatePurchaseOrderDraft payload")


async def test_webhook_context_hides_payload_in_log(builder_factory, resources, caplog):
    builder = builder_factory(WebhookType.VALIDATE_ACCOUNT, {"id": "ACC-1", "name": 42})

    with pytest.raises(WebhookInvalidPayloadError):
        await builder.build(resources)

    assert "'loc': ('name',)" in caplog.messages[0]
    assert "42" not in caplog.messages[0]

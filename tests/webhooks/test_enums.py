import pytest

from mpt_extension_sdk.webhooks import WebhookObjectType, WebhookType


@pytest.mark.parametrize(
    ("webhook_type", "expected_object_type"),
    [
        (WebhookType.SELECT_ORDER_LINES, WebhookObjectType.ORDER),
        (WebhookType.VALIDATE_ACCOUNT, WebhookObjectType.ACCOUNT),
        (WebhookType.VALIDATE_CHANGE_ORDER_DRAFT, WebhookObjectType.ORDER),
        (WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT, WebhookObjectType.ORDER),
        (WebhookType.VALIDATE_PURCHASE_ORDER_QUERYING, WebhookObjectType.ORDER),
        (WebhookType.VALIDATE_REQUEST, WebhookObjectType.REQUEST),
        (WebhookType.VALIDATE_TERMINATE_ORDER, WebhookObjectType.ORDER),
    ],
)
def test_webhook_type_object_type(webhook_type, expected_object_type):
    result = webhook_type.object_type

    assert result is expected_object_type


@pytest.mark.parametrize(
    ("webhook_type", "expected_type"),
    [
        ("ValidatePurchaseOrderDraft", WebhookType.VALIDATE_PURCHASE_ORDER_DRAFT),
        (WebhookType.VALIDATE_ACCOUNT, WebhookType.VALIDATE_ACCOUNT),
        (" validateHelpdeskAnswer ", "validateHelpdeskAnswer"),
    ],
)
def test_webhook_type_resolve(webhook_type, expected_type):
    result = WebhookType.resolve(webhook_type)

    assert result == expected_type

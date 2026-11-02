from dataclasses import dataclass
from typing import Any, Self, override

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.context import BaseContext
from mpt_extension_sdk.models import Account, OrderSimple, Request


@dataclass(kw_only=True)
class WebhookContext(BaseContext):
    """Execution context passed to webhook handlers."""

    payload: dict[str, Any]
    request: AuthenticatedRequestContext

    @classmethod
    def from_payload(cls, payload: dict[str, Any], **context_fields: Any) -> Self:
        """Build the context for a webhook payload."""
        return cls(payload=payload, **context_fields)


@dataclass(kw_only=True)
class AccountWebhookContext(WebhookContext):
    """Execution context for webhooks that carry an account."""

    account: Account

    @override
    @classmethod
    def from_payload(cls, payload: dict[str, Any], **context_fields: Any) -> Self:
        """Build the context with the account parsed from the webhook payload."""
        return cls(account=Account.from_payload(payload), payload=payload, **context_fields)


@dataclass(kw_only=True)
class OrderWebhookContext(WebhookContext):
    """Execution context for webhooks that carry an order."""

    order: OrderSimple

    @override
    @classmethod
    def from_payload(cls, payload: dict[str, Any], **context_fields: Any) -> Self:
        """Build the context with the order parsed from the webhook payload."""
        return cls(order=OrderSimple.from_payload(payload), payload=payload, **context_fields)


@dataclass(kw_only=True)
class RequestWebhookContext(WebhookContext):
    """Execution context for webhooks that carry a platform request.

    The request object is `mpt_request`, because `request` is the HTTP request
    in every SDK context.
    """

    mpt_request: Request

    @override
    @classmethod
    def from_payload(cls, payload: dict[str, Any], **context_fields: Any) -> Self:
        """Build the context with the request parsed from the webhook payload."""
        return cls(mpt_request=Request.from_payload(payload), payload=payload, **context_fields)

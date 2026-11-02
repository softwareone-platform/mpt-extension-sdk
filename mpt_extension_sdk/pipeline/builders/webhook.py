import logging
from types import MappingProxyType
from typing import Any, override

from pydantic import ValidationError

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.webhooks import (
    AccountWebhookContext,
    OrderWebhookContext,
    RequestWebhookContext,
    WebhookContext,
    WebhookObjectType,
    WebhookType,
)
from mpt_extension_sdk.webhooks.errors import WebhookInvalidPayloadError

WEBHOOK_CONTEXT_TYPES = MappingProxyType({
    WebhookObjectType.ACCOUNT: AccountWebhookContext,
    WebhookObjectType.ORDER: OrderWebhookContext,
    WebhookObjectType.REQUEST: RequestWebhookContext,
})


class WebhookContextBuilder(ContextBuilder[WebhookContext]):
    """Build the execution context of a webhook call, typed by its object type.

    A webhook type the SDK does not know gets the generic `WebhookContext`.
    """

    def __init__(
        self,
        *,
        handler_logger: logging.Logger,
        payload: dict[str, Any],
        request_context: AuthenticatedRequestContext,
        webhook_type: WebhookType | str,
    ) -> None:
        self.handler_logger = handler_logger
        self.payload = payload
        self.request_context = request_context
        self.webhook_type = webhook_type

    @override
    async def build(self, resources: ContextResources) -> WebhookContext:
        """Build the webhook context with the business object parsed from the payload.

        Raises:
            WebhookInvalidPayloadError: The payload does not match the webhook object type.
        """
        try:
            return self._context_type().from_payload(
                self.payload,
                logger=self.handler_logger,
                request=self.request_context,
                **resources.base_fields(),
            )
        except ValidationError as error:
            self.handler_logger.warning(
                "Invalid webhook %s payload: %s",
                self.webhook_type,
                error.errors(include_url=False, include_context=False, include_input=False),
            )
            raise WebhookInvalidPayloadError("The webhook body does not match its type") from error

    def _context_type(self) -> type[WebhookContext]:
        if not isinstance(self.webhook_type, WebhookType):
            return WebhookContext
        return WEBHOOK_CONTEXT_TYPES[self.webhook_type.object_type]

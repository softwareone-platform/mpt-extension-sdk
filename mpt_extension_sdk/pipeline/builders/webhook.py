import logging
from typing import Any, override

from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.webhooks import WebhookContext


class WebhookContextBuilder(ContextBuilder[WebhookContext]):
    """Build the execution context of a webhook call."""

    def __init__(
        self,
        *,
        handler_logger: logging.Logger,
        payload: dict[str, Any],
        request_context: AuthenticatedRequestContext,
    ) -> None:
        self.handler_logger = handler_logger
        self.payload = payload
        self.request_context = request_context

    @override
    async def build(self, resources: ContextResources) -> WebhookContext:
        """Build the webhook context with the webhook body as its payload."""
        return WebhookContext(
            logger=self.handler_logger,
            payload=self.payload,
            request=self.request_context,
            **resources.base_fields(),
        )

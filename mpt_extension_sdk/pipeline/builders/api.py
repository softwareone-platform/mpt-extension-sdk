import logging
from typing import override

from mpt_extension_sdk.api.context import APIContext, AuthenticatedRequestContext
from mpt_extension_sdk.pipeline.builders.base import ContextBuilder, ContextResources
from mpt_extension_sdk.tasks import TaskHandle


class APIContextBuilder(ContextBuilder[APIContext]):
    """Build the execution context of an API request."""

    def __init__(
        self,
        *,
        handler_logger: logging.Logger,
        request_context: AuthenticatedRequestContext,
        task: TaskHandle | None = None,
    ) -> None:
        self.handler_logger = handler_logger
        self.request_context = request_context
        self.task = task

    @override
    async def build(self, resources: ContextResources) -> APIContext:
        """Build the API context, carrying the platform task when one is given."""
        return APIContext(
            logger=self.handler_logger,
            request=self.request_context,
            task=self.task,
            **resources.base_fields(),
        )

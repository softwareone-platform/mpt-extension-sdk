import logging
from typing import override

from fastapi import Request

from mpt_extension_sdk.api.auth import AuthContext
from mpt_extension_sdk.api.builders.arguments import APIHandlerArgumentsBuilder
from mpt_extension_sdk.api.builders.deferred_handler import build_deferred_callback
from mpt_extension_sdk.api.builders.task_delivery import TaskDeliveryHandler, TaskHandlerType
from mpt_extension_sdk.api.context import AuthenticatedRequestContext
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import RouteContextFactory
from mpt_extension_sdk.pipeline.builders import APIContextBuilder
from mpt_extension_sdk.routing.models import APIRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler, AsyncTaskRunner
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.tasks import TaskHandle


class DeferredCallHandler(TaskDeliveryHandler[None]):
    """Answer deferred API call deliveries."""

    def __init__(  # noqa: WPS211
        self,
        *,
        route: APIRouteDefinition,
        context_factory: RouteContextFactory,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
        instance_id: str | None = None,
    ) -> None:
        super().__init__(
            handler_type=TaskHandlerType.DEFERRED_CALL,
            task_service=task_service,
            runner=runner,
            handler_logger=handler_logger,
            instance_id=instance_id,
        )
        self.route = route
        self.context_factory = context_factory
        self._arguments_builder = APIHandlerArgumentsBuilder(route)

    @override
    async def build_callback(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: None
    ) -> AsyncTaskHandler:
        """Return a call to the API handler with the arguments built from the request."""
        request_context = AuthenticatedRequestContext.from_request(
            request, body=await self._arguments_builder.parse_request_body(request)
        )
        context = await self.context_factory.build(
            APIContextBuilder(
                handler_logger=self.handler_logger,
                request_context=request_context,
                task=TaskHandle(id=task.id, task_service=self.task_service),
            ),
            auth,
        )
        handler_arguments = await self._arguments_builder.build(request=request, context=context)
        return build_deferred_callback(
            callback=self.route.callback,
            handler_arguments=handler_arguments,
            task_service=self.task_service,
            task_id=task.id,
        )

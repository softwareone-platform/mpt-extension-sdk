import logging
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status

from mpt_extension_sdk.api.auth import AuthenticationError, RequestAuthenticationService
from mpt_extension_sdk.api.models.events import Event, EventResponse, TaskEvent
from mpt_extension_sdk.errors.mapping import map_exception_to_event_response
from mpt_extension_sdk.errors.pipeline import CancelError, DeferError, FailError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.observability.tracing import (
    get_business_attributes,
    record_exception,
    set_attributes,
    start_event_span,
)
from mpt_extension_sdk.pipeline import EventBaseContext, build_context
from mpt_extension_sdk.routing import EventDeliveryMode, EventRouteCallback, EventRouteDefinition
from mpt_extension_sdk.runtime.logging import set_event_context
from mpt_extension_sdk.services.mpt_api_service.api_service import MPTAPIService
from mpt_extension_sdk.services.mpt_api_service.task import TaskService
from mpt_extension_sdk.settings.runtime import RuntimeSettings, get_runtime_settings

TaskHandler = Callable[[TaskEvent, EventBaseContext], Awaitable[None] | None]
EventHandler = Callable[[Event, EventBaseContext], Awaitable[None] | None]

logger = logging.getLogger(__name__)


def create_event_route(route: EventRouteDefinition, extension_app: ExtensionApp) -> APIRouter:
    """Create a FastAPI router for an event route definition."""
    if route.delivery_mode == EventDeliveryMode.TASK:
        return create_task_event_route(route, extension_app)
    return create_non_task_event_route(route, extension_app)


# TODO: Refactor event route builders in a separate PR.
def create_task_event_route(  # ruff:ignore[complex-structure]  # noqa: WPS213, WPS217
    route: EventRouteDefinition, extension_app: ExtensionApp
) -> APIRouter:
    """Create a router for a task-based event handler."""
    router = APIRouter()
    handler_logger = logging.getLogger(route.callback.__module__)

    @router.post(route.path, status_code=status.HTTP_200_OK, response_model=EventResponse)
    async def handle_task_event(  # noqa: WPS212, WPS213, WPS217, WPS430
        request: Request,
        event: TaskEvent,
        task_service: Annotated[TaskService, Depends(get_tasks_service)],
    ) -> EventResponse:
        handler_logger.info("Received event (%s): %s", event.id, event.to_dict())
        set_event_context(task_id=event.task.id)
        try:
            context = await build_authenticated_context(
                request, event, handler_logger, extension_app
            )
        except AuthenticationError as error:
            handler_logger.exception("Task event authentication failed", exc_info=error)
            return map_exception_to_event_response(error)  # noqa: WPS204
        context = extension_app.build_context(route, context)
        with start_event_span(route.path, task_based=True, event=event) as span:
            business_attributes = get_business_attributes(context)
            set_event_context(
                order_id=str(business_attributes.get("order.id", "")),
                agreement_id=str(business_attributes.get("agreement.id", "")),
            )
            set_attributes(span, business_attributes)
            handler_logger.info("Starting task %s", event.task.id)
            await task_service.start(event.task.id)
            try:  # noqa: WPS225
                await run_handler(route.callback, event, context)
            except CancelError as error:
                record_exception(span, error)  # noqa: WPS204
                handler_logger.info("Task %s cancelled", event.task.id)
                await task_service.fail(event.task.id)
                return map_exception_to_event_response(error)  # noqa: WPS204
            except DeferError as error:
                record_exception(span, error)
                handler_logger.info("Task %s rescheduled", event.task.id)
                await task_service.reschedule(event.task.id)
                return map_exception_to_event_response(error)
            except FailError as error:
                record_exception(span, error)
                handler_logger.exception("Task %s failed", event.task.id, exc_info=error)
                await task_service.fail(event.task.id)
                return map_exception_to_event_response(error)
            except Exception as error:
                record_exception(span, error)
                handler_logger.exception("Task %s failed", event.task.id, exc_info=error)
                await task_service.fail(event.task.id)
                return map_exception_to_event_response(error)

            handler_logger.info("Task %s completed successfully", event.task.id)
            await task_service.complete(event.task.id)
            return EventResponse.ok()

    return router


# TODO: Refactor event route builders in a separate PR.
def create_non_task_event_route(  # ruff:ignore[complex-structure]  # noqa: WPS213
    route: EventRouteDefinition, extension_app: ExtensionApp
) -> APIRouter:
    """Create a FastAPI router for a non-task event handler."""
    router = APIRouter()
    handler_logger = logging.getLogger(route.callback.__module__)

    @router.post(route.path, status_code=status.HTTP_200_OK, response_model=EventResponse)
    async def handle_event(  # noqa: WPS212, WPS213, WPS430
        request: Request, event: Event
    ) -> EventResponse:
        handler_logger.info("Received event (%s): %s", event.id, event.to_dict())
        set_event_context()
        try:
            context = await build_authenticated_context(
                request, event, handler_logger, extension_app
            )
        except AuthenticationError as error:
            handler_logger.exception("Event authentication failed", exc_info=error)
            return map_exception_to_event_response(error)  # noqa: WPS204
        context = extension_app.build_context(route, context)
        with start_event_span(route.path, task_based=False, event=event) as span:
            business_attributes = get_business_attributes(context)
            set_event_context(
                order_id=str(business_attributes.get("order.id", "")),
                agreement_id=str(business_attributes.get("agreement.id", "")),
            )
            set_attributes(span, business_attributes)
            try:  # noqa: WPS225
                await run_handler(route.callback, event, context)
            except CancelError as error:
                record_exception(span, error)
                handler_logger.info("Event (%s) canceled", event.id)
                return map_exception_to_event_response(error)
            except DeferError as error:
                record_exception(span, error)
                handler_logger.info("Event (%s) rescheduled", event.id)
                return map_exception_to_event_response(error)
            except FailError as error:
                record_exception(span, error)
                handler_logger.exception("Event (%s) failed", event.id, exc_info=error)
                return map_exception_to_event_response(error)
            except Exception as error:
                record_exception(span, error)
                handler_logger.exception("Unhandled error", exc_info=error)
                return map_exception_to_event_response(error)

            return EventResponse.ok()

    return router


def get_tasks_service(
    runtime_settings: Annotated[RuntimeSettings, Depends(get_runtime_settings)],
) -> TaskService:
    """Return the task service authenticated with the extension token."""
    return MPTAPIService.from_config(
        base_url=runtime_settings.mpt_api_base_url, api_token=runtime_settings.ext_api_key
    ).tasks


async def build_authenticated_context(
    request: Request,
    event: Event,
    handler_logger: logging.Logger,
    extension_app: ExtensionApp,
) -> EventBaseContext:
    """Build an event context after authenticating the incoming request."""
    auth = RequestAuthenticationService().authenticate(request)
    return await build_context(
        event,
        handler_logger,
        auth=auth,
        mpt_api_service_type=extension_app.mpt_api_service_type,
    )


async def run_handler(
    event_handler: EventRouteCallback, event: Any, context: EventBaseContext
) -> None:
    """Invoke a handler and await the result if it is a coroutine."""
    handler_result = event_handler(event, context)
    if isawaitable(handler_result):
        await handler_result

import logging

from fastapi import Request

from mpt_extension_sdk.api.auth import (
    AuthContext,
    AuthenticationError,
    RequestAuthenticationService,
)
from mpt_extension_sdk.api.builders.schedule_acceptance import (
    CONTEXT_CREATION_ERRORS,
    ScheduleTaskAcceptance,
)
from mpt_extension_sdk.api.builders.schedule_timing import (
    get_execution_deadline,
    watchdog_delay_seconds,
)
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError
from mpt_extension_sdk.extension_app import ExtensionApp
from mpt_extension_sdk.models.task import Task
from mpt_extension_sdk.pipeline import RouteContextFactory, ScheduleContext
from mpt_extension_sdk.routing import ScheduleRouteDefinition
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskRunner, TaskExecution
from mpt_extension_sdk.runtime.logging import set_event_context
from mpt_extension_sdk.services.mpt_api_service.task import TaskService


class ScheduleTaskExecutor:
    """Execute the schedule delivery state machine."""

    def __init__(
        self,
        *,
        route: ScheduleRouteDefinition,
        extension_app: ExtensionApp,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
    ) -> None:
        """Initialize the executor with schedule runtime collaborators."""
        self.route = route
        self.extension_app = extension_app
        self.task_service = task_service
        self.runner = runner
        self.handler_logger = handler_logger
        self.acceptance = ScheduleTaskAcceptance(
            task_service=task_service,
            handler_logger=handler_logger,
        )

    async def execute(self, *, request: Request, task_id: str) -> EventResponse:
        """Answer a schedule delivery according to the platform task state."""
        set_event_context(task_id=task_id)
        try:
            auth = RequestAuthenticationService().authenticate(request)
        except AuthenticationError:
            self.handler_logger.exception("Schedule task authentication failed")
            response = EventResponse.cancel(reason="Authentication failed")
        else:
            response = await self._respond_by_task_state(task_id=task_id, auth=auth)
        return response

    async def _respond_by_task_state(self, *, task_id: str, auth: AuthContext) -> EventResponse:
        """Choose the delivery response from the current platform task state."""
        task = await self.acceptance.fetch_task(task_id)
        if task is None:
            response = EventResponse.reschedule()
        elif task.is_final:
            self.handler_logger.info("Schedule task %s is final: acknowledging the event", task_id)
            response = EventResponse.ok()
        else:
            response = await self._handle_non_final_delivery(task=task, auth=auth)
        return response

    async def _handle_non_final_delivery(self, *, task: Task, auth: AuthContext) -> EventResponse:
        """Reserve the task locally and accept it, or defer when already reserved."""
        with self.runner.reserve(task.id) as reserved:
            if reserved:
                context = await self._build_context_or_failure(auth=auth, task_id=task.id)
                if isinstance(context, EventResponse):
                    response = context
                else:
                    response = await self._start_and_submit(task=task, context=context)
            else:
                response = EventResponse.reschedule(watchdog_delay_seconds(task))
        return response

    async def _build_context_or_failure(
        self, *, auth: AuthContext, task_id: str
    ) -> ScheduleContext | EventResponse:
        """Build the schedule context or map the acceptance failure to a response."""
        factory = RouteContextFactory.from_service_type(self.extension_app.mpt_api_service_type)
        try:
            return await factory.build_schedule_context(
                schedule_id=self.route.id,
                task_id=task_id,
                handler_logger=self.handler_logger,
                auth=auth,
                task_service=self.task_service,
            )
        except CONTEXT_CREATION_ERRORS as error:
            return self.acceptance.map_context_error(error)

    async def _start_and_submit(self, *, task: Task, context: ScheduleContext) -> EventResponse:
        """Recover a lost task, start it, and submit the handler to the runner."""
        if task.is_processing:
            recovery_response = await self.acceptance.reschedule_lost_task(task.id)
            if recovery_response is not None:
                return recovery_response

        start_response = await self.acceptance.start_task(task.id)
        if start_response is not None:
            return start_response

        return await self._submit_to_runner(task=task, context=context)

    async def _submit_to_runner(self, *, task: Task, context: ScheduleContext) -> EventResponse:
        """Submit an accepted schedule task to the application runner."""
        try:
            submitted = self.runner.submit(
                execution=TaskExecution(
                    task_id=task.id,
                    task_callback=lambda: self.route.callback(context),
                    task_service=self.task_service,
                    handler_logger=self.handler_logger,
                    deadline_seconds=get_execution_deadline(task),
                ),
            )
        except AsyncTasksRunnerError as error:
            self.handler_logger.exception("Schedule task submission failed", exc_info=error)
            await self.acceptance.reschedule_after_failed_submit(task.id)
            return EventResponse.reschedule()

        self.handler_logger.debug("Schedule task %s submitted: %s", task.id, submitted)
        return EventResponse.reschedule(watchdog_delay_seconds(task))

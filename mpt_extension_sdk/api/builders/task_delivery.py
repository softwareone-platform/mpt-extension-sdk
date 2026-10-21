import datetime as dt
import logging
from abc import ABC, abstractmethod
from enum import StrEnum

from fastapi import Request
from mpt_api_client.exceptions import MPTError

from mpt_extension_sdk.api.auth import (
    AuthContext,
    AuthenticationError,
    RequestAuthenticationService,
)
from mpt_extension_sdk.api.builders.task_timing import (
    MAX_WATCHDOG_DELAY_SECONDS,
    MIN_WATCHDOG_DELAY_SECONDS,
    get_execution_deadline,
)
from mpt_extension_sdk.api.errors import APIError
from mpt_extension_sdk.api.models.events import EventResponse
from mpt_extension_sdk.errors.runtime import AsyncTasksRunnerError, ConfigError, ValidationError
from mpt_extension_sdk.models.task import Task, TaskStatus
from mpt_extension_sdk.runtime.async_tasks import AsyncTaskHandler, AsyncTaskRunner, TaskExecution
from mpt_extension_sdk.runtime.task_transitions import ClaimOutcome, SafeTaskTransitions
from mpt_extension_sdk.services.mpt_api_service.task import TaskService

NON_RECOVERABLE_CONTEXT_ERRORS = (ConfigError, ValidationError, TypeError, ValueError)
CONTEXT_CREATION_ERRORS = (AuthenticationError, *NON_RECOVERABLE_CONTEXT_ERRORS, MPTError)


class TaskHandlerType(StrEnum):
    """Handler types whose deliveries run as a Platform Task."""

    DEFERRED_CALL = "Deferred call"
    SCHEDULE = "Schedule"


class TaskDeliveryHandler[DeliveryT](ABC):  # noqa: WPS214
    """Answer a task delivery according to the state of its platform task."""

    def __init__(
        self,
        *,
        handler_type: TaskHandlerType,
        task_service: TaskService,
        runner: AsyncTaskRunner,
        handler_logger: logging.Logger,
        instance_id: str | None = None,
    ) -> None:
        self.handler_type = handler_type
        self.task_service = task_service
        self.runner = runner
        self.handler_logger = handler_logger
        self._transitions = SafeTaskTransitions(task_service, handler_logger, instance_id)

    async def execute(
        self, *, request: Request, task_id: str, delivery: DeliveryT
    ) -> EventResponse:
        """Answer the delivery of a platform task."""
        task = await self._fetch_task(task_id)
        if task is None:
            return EventResponse.reschedule()

        # Acknowledge a final task before authenticating, so it is never answered Cancel.
        if task.is_final:
            self.handler_logger.info(
                "%s task %s is final: acknowledging the delivery", self.handler_type, task_id
            )
            return EventResponse.ok()

        try:
            auth = RequestAuthenticationService().authenticate(request)
        except AuthenticationError:
            self.handler_logger.exception("%s task authentication failed", self.handler_type)
            return EventResponse.cancel(reason="Authentication failed")

        return await self._accept_delivery(request=request, auth=auth, task=task, delivery=delivery)

    @abstractmethod
    async def build_callback(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: DeliveryT
    ) -> AsyncTaskHandler:
        """Return the call the runner executes for this delivery."""

    def can_claim(self, task: Task) -> bool:
        """Return whether no other instance runs the task and the runner has capacity."""
        # A Processing task is already claimed: the platform would reject the claim.
        if task.status == TaskStatus.PROCESSING and not self.runner.is_running(task.id):
            self.handler_logger.info(
                "%s task %s is running elsewhere: deferring the delivery",
                self.handler_type,
                task.id,
            )
            return False

        if self.runner.has_capacity():
            return True

        self.handler_logger.warning(
            "%s task %s deferred: the runner is at capacity", self.handler_type, task.id
        )
        return False

    def watchdog_delay(self, task: Task, delivery: DeliveryT) -> int:
        """Return the Delay, in seconds, to answer while the task runs."""
        now = dt.datetime.now(dt.UTC)
        processing = (now - (task.started_at or now)).total_seconds()
        delay = min(max(processing, MIN_WATCHDOG_DELAY_SECONDS), MAX_WATCHDOG_DELAY_SECONDS)
        return int(delay)

    async def _accept_delivery(
        self, *, request: Request, auth: AuthContext, task: Task, delivery: DeliveryT
    ) -> EventResponse:
        watchdog_delay = self.watchdog_delay(task, delivery)
        if not self.can_claim(task):
            return EventResponse.reschedule(watchdog_delay)

        with self.runner.reserve(task.id) as reserved:
            if not reserved:
                return EventResponse.reschedule(watchdog_delay)

            try:
                task_callback = await self.build_callback(
                    request=request, auth=auth, task=task, delivery=delivery
                )
            except APIError:
                self.handler_logger.exception(
                    "%s task request payload is invalid", self.handler_type
                )
                return EventResponse.cancel(reason="Invalid request payload")
            except CONTEXT_CREATION_ERRORS as error:
                return self._map_context_error(error)

            return await self._start_execution(
                task=task, task_callback=task_callback, watchdog_delay=watchdog_delay
            )

    async def _start_execution(
        self, *, task: Task, task_callback: AsyncTaskHandler, watchdog_delay: int
    ) -> EventResponse:
        claim = await self._transitions.claim(task.id)
        if claim == ClaimOutcome.ALREADY_CLAIMED:
            return EventResponse.reschedule(watchdog_delay)

        if claim == ClaimOutcome.FAILED:
            return EventResponse.reschedule()

        try:
            submitted = self.runner.submit(
                execution=TaskExecution(
                    task_id=task.id,
                    task_callback=task_callback,
                    task_service=self.task_service,
                    handler_logger=self.handler_logger,
                    deadline_seconds=get_execution_deadline(task),
                ),
            )
        except AsyncTasksRunnerError:
            self.handler_logger.exception("%s task submission failed", self.handler_type)
            submitted = False

        if submitted:
            self.handler_logger.debug("%s task %s submitted", self.handler_type, task.id)
            return EventResponse.reschedule(watchdog_delay)

        self.handler_logger.warning("%s task %s was not submitted", self.handler_type, task.id)
        # The claim succeeded, so put the task back in a retryable state for the next delivery.
        try:
            await self.task_service.reschedule(task.id)
        except MPTError:
            self.handler_logger.exception("%s task reschedule failed", self.handler_type)
        return EventResponse.reschedule()

    async def _fetch_task(self, task_id: str) -> Task | None:
        try:
            return await self.task_service.get(task_id)
        except MPTError:
            self.handler_logger.exception("%s task could not be fetched", self.handler_type)
            return None

    def _map_context_error(self, error: Exception) -> EventResponse:
        if isinstance(error, AuthenticationError):
            self.handler_logger.error(
                "%s task authentication failed", self.handler_type, exc_info=error
            )
            return EventResponse.cancel(reason="Authentication failed")

        if isinstance(error, NON_RECOVERABLE_CONTEXT_ERRORS):
            self.handler_logger.error(
                "%s context creation is not recoverable", self.handler_type, exc_info=error
            )
            return EventResponse.cancel(reason="Non-recoverable context error")

        self.handler_logger.error("%s context creation failed", self.handler_type, exc_info=error)
        return EventResponse.reschedule()
